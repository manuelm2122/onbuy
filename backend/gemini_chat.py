import base64
from pathlib import Path
import json
import os
from typing import Any, AsyncIterator, List, Optional

import httpx

API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class Usage:
    def __init__(self, input_tokens=0, output_tokens=0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class LlmResponse:
    def __init__(self, text, usage):
        self.text = text
        self.usage = usage

    def __str__(self):
        return self.text


class UserMessage:
    def __init__(self, text=None, file_contents=None, *args, **kwargs):
        if text is None and args:
            text = args[0]
        self.text = text if text is not None else kwargs.get("text", "")
        self.file_contents = file_contents if file_contents is not None else kwargs.get("file_contents") or []


class FileContentWithMimeType:
    def __init__(self, content=None, mime_type=None, file_path=None, *args, **kwargs):
        self.content = content if content is not None else kwargs.get("content") or kwargs.get("data") or b""
        self.file_path = file_path or kwargs.get("file_path")
        self.mime_type = mime_type or kwargs.get("mime_type") or "application/octet-stream"


class TextDelta:
    def __init__(self, content="", *args, **kwargs):
        self.content = content or kwargs.get("content", "")
        self.text = self.content
        self.usage = None


class StreamDone:
    def __init__(self, usage=None, text=""):
        self.usage = usage or Usage()
        self.content = text
        self.text = text


class LlmChat:
    def __init__(self, api_key=None, session_id=None, system_message=None, initial_messages=None, **kwargs):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
        self.session_id = session_id
        self.system_message = system_message or ""
        self.model = kwargs.get("model") or "gemini-2.5-flash"
        self.tools = None
        self.history: List[dict] = []
        self.provider = "gemini"
        self.vertex = {}
        extra_system = []
        for msg in initial_messages or []:
            if isinstance(msg, str):
                role, content = "user", msg
            elif isinstance(msg, dict):
                role = msg.get("role") or "user"
                content = msg.get("content") or msg.get("text") or ""
            else:
                role, content = "user", getattr(msg, "text", "") or ""
            if not content:
                continue
            if role == "system":
                extra_system.append(content)
                continue
            if role == "assistant":
                role = "model"
            if role not in ("user", "model"):
                role = "user"
            self.history.append({"role": role, "parts": [{"text": content[:12000]}]})
        if extra_system:
            self.system_message = (self.system_message + "\n\n" + "\n\n".join(extra_system)).strip()
        # Gemini exige que contents empiece en user y alterne
        cleaned = []
        for item in self.history:
            if cleaned and cleaned[-1]["role"] == item["role"]:
                cleaned[-1]["parts"][0]["text"] += "\n" + item["parts"][0]["text"]
            else:
                cleaned.append(item)
        if cleaned and cleaned[0]["role"] != "user":
            cleaned.insert(0, {"role": "user", "parts": [{"text": "(inicio del expediente)"}]})
        self.history = cleaned[-24:]

    def with_model(self, provider, model):
        self.provider = provider or "gemini"
        self.model = model or self.model
        return self

    def with_params(self, **kwargs):
        self.vertex = kwargs
        return self

    def with_tools(self, tools):
        self.tools = tools
        return self

    def _file_bytes(self, f):
        for name in ("content", "data", "file_content", "bytes", "blob"):
            raw = getattr(f, name, None)
            if raw:
                return raw
        path = getattr(f, "file_path", None) or (f.get("file_path") if isinstance(f, dict) else None)
        if path:
            return Path(path).read_bytes()
        if isinstance(f, (bytes, bytearray)):
            return bytes(f)
        if isinstance(f, dict):
            return f.get("content") or f.get("data") or f.get("file_content") or b""
        return b""

    def _file_mime(self, f):
        if isinstance(f, dict):
            return f.get("mime_type") or f.get("mimeType") or "application/octet-stream"
        return getattr(f, "mime_type", None) or getattr(f, "mimeType", None) or "application/octet-stream"

    def _parts_from_message(self, message) -> list:
        if isinstance(message, str):
            return [{"text": message}]
        parts = []
        text = getattr(message, "text", None) or ""
        if text:
            parts.append({"text": text})
        for f in getattr(message, "file_contents", None) or []:
            raw = self._file_bytes(f)
            if isinstance(raw, str):
                raw = raw.encode()
            if not raw:
                raise RuntimeError("Adjunto vacio: el objeto no trae content/data")
            mime = self._file_mime(f)
            parts.append({
                "inlineData": {
                    "mimeType": mime,
                    "data": base64.b64encode(raw).decode(),
                }
            })
        return parts or [{"text": ""}]

    async def _raise_for_status(self, r):
        if r.status_code < 400:
            return
        if getattr(r, "is_stream_consumed", None) is not None:
            body = (await r.aread()).decode("utf-8", "replace")
        else:
            body = r.text
        raise RuntimeError(f"Gemini {r.status_code} en {self.model}: {body[:500]}")

    def _body(self, parts: list) -> dict:
        contents = list(self.history) + [{"role": "user", "parts": parts}]
        body: dict[str, Any] = {"contents": contents}
        if self.system_message:
            body["systemInstruction"] = {"parts": [{"text": self.system_message}]}
        mapped = []
        for t in self.tools or []:
            if isinstance(t, dict) and ("googleSearch" in t or "google_search" in t):
                mapped.append({"google_search": {}})
        if mapped:
            body["tools"] = mapped
        return body

    def _headers_and_url(self, method: str):
        if self.provider == "vertex_ai":
            token = self._vertex_token()
            project = self.vertex.get("vertex_project")
            location = self.vertex.get("vertex_location") or "us-central1"
            if not project:
                raise RuntimeError("vertex_project vacio")
            url = (
                f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
                f"/locations/{location}/publishers/google/models/{self.model}:{method}"
            )
            return url, {"Authorization": f"Bearer {token}"}, None
        if not self.api_key:
            raise RuntimeError("No hay API key de Gemini (active_llm_key / GOOGLE_API_KEY)")
        url = f"{API_BASE}/models/{self.model}:{method}"
        return url, {}, {"key": self.api_key}

    def _vertex_token(self) -> str:
        raw = self.vertex.get("vertex_credentials")
        if not raw:
            raise RuntimeError("Falta vertex_service_account_json")
        info = json.loads(raw) if isinstance(raw, str) else raw
        from google.oauth2 import service_account
        import google.auth.transport.requests
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token

    def _extract(self, data: dict):
        candidates = data.get("candidates") or []
        if not candidates:
            err = data.get("error") or data
            raise RuntimeError(f"Gemini sin candidates: {err}")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        texts, images = [], []
        for p in parts:
            if p.get("text"):
                texts.append(p["text"])
            inline = p.get("inlineData") or p.get("inline_data")
            if inline and inline.get("data"):
                images.append(inline["data"])
        meta = data.get("usageMetadata") or {}
        usage = Usage(meta.get("promptTokenCount", 0), meta.get("candidatesTokenCount", 0))
        return "\n".join(texts), images, usage

    async def send_message(self, message):
        parts = self._parts_from_message(message)
        url, headers, params = self._headers_and_url("generateContent")
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(url, params=params, headers=headers, json=self._body(parts))
            await self._raise_for_status(r)
            data = r.json()
        text, _, usage = self._extract(data)
        self.history.append({"role": "user", "parts": [
            {"text": p["text"]} if "text" in p else {"text": "[adjunto enviado]"}
            for p in parts
        ]})
        self.history.append({"role": "model", "parts": [{"text": text}]})
        return LlmResponse(text, usage)

    async def send_message_multimodal_response(self, message):
        parts = self._parts_from_message(message)
        url, headers, params = self._headers_and_url("generateContent")
        body = self._body(parts)
        body["generationConfig"] = {"responseModalities": ["TEXT", "IMAGE"]}
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(url, params=params, headers=headers, json=body)
            await self._raise_for_status(r)
            data = r.json()
        text, images, usage = self._extract(data)
        self.history.append({"role": "user", "parts": [
            {"text": p["text"]} if "text" in p else {"text": "[adjunto enviado]"}
            for p in parts
        ]})
        self.history.append({"role": "model", "parts": [{"text": text}]})
        self.last_usage = usage
        return text, images

    async def stream_message(self, message) -> AsyncIterator:
        parts = self._parts_from_message(message)
        url, headers, params = self._headers_and_url("streamGenerateContent")
        params = dict(params or {})
        params["alt"] = "sse"
        acc = []
        usage = Usage()
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("POST", url, params=params, headers=headers, json=self._body(parts)) as r:
                await self._raise_for_status(r)
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    data = json.loads(payload)
                    text, _, chunk_usage = self._extract(data)
                    if chunk_usage.input_tokens or chunk_usage.output_tokens:
                        usage = chunk_usage
                    if text:
                        acc.append(text)
                        yield TextDelta(text)
        full = "".join(acc)
        self.history.append({"role": "user", "parts": [
            {"text": p["text"]} if "text" in p else {"text": "[adjunto enviado]"}
            for p in parts
        ]})
        self.history.append({"role": "model", "parts": [{"text": full}]})
        yield StreamDone(usage, full)

    def send_message_stream(self, *args, **kwargs):
        raise RuntimeError("Usa stream_message (async)")
