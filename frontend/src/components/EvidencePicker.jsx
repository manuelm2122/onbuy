import { useEffect, useRef, useState } from "react";
import { FileText, Paperclip, X } from "lucide-react";
import { api, BACKEND_URL } from "@/lib/api";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,.csv,.txt,.xlsx,.xls,.mp4,.mov,.webm,.avi,.mp3,.wav,.m4a,.ogg";

export const inputCls = "w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2 text-sm transition-colors bg-white";
export const fmtDay = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" });

export const FileChip = ({ caseId, file }) =>
  file ? (
    <a href={`${BACKEND_URL}/api/cases/${caseId}/files/${file.stored_name}`} target="_blank" rel="noreferrer" data-testid={`evidence-link-${file.stored_name}`} className="inline-flex items-center gap-1 text-[11px] text-[#0284C7] hover:underline max-w-full">
      <FileText size={11} className="shrink-0" /> <span className="truncate">{file.filename}</span>
    </a>
  ) : null;

export const EvidencePicker = ({ caseId, value, onChange, label = "Prueba o comprobante (opcional)" }) => {
  const [files, setFiles] = useState([]);
  const inputRef = useRef(null);

  useEffect(() => {
    api.get(`/cases/${caseId}/evidence`).then(({ data }) => setFiles(data)).catch(() => setFiles([]));
  }, [caseId, value]);

  return (
    <div>
      <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">{label}</label>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        {value?.file ? (
          <span className="inline-flex items-center gap-1.5 bg-sky-50 border border-sky-200 text-sky-800 text-xs px-3 py-1.5 rounded-full" data-testid="evidence-new-file">
            <FileText size={11} /> {value.file.name}
            <button type="button" onClick={() => onChange(null)} aria-label="Quitar archivo"><X size={11} /></button>
          </span>
        ) : (
          <select value={value?.storedName || ""} onChange={(e) => onChange(e.target.value ? { storedName: e.target.value } : null)} data-testid="evidence-select" className={`${inputCls} flex-1 min-w-[180px]`}>
            <option value="">Sin archivo</option>
            {files.map((f) => <option key={f.stored_name} value={f.stored_name}>{f.filename} ({f.origin})</option>)}
          </select>
        )}
        <input ref={inputRef} type="file" accept={ACCEPT} className="hidden" data-testid="evidence-file-input" onChange={(e) => { if (e.target.files[0]) onChange({ file: e.target.files[0] }); e.target.value = ""; }} />
        <button type="button" onClick={() => inputRef.current?.click()} data-testid="evidence-upload-btn" className="inline-flex items-center gap-1.5 border border-slate-300 hover:border-[#0284C7] hover:text-[#0284C7] text-slate-600 font-semibold px-3 py-2 rounded-full text-xs transition-colors">
          <Paperclip size={12} /> Subir archivo
        </button>
      </div>
    </div>
  );
};
