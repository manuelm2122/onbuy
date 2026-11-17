import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, FileStack, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { downloadFromApi } from "@/lib/download";
import { inputCls } from "@/components/EvidencePicker";

const PRINTABLE = (mime) => mime === "application/pdf" || mime?.startsWith("image/");

export const CaseBundle = ({ caseId, open, onOpenChange }) => {
  const [docs, setDocs] = useState(null);
  const [files, setFiles] = useState([]);
  const [docKey, setDocKey] = useState("");
  const [includeFacts, setIncludeFacts] = useState(false);
  const [includeLedger, setIncludeLedger] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDocs(null);
    Promise.all([api.get(`/cases/${caseId}/documents`), api.get(`/cases/${caseId}/evidence`)])
      .then(([d, e]) => {
        setDocs(d.data);
        setDocKey(d.data.length ? `${d.data[d.data.length - 1].message_id}:${d.data[d.data.length - 1].doc_index}` : "");
        setFiles(e.data.map((f) => ({ ...f, selected: f.origin !== "Generado por IA" })));
      })
      .catch(() => {
        toast.error("No se pudo cargar el contenido del caso");
        setDocs([]);
      });
  }, [open, caseId]);

  const move = (i, dir) =>
    setFiles((prev) => {
      const next = [...prev];
      [next[i], next[i + dir]] = [next[i + dir], next[i]];
      return next;
    });

  const generate = async () => {
    setBusy(true);
    try {
      const [message_id, doc_index] = docKey ? docKey.split(":") : [null, null];
      await downloadFromApi(`/cases/${caseId}/bundle`, {
        method: "POST",
        fallback: "Expediente.pdf",
        body: {
          message_id,
          doc_index: doc_index === null ? null : Number(doc_index),
          include_facts: includeFacts,
          include_ledger: includeLedger,
          files: files.filter((f) => f.selected).map((f) => f.stored_name),
        },
      });
      toast.success("Expediente descargado");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  const selected = files.filter((f) => f.selected);
  let annexIndex = -1;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl">Expediente listo para presentar</DialogTitle>
          <DialogDescription>Un solo PDF con carátula, índice, tu escrito y los anexos numerados y foliados. No descuenta mensajes.</DialogDescription>
        </DialogHeader>
        {!docs ? (
          <div className="py-8 flex justify-center"><Loader2 className="animate-spin text-[#0284C7]" size={20} /></div>
        ) : (
          <div className="space-y-5">
            <div>
              <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Escrito principal</label>
              <select value={docKey} onChange={(e) => setDocKey(e.target.value)} data-testid="bundle-doc-select" className={`${inputCls} mt-1`}>
                <option value="">Sin escrito (solo anexos)</option>
                {docs.map((d) => <option key={`${d.message_id}:${d.doc_index}`} value={`${d.message_id}:${d.doc_index}`}>{d.title}</option>)}
              </select>
              {docs.length === 0 && <p className="text-[10px] text-slate-400 mt-1">Aún no hay documentos redactados. Pídele al agente que redacte tu carta, demanda o denuncia y aparecerá aquí.</p>}
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={includeFacts} onChange={(e) => setIncludeFacts(e.target.checked)} data-testid="bundle-facts-checkbox" className="accent-[#0284C7]" /> Incluir la relación de hechos
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={includeLedger} onChange={(e) => setIncludeLedger(e.target.checked)} data-testid="bundle-ledger-checkbox" className="accent-[#0284C7]" /> Incluir el estado de cuenta
              </label>
            </div>
            <div>
              <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Anexos ({selected.length} seleccionados). Ordénalos con las flechas.</label>
              {files.length === 0 ? (
                <p className="text-xs text-slate-500 mt-2" data-testid="bundle-no-files">Este caso aún no tiene archivos. Súbelos en el chat, en el cuaderno de hechos o en el registro de pagos.</p>
              ) : (
                <ul className="mt-2 border border-slate-200 divide-y divide-slate-100" data-testid="bundle-files">
                  {files.map((f, i) => {
                    if (f.selected) annexIndex += 1;
                    return (
                      <li key={f.stored_name} className="flex items-center gap-3 px-3 py-2" data-testid={`bundle-file-${i}`}>
                        <input type="checkbox" checked={f.selected} onChange={() => setFiles((prev) => prev.map((x, j) => (j === i ? { ...x, selected: !x.selected } : x)))} data-testid={`bundle-file-check-${i}`} className="accent-[#0284C7] shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-[#0F172A] truncate">{f.filename}</p>
                          <p className="text-[10px] text-slate-400">
                            {f.selected && <b className="text-[#0284C7]">Anexo 1-{String.fromCharCode(65 + (annexIndex % 26))} · </b>}
                            {f.origin}{!PRINTABLE(f.mime_type) && " · no imprimible: irá solo su carátula"}
                          </p>
                        </div>
                        <button onClick={() => move(i, -1)} disabled={i === 0} aria-label="Subir" data-testid={`bundle-file-up-${i}`} className="text-slate-400 hover:text-[#0284C7] disabled:opacity-30 transition-colors"><ArrowUp size={14} /></button>
                        <button onClick={() => move(i, 1)} disabled={i === files.length - 1} aria-label="Bajar" data-testid={`bundle-file-down-${i}`} className="text-slate-400 hover:text-[#0284C7] disabled:opacity-30 transition-colors"><ArrowDown size={14} /></button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
            <button onClick={generate} disabled={busy || (!docKey && !includeFacts && !includeLedger && selected.length === 0)} data-testid="bundle-generate-btn" className="w-full inline-flex items-center justify-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-50 text-white font-semibold py-3 rounded-full text-sm transition-colors">
              {busy ? <Loader2 className="animate-spin" size={15} /> : <FileStack size={15} />} {busy ? "Armando el expediente…" : "Generar expediente en PDF"}
            </button>
            <p className="text-[10px] text-slate-400 leading-relaxed">Revisa el PDF antes de presentarlo. Cada entidad puede exigir su propio formato, firmas o copias legalizadas.</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
