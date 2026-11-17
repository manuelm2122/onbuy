import { BACKEND_URL, formatApiErrorDetail } from "@/lib/api";

const chatError = (message, retryable, status) => Object.assign(new Error(message), { retryable, status });

export const newClientMsgId = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export async function postCaseChat({ caseId, text, files, clientMsgId, onChunk }) {
  const fd = new FormData();
  fd.append("text", text);
  fd.append("client_msg_id", clientMsgId);
  files.forEach((f) => fd.append("files", f));
  let res;
  try {
    res = await fetch(`${BACKEND_URL}/api/cases/${caseId}/chat`, { method: "POST", credentials: "include", body: fd });
  } catch {
    throw chatError("No hubo conexión con el servidor", true);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = body.detail ? formatApiErrorDetail(body.detail) : `El servidor respondió con error ${res.status}`;
    throw chatError(message, res.status >= 500 || res.status === 408, res.status);
  }
  let acc = "";
  try {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      acc += decoder.decode(value, { stream: true });
      onChunk(acc.split("[ERROR]")[0]);
    }
  } catch {
    throw chatError("La conexión se cortó mientras llegaba la respuesta", true);
  }
  if (acc.includes("[ERROR]")) throw chatError(acc.split("[ERROR]")[1].trim() || "La respuesta se interrumpió", true);
  if (!acc.trim()) throw chatError("El agente no devolvió respuesta", true);
  return acc;
}
