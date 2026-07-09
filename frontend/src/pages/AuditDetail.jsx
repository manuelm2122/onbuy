import { useEffect, useState, useCallback, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowLeft,
  UploadCloud,
  FileText,
  Trash2,
  Sparkles,
  Download,
  LogOut,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/context/AuthContext";
import { api, BACKEND_URL, formatApiErrorDetail } from "@/lib/api";
import { StatusBadge } from "@/pages/Panel";

const CATEGORIES = [
  { value: "factura", label: "Factura / Comprobante" },
  { value: "estado_cuenta", label: "Estado de cuenta bancario" },
  { value: "recibo", label: "Recibo de mantenimiento" },
  { value: "contrato", label: "Contrato de servicios" },
  { value: "libro_actas", label: "Acta de asamblea" },
  { value: "presupuesto", label: "Presupuesto / Balance" },
  { value: "otro", label: "Otro documento" },
];

const catLabel = (v) => CATEGORIES.find((c) => c.value === v)?.label || "Otro";

const fmtSize = (b) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.ceil(b / 1024)} KB`);

export default function AuditDetail() {
  const { id } = useParams();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [audit, setAudit] = useState(null);
  const [docs, setDocs] = useState([]);
  const [category, setCategory] = useState("factura");
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [downloading, setDownloading] = useState(false);
  const fileRef = useRef(null);
  const streamBoxRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const [a, d] = await Promise.all([api.get(`/audits/${id}`), api.get(`/audits/${id}/documents`)]);
      setAudit(a.data);
      setDocs(d.data);
    } catch {
      toast.error("No se pudo cargar la auditoría");
      navigate("/panel");
    }
  }, [id, navigate]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (streamBoxRef.current) {
      streamBoxRef.current.scrollTop = streamBoxRef.current.scrollHeight;
    }
  }, [streamText]);

  const uploadFiles = async (fileList) => {
    if (!fileList?.length) return;
    setUploading(true);
    const fd = new FormData();
    for (const f of fileList) fd.append("files", f);
    fd.append("category", category);
    try {
      await api.post(`/audits/${id}/documents`, fd);
      toast.success(`${fileList.length} documento(s) subido(s)`);
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const deleteDoc = async (docId) => {
    try {
      await api.delete(`/documents/${docId}`);
      toast.success("Documento eliminado");
      load();
    } catch {
      toast.error("No se pudo eliminar");
    }
  };

  const runAnalysis = async () => {
    if (docs.length === 0) {
      toast.error("Sube al menos un documento antes de iniciar la auditoría");
      return;
    }
    setAnalyzing(true);
    setStreamText("");
    try {
      const res = await fetch(`${BACKEND_URL}/api/audits/${id}/analyze`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(formatApiErrorDetail(err.detail) || "Error al iniciar el análisis");
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let acc = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        acc += decoder.decode(value, { stream: true });
        setStreamText(acc);
      }
      if (acc.includes("[ERROR]")) {
        toast.error("El análisis terminó con errores");
      } else {
        toast.success("Auditoría completada con éxito");
      }
      load();
    } catch (err) {
      toast.error(err.message || "Error durante el análisis");
    } finally {
      setAnalyzing(false);
    }
  };

  const downloadReport = async () => {
    setDownloading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/audits/${id}/report`, { credentials: "include" });
      if (!res.ok) throw new Error("No se pudo generar el reporte");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Informe_Auditoria_${audit.condominium_name.replace(/\s+/g, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Reporte descargado");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDownloading(false);
    }
  };

  if (!audit)
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC]">
        <div className="w-8 h-8 border-2 border-[#0284C7] border-t-transparent rounded-full animate-spin" />
      </div>
    );

  const analysisContent = analyzing ? streamText : audit.analysis || streamText;

  return (
    <div className="min-h-screen bg-[#F8FAFC]">
      <header className="bg-[#020617] text-white">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
          <Link to="/" className="font-heading font-black text-lg tracking-tight">
            OnBuy<span className="text-[#0EA5E9]">Solutions</span>
          </Link>
          <div className="flex items-center gap-5">
            <span className="text-sm text-slate-300 hidden sm:block">{user?.name}</span>
            <button
              onClick={async () => {
                await logout();
                navigate("/");
              }}
              data-testid="detail-logout-btn"
              className="inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white transition-colors"
            >
              <LogOut size={16} /> Salir
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 lg:px-10 py-10">
        <Link to="/panel" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-[#0284C7] transition-colors" data-testid="back-to-panel-link">
          <ArrowLeft size={16} /> Volver al panel
        </Link>

        <div className="mt-6 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-4">
              <h1 className="font-heading font-black text-3xl tracking-tight text-[#0F172A]" data-testid="audit-detail-title">
                {audit.condominium_name}
              </h1>
              <StatusBadge status={audit.status} />
            </div>
            <p className="text-slate-500 text-sm mt-2">
              {[audit.address, audit.district].filter(Boolean).join(", ") || "Sin dirección"} · Período:{" "}
              {audit.period} · {docs.length} documento(s)
            </p>
          </div>
        </div>

        <Tabs defaultValue="documentos" className="mt-10">
          <TabsList className="bg-white border border-slate-200 p-1 h-auto">
            <TabsTrigger value="documentos" data-testid="tab-documentos" className="px-6 py-2.5 text-sm data-[state=active]:bg-[#0F172A] data-[state=active]:text-white">
              Documentos
            </TabsTrigger>
            <TabsTrigger value="analisis" data-testid="tab-analisis" className="px-6 py-2.5 text-sm data-[state=active]:bg-[#0F172A] data-[state=active]:text-white">
              Análisis IA
            </TabsTrigger>
            <TabsTrigger value="reporte" data-testid="tab-reporte" className="px-6 py-2.5 text-sm data-[state=active]:bg-[#0F172A] data-[state=active]:text-white">
              Reporte final
            </TabsTrigger>
          </TabsList>

          {/* DOCUMENTOS */}
          <TabsContent value="documentos" className="mt-8">
            <div className="grid lg:grid-cols-3 gap-6">
              <div className="bg-white border border-slate-200 p-6">
                <h3 className="font-heading font-bold text-[#0F172A]">Subir documentos</h3>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  PDF, JPG, PNG, WEBP, Excel o CSV. Máximo 20MB por archivo.
                </p>
                <div className="mt-5">
                  <label className="text-xs tracking-[0.2em] uppercase text-slate-500 font-semibold">Categoría</label>
                  <Select value={category} onValueChange={setCategory}>
                    <SelectTrigger className="mt-2 w-full" data-testid="doc-category-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((c) => (
                        <SelectItem key={c.value} value={c.value} data-testid={`category-option-${c.value}`}>
                          {c.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <label
                  className="mt-5 flex flex-col items-center justify-center border-2 border-dashed border-slate-300 hover:border-[#0284C7] p-8 cursor-pointer transition-colors group"
                  data-testid="upload-dropzone"
                >
                  <UploadCloud className="text-slate-400 group-hover:text-[#0284C7] transition-colors" size={32} strokeWidth={1.5} />
                  <span className="text-sm text-slate-500 mt-3 text-center">
                    {uploading ? "Subiendo…" : "Haz clic para seleccionar archivos"}
                  </span>
                  <input
                    ref={fileRef}
                    type="file"
                    multiple
                    accept=".pdf,.png,.jpg,.jpeg,.webp,.xlsx,.xls,.csv,.txt"
                    className="hidden"
                    disabled={uploading}
                    data-testid="file-input"
                    onChange={(e) => uploadFiles(Array.from(e.target.files))}
                  />
                </label>
              </div>

              <div className="lg:col-span-2 bg-white border border-slate-200">
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="font-heading font-bold text-[#0F172A]">Documentos cargados</h3>
                  <span className="text-xs text-slate-400">{docs.length} archivo(s)</span>
                </div>
                {docs.length === 0 ? (
                  <div className="p-12 text-center" data-testid="empty-docs-message">
                    <FileText className="mx-auto text-slate-300" size={36} strokeWidth={1.2} />
                    <p className="text-slate-500 text-sm mt-4">
                      Aún no hay documentos. Sube facturas, estados de cuenta y recibos para comenzar.
                    </p>
                  </div>
                ) : (
                  <ul className="divide-y divide-slate-100" data-testid="docs-list">
                    {docs.map((d) => (
                      <li key={d.id} className="px-6 py-4 flex items-center justify-between gap-4" data-testid={`doc-item-${d.id}`}>
                        <div className="flex items-center gap-3 min-w-0">
                          <FileText className="text-[#0284C7] shrink-0" size={20} strokeWidth={1.5} />
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-[#0F172A] truncate">{d.filename}</p>
                            <p className="text-xs text-slate-400">
                              {catLabel(d.category)} · {fmtSize(d.size)}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => deleteDoc(d.id)}
                          data-testid={`delete-doc-btn-${d.id}`}
                          className="text-slate-400 hover:text-red-600 transition-colors p-1 shrink-0"
                        >
                          <Trash2 size={16} />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </TabsContent>

          {/* ANÁLISIS */}
          <TabsContent value="analisis" className="mt-8">
            <div className="bg-white border border-slate-200">
              <div className="px-6 py-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-heading font-bold text-[#0F172A]">Auditoría con Inteligencia Artificial</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Google Gemini analizará los {docs.length} documento(s) y generará el informe completo.
                  </p>
                </div>
                <button
                  onClick={runAnalysis}
                  disabled={analyzing || docs.length === 0}
                  data-testid="run-analysis-btn"
                  className="inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-50 text-white font-semibold px-6 py-3 rounded-full text-sm transition-colors shrink-0"
                >
                  <Sparkles size={16} />
                  {analyzing ? "Auditando…" : audit.analysis ? "Volver a auditar" : "Iniciar auditoría IA"}
                </button>
              </div>

              {analyzing && (
                <div className="px-6 py-3 bg-sky-50 border-b border-sky-100 flex items-center gap-3" data-testid="analyzing-indicator">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#0284C7] analyzing-dot" />
                  <p className="text-xs text-sky-800 font-medium">
                    La IA está revisando tus documentos en tiempo real. Esto puede tomar varios minutos, no cierres esta pestaña…
                  </p>
                </div>
              )}

              <div ref={streamBoxRef} className="p-6 lg:p-10 max-h-[600px] overflow-y-auto" data-testid="analysis-content">
                {analysisContent ? (
                  <>
                    <div className="mb-6 flex items-start gap-3 bg-slate-50 border border-slate-200 p-4" data-testid="ai-transparency-notice">
                      <AlertTriangle className="text-slate-500 shrink-0 mt-0.5" size={16} />
                      <p className="text-[11px] text-slate-500 leading-relaxed">
                        Informe generado mediante algoritmos automatizados de IA (Ley N° 31814 y D.S. N°
                        115-2025-PCM). Debes revisar y validar su contenido (supervisión humana) antes de
                        formular denuncias formales o iniciar acciones legales.{" "}
                        <Link to="/uso-ia" target="_blank" className="text-[#0284C7] font-semibold hover:underline">
                          Ver Aviso de Uso de IA
                        </Link>
                      </p>
                    </div>
                    <div className="markdown-report">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysisContent}</ReactMarkdown>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-10">
                    <Sparkles className="mx-auto text-slate-300" size={36} strokeWidth={1.2} />
                    <p className="text-slate-500 text-sm mt-4 max-w-md mx-auto">
                      Cuando inicies la auditoría, verás aquí el análisis de la IA generándose en vivo:
                      hallazgos, irregularidades, recomendaciones y opinión del auditor.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* REPORTE */}
          <TabsContent value="reporte" className="mt-8">
            <div className="bg-white border border-slate-200 p-8 lg:p-12 max-w-3xl">
              <Download className="text-[#0284C7]" size={32} strokeWidth={1.5} />
              <h3 className="font-heading font-bold text-xl text-[#0F172A] mt-5">Informe final en PDF</h3>
              <p className="text-sm text-slate-600 leading-relaxed mt-3">
                Documento profesional con membrete de OnBuySolutions, datos del condominio, análisis
                completo, hallazgos con severidad, recomendaciones, opinión del auditor y código de
                verificación único. Elaborado conforme a la Ley N° 27157 y su Reglamento, puede
                usarse para el fin que decidas: juntas de propietarios, administración o
                procedimientos legales.
              </p>
              {!audit.analysis ? (
                <div className="mt-6 flex items-start gap-3 bg-amber-50 border border-amber-200 p-4" data-testid="report-warning">
                  <AlertTriangle className="text-amber-600 shrink-0" size={18} />
                  <p className="text-xs text-amber-800 leading-relaxed">
                    Primero debes ejecutar el análisis con IA en la pestaña "Análisis IA". El reporte
                    se genera a partir de ese análisis.
                  </p>
                </div>
              ) : (
                <button
                  onClick={downloadReport}
                  disabled={downloading}
                  data-testid="download-report-btn"
                  className="mt-8 inline-flex items-center gap-2 bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold px-8 py-4 rounded-full text-sm transition-colors"
                >
                  <Download size={16} />
                  {downloading ? "Generando PDF…" : "Descargar informe PDF"}
                </button>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
