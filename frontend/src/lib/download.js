import { BACKEND_URL, formatApiErrorDetail } from "@/lib/api";

export async function downloadFromApi(path, { method = "GET", body, fallback = "descarga" } = {}) {
  const res = await fetch(`${BACKEND_URL}/api${path}`, {
    method,
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ? formatApiErrorDetail(err.detail) : "No se pudo generar la descarga");
  }
  const match = (res.headers.get("Content-Disposition") || "").match(/filename="(.+?)"/);
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = match ? match[1] : fallback;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const toFormData = (fields, evidence) => {
  const fd = new FormData();
  Object.entries(fields).forEach(([k, v]) => v !== "" && v != null && fd.append(k, v));
  if (evidence?.file) fd.append("file", evidence.file);
  else if (evidence?.storedName) fd.append("stored_name", evidence.storedName);
  return fd;
};
