import { useRef, useState } from "react";
import { DatabaseBackup, Download, Upload } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";

const CHUNK_SIZE = 5 * 1024 * 1024;

export const BackupPanel = () => {
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [file, setFile] = useState(null);
  const [confirm, setConfirm] = useState("");
  const fileRef = useRef(null);

  const exportBackup = async () => {
    setExporting(true);
    try {
      const { data } = await api.get("/admin/backup/export", { responseType: "blob", timeout: 300000 });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "");
      a.href = url;
      a.download = `onbuysolutions-backup-${stamp}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Backup descargado. Guárdalo en un lugar seguro: contiene claves API y datos de clientes.");
    } catch (err) {
      toast.error("No se pudo generar el backup");
    } finally {
      setExporting(false);
    }
  };

  const importBackup = async () => {
    if (!file) return;
    setImporting(true);
    setProgress(0);
    try {
      const uploadId = crypto.randomUUID().replace(/-/g, "");
      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
      for (let i = 0; i < totalChunks; i++) {
        const fd = new FormData();
        fd.append("upload_id", uploadId);
        fd.append("chunk_index", i);
        fd.append("file", file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE), "chunk");
        await api.post("/admin/backup/import/chunk", fd, { timeout: 120000 });
        setProgress(Math.round(((i + 1) / totalChunks) * 90));
      }
      const { data } = await api.post(
        "/admin/backup/import/complete",
        { upload_id: uploadId, total_chunks: totalChunks, confirm },
        { timeout: 300000 }
      );
      setProgress(100);
      toast.success(data.message, { duration: 8000 });
      setFile(null);
      setConfirm("");
      if (fileRef.current) fileRef.current.value = "";
      setTimeout(() => window.location.reload(), 3000);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setImporting(false);
    }
  };

  const canImport = file && confirm.trim().toUpperCase() === "RESTAURAR" && !importing;

  return (
    <div className="bg-white border border-slate-200 p-6" data-testid="backup-panel">
      <div className="flex items-center gap-3">
        <DatabaseBackup className="text-[#0284C7]" size={22} strokeWidth={1.5} />
        <h3 className="font-heading font-bold text-[#0F172A]">Copia de seguridad</h3>
      </div>
      <p className="text-xs text-slate-500 mt-2 leading-relaxed">
        Exporta TODO (base de datos + documentos subidos + claves API) en un archivo .zip para migrar a una
        nueva instalación o guardar un respaldo. La importación <b>reemplaza por completo</b> los datos actuales.
      </p>

      <div className="mt-5 space-y-5">
        <button
          onClick={exportBackup}
          disabled={exporting}
          data-testid="backup-export-btn"
          className="inline-flex items-center gap-2 bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold px-6 py-3 rounded-full text-sm transition-colors"
        >
          <Download size={16} />
          {exporting ? "Generando backup…" : "Exportar backup (.zip)"}
        </button>

        <div className="border-t border-slate-200 pt-5">
          <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Importar backup</label>
          <input
            ref={fileRef}
            type="file"
            accept=".zip"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            data-testid="backup-import-file-input"
            className="mt-1 w-full border border-slate-300 px-3 py-2.5 text-sm bg-white file:mr-3 file:border-0 file:bg-[#0284C7] file:text-white file:px-3 file:py-1 file:rounded-full file:text-xs file:cursor-pointer"
          />
          {file && (
            <>
              <p className="text-[10px] text-slate-500 mt-2" data-testid="backup-selected-file">
                {file.name} — {(file.size / 1024 / 1024).toFixed(1)} MB
              </p>
              <div className="mt-3 bg-red-50 border border-red-200 p-3 text-xs text-red-700 leading-relaxed">
                ⚠️ Esta acción <b>eliminará todos los datos actuales</b> (usuarios, auditorías, casos, pagos, configuración y
                archivos) y los reemplazará por los del backup. Escribe <b>RESTAURAR</b> para confirmar.
              </div>
              <input
                type="text"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder='Escribe RESTAURAR'
                data-testid="backup-confirm-input"
                className="mt-2 w-full border border-slate-300 focus:border-red-500 outline-none px-3 py-2.5 text-sm transition-colors bg-white"
              />
            </>
          )}
          {importing && (
            <div className="mt-3">
              <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                <div className="h-full bg-[#0284C7] transition-all" style={{ width: `${progress}%` }} data-testid="backup-progress" />
              </div>
              <p className="text-[10px] text-slate-500 mt-1">{progress < 90 ? `Subiendo… ${progress}%` : "Restaurando datos…"}</p>
            </div>
          )}
          <button
            onClick={importBackup}
            disabled={!canImport}
            data-testid="backup-import-btn"
            className="mt-3 inline-flex items-center gap-2 bg-red-600 hover:bg-red-700 disabled:opacity-40 text-white font-semibold px-6 py-3 rounded-full text-sm transition-colors"
          >
            <Upload size={16} />
            {importing ? "Importando…" : "Importar y reemplazar todo"}
          </button>
        </div>
      </div>
    </div>
  );
};
