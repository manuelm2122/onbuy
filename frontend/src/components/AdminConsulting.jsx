import { useEffect, useState, useCallback, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Scale,
  Plus,
  Trash2,
  Pencil,
  Send,
  Paperclip,
  FileText,
  Download,
  ImagePlus,
  Loader2,
  FolderOpen,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, BACKEND_URL, formatApiErrorDetail } from "@/lib/api";

const STATUS_META = {
  activo: { label: "Activo", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  archivado: { label: "Archivado", cls: "bg-slate-100 text-slate-500 border-slate-200" },
  cerrado: { label: "Cerrado", cls: "bg-red-50 text-red-700 border-red-200" },
};

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,.csv,.txt,.xlsx,.xls,.mp4,.mov,.webm,.avi,.mp3,.wav,.m4a,.ogg";

const fmtDate = (iso) =>
  new Date(iso).toLocaleString("es-PE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

const AttachmentChip = ({ att, caseId }) => {
  const url = `${BACKEND_URL}/api/admin/cases/${caseId}/files/${att.stored_name}`;
  if (att.mime_type?.startsWith("image/")) {
    return (
      <a href={url} target="_blank" rel="noreferrer" data-testid={`attachment-image-${att.stored_name}`}>
        <img src={url} alt={att.filename} className="max-h-64 rounded border border-slate-200 mt-2" />
      </a>
    );
  }
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      data-testid={`attachment-file-${att.stored_name}`}
      className="inline-flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium px-3 py-1.5 rounded-full mt-2 mr-2 transition-colors"
    >
      <FileText size={12} /> {att.filename}
    </a>
  );
};

const cleanContent = (text) =>
  (text || "")
    .replace(/<<<DOCUMENTO:\s*(.*?)>>>/g, "\n---\n### $1\n")
    .replace(/<<<FIN_DOCUMENTO>>>/g, "\n---\n");

const Message = ({ m, caseId, onExport, exporting }) => {
  const isUser = m.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`} data-testid={`case-message-${m.id || "streaming"}`}>
      <div
        className={`max-w-[85%] px-5 py-4 text-sm leading-relaxed ${
          isUser
            ? "bg-[#0F172A] text-white rounded-2xl rounded-br-sm"
            : "bg-white border border-slate-200 text-slate-800 rounded-2xl rounded-bl-sm"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{m.content}</p>
        ) : (
          <div className="markdown-report text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{cleanContent(m.content)}</ReactMarkdown>
          </div>
        )}
        {(m.attachments || []).map((a) => (
          <AttachmentChip key={a.stored_name} att={a} caseId={caseId} />
        ))}
        {!isUser && m.id && m.content && (
          <div className="mt-3 flex flex-wrap gap-2">
            {m.has_document && (
              <button
                onClick={() => onExport(m.id, true)}
                disabled={exporting === m.id}
                data-testid={`export-document-btn-${m.id}`}
                className="inline-flex items-center gap-1.5 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-50 text-white font-semibold px-3.5 py-1.5 rounded-full text-[11px] transition-colors"
              >
                <FileText size={11} />
                {exporting === m.id ? "Exportando…" : "Descargar documento (PDF)"}
              </button>
            )}
            <button
              onClick={() => onExport(m.id, false)}
              disabled={exporting === m.id}
              data-testid={`export-pdf-btn-${m.id}`}
              className="inline-flex items-center gap-1.5 border border-slate-300 hover:border-[#0284C7] hover:text-[#0284C7] disabled:opacity-50 text-slate-500 font-semibold px-3 py-1.5 rounded-full text-[11px] transition-colors"
            >
              <Download size={11} />
              {m.has_document ? "Respuesta completa" : "Exportar PDF"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export const AdminConsulting = () => {
  const [cases, setCases] = useState(null);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [pendingFiles, setPendingFiles] = useState([]);
  const [sending, setSending] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [exporting, setExporting] = useState(null);
  const [newDialog, setNewDialog] = useState(false);
  const [editDialog, setEditDialog] = useState(false);
  const [imgDialog, setImgDialog] = useState(false);
  const [libDialog, setLibDialog] = useState(false);
  const [libraryDocs, setLibraryDocs] = useState(null);
  const [libExporting, setLibExporting] = useState(null);
  const [caseForm, setCaseForm] = useState({ title: "", description: "" });
  const [imgPrompt, setImgPrompt] = useState("");
  const [generatingImg, setGeneratingImg] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef(null);
  const bottomRef = useRef(null);

  const loadCases = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/cases");
      setCases(data);
      return data;
    } catch {
      toast.error("No se pudieron cargar los casos");
      return [];
    }
  }, []);

  const openCase = useCallback(async (id) => {
    try {
      const { data } = await api.get(`/admin/cases/${id}`);
      setSelected(data.case);
      setMessages(data.messages);
    } catch {
      toast.error("No se pudo abrir el caso");
    }
  }, []);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

  const createCase = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await api.post("/admin/cases", caseForm);
      toast.success("Caso creado");
      setNewDialog(false);
      setCaseForm({ title: "", description: "" });
      await loadCases();
      openCase(data.id);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const updateCase = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await api.put(`/admin/cases/${selected.id}`, caseForm);
      setSelected(data);
      toast.success("Caso actualizado");
      setEditDialog(false);
      loadCases();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const setStatus = async (status) => {
    try {
      const { data } = await api.put(`/admin/cases/${selected.id}`, { status });
      setSelected(data);
      loadCases();
      toast.success(`Caso marcado como ${STATUS_META[status].label.toLowerCase()}`);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    }
  };

  const deleteCase = async (c, e) => {
    e?.stopPropagation();
    if (!window.confirm(`¿Eliminar el caso "${c.title}" con todo su historial y archivos? Esta acción es irreversible.`)) return;
    try {
      const { data } = await api.delete(`/admin/cases/${c.id}`);
      toast.success(data.message);
      if (selected?.id === c.id) {
        setSelected(null);
        setMessages([]);
      }
      loadCases();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    }
  };

  const sendMessage = async () => {
    if ((!input.trim() && pendingFiles.length === 0) || sending) return;
    setSending(true);
    const text = input.trim();
    const localFiles = pendingFiles;
    setInput("");
    setPendingFiles([]);
    setMessages((prev) => [
      ...prev,
      { id: `local-${Date.now()}`, role: "user", content: text || "(archivos adjuntos)", attachments: [] },
    ]);
    setStreamText("");
    try {
      const fd = new FormData();
      fd.append("text", text);
      localFiles.forEach((f) => fd.append("files", f));
      const res = await fetch(`${BACKEND_URL}/api/admin/cases/${selected.id}/chat`, {
        method: "POST",
        credentials: "include",
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(formatApiErrorDetail(err.detail) || "Error al enviar el mensaje");
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
      if (acc.includes("[ERROR]")) toast.error("La respuesta terminó con errores");
      await openCase(selected.id);
      loadCases();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setStreamText("");
      setSending(false);
    }
  };

  const generateImage = async (e) => {
    e.preventDefault();
    setGeneratingImg(true);
    try {
      await api.post(`/admin/cases/${selected.id}/generate-image`, { prompt: imgPrompt });
      toast.success("Imagen generada y añadida al caso");
      setImgDialog(false);
      setImgPrompt("");
      openCase(selected.id);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setGeneratingImg(false);
    }
  };

  const openLibrary = async () => {
    setLibDialog(true);
    setLibraryDocs(null);
    try {
      const { data } = await api.get(`/admin/cases/${selected.id}/documents`);
      setLibraryDocs(data);
    } catch {
      toast.error("No se pudo cargar la biblioteca de documentos");
      setLibraryDocs([]);
    }
  };

  const downloadLibraryDoc = async (doc) => {
    const key = `${doc.message_id}-${doc.doc_index}`;
    setLibExporting(key);
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/cases/${selected.id}/export-pdf`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: doc.message_id, only_document: true, doc_index: doc.doc_index }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(formatApiErrorDetail(err.detail) || "No se pudo generar el PDF");
      }
      const cd = res.headers.get("Content-Disposition") || "";
      const match = cd.match(/filename="(.+)"/);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = match ? match[1] : `Documento_${doc.title.replace(/[^\w-]/g, "_").slice(0, 40)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(`"${doc.title}" descargado en PDF`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLibExporting(null);
    }
  };

  const exportPdf = async (messageId, onlyDocument = false) => {
    setExporting(messageId);
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/cases/${selected.id}/export-pdf`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: messageId, only_document: onlyDocument }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(formatApiErrorDetail(err.detail) || "No se pudo generar el PDF");
      }
      const cd = res.headers.get("Content-Disposition") || "";
      const match = cd.match(/filename="(.+)"/);
      const filename = match ? match[1] : `Consultoria_${selected.title.replace(/[^\w-]/g, "_").slice(0, 40)}.pdf`;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(onlyDocument ? "Documento limpio descargado en PDF" : "PDF descargado");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="grid lg:grid-cols-[320px_1fr] gap-6" data-testid="consulting-panel">
      {/* Lista de casos */}
      <div className="bg-white border border-slate-200 flex flex-col h-[72vh]">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-heading font-bold text-[#0F172A] text-sm flex items-center gap-2">
            <Scale size={16} className="text-[#0284C7]" /> Casos
          </h3>
          <button
            onClick={() => {
              setCaseForm({ title: "", description: "" });
              setNewDialog(true);
            }}
            data-testid="new-case-btn"
            className="inline-flex items-center gap-1.5 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-3.5 py-2 rounded-full text-xs transition-colors"
          >
            <Plus size={14} /> Nuevo caso
          </button>
        </div>
        <div className="flex-1 overflow-y-auto" data-testid="cases-list">
          {!cases ? (
            <div className="p-8 flex justify-center">
              <Loader2 className="animate-spin text-[#0284C7]" size={20} />
            </div>
          ) : cases.length === 0 ? (
            <div className="p-8 text-center" data-testid="empty-cases">
              <FolderOpen className="mx-auto text-slate-300" size={32} strokeWidth={1.2} />
              <p className="text-xs text-slate-500 mt-3">
                Crea tu primer caso para conversar con el consultor IA (abogado civil, penal y contador).
              </p>
            </div>
          ) : (
            cases.map((c) => (
              <div
                key={c.id}
                onClick={() => openCase(c.id)}
                data-testid={`case-item-${c.id}`}
                className={`px-4 py-3.5 border-b border-slate-50 cursor-pointer transition-colors group ${
                  selected?.id === c.id ? "bg-sky-50 border-l-2 border-l-[#0284C7]" : "hover:bg-slate-50"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="font-semibold text-[#0F172A] text-sm truncate">{c.title}</p>
                  <button
                    onClick={(e) => deleteCase(c, e)}
                    data-testid={`delete-case-btn-${c.id}`}
                    className="text-slate-300 hover:text-red-600 transition-colors shrink-0"
                    title="Eliminar caso"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className={`inline-flex text-[10px] font-semibold px-2 py-0.5 rounded-full border ${STATUS_META[c.status]?.cls || ""}`}>
                    {STATUS_META[c.status]?.label || c.status}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {c.message_count} msj · {fmtDate(c.updated_at)}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Chat del caso */}
      {!selected ? (
        <div className="bg-white border border-dashed border-slate-300 h-[72vh] flex flex-col items-center justify-center text-center px-8" data-testid="no-case-selected">
          <Scale className="text-slate-300" size={48} strokeWidth={1} />
          <h3 className="font-heading font-bold text-[#0F172A] mt-5">Consultoría legal y contable con IA</h3>
          <p className="text-sm text-slate-500 mt-2 max-w-md leading-relaxed">
            Selecciona un caso o crea uno nuevo. El consultor actúa como abogado civil, abogado penal y
            contador peruano: analiza documentos, imágenes, audios y videos, busca normativa en la web y
            redacta documentos listos para exportar a PDF.
          </p>
        </div>
      ) : (
        <div className="bg-[#F8FAFC] border border-slate-200 h-[72vh] flex flex-col">
          {/* Header del caso */}
          <div className="bg-white border-b border-slate-200 px-5 py-3.5 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="font-heading font-bold text-[#0F172A] text-sm truncate" data-testid="case-title">
                {selected.title}
              </p>
              {selected.description && <p className="text-xs text-slate-400 truncate">{selected.description}</p>}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Select value={selected.status} onValueChange={setStatus}>
                <SelectTrigger className="h-8 text-xs w-[120px]" data-testid="case-status-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="activo" data-testid="case-status-activo">Activo</SelectItem>
                  <SelectItem value="archivado" data-testid="case-status-archivado">Archivado</SelectItem>
                  <SelectItem value="cerrado" data-testid="case-status-cerrado">Cerrado</SelectItem>
                </SelectContent>
              </Select>
              <button
                onClick={() => {
                  setCaseForm({ title: selected.title, description: selected.description });
                  setEditDialog(true);
                }}
                data-testid="edit-case-btn"
                className="text-slate-400 hover:text-[#0284C7] transition-colors p-1.5"
                title="Editar caso"
              >
                <Pencil size={15} />
              </button>
              <button
                onClick={openLibrary}
                data-testid="library-btn"
                className="inline-flex items-center gap-1.5 border border-slate-300 hover:border-[#0284C7] hover:text-[#0284C7] text-slate-500 font-semibold px-3 py-1.5 rounded-full text-xs transition-colors"
              >
                <FolderOpen size={13} /> Documentos
              </button>
              <button
                onClick={() => setImgDialog(true)}
                data-testid="generate-image-btn"
                className="inline-flex items-center gap-1.5 border border-slate-300 hover:border-[#0284C7] hover:text-[#0284C7] text-slate-500 font-semibold px-3 py-1.5 rounded-full text-xs transition-colors"
              >
                <ImagePlus size={13} /> Imagen IA
              </button>
            </div>
          </div>

          {/* Mensajes */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4" data-testid="case-messages">
            {messages.length === 0 && !streamText && (
              <div className="text-center py-10" data-testid="empty-case-messages">
                <p className="text-sm text-slate-400">
                  Escribe tu consulta o adjunta documentos para empezar el expediente.
                </p>
              </div>
            )}
            {messages.map((m) => (
              <Message key={m.id} m={m} caseId={selected.id} onExport={exportPdf} exporting={exporting} />
            ))}
            {streamText && (
              <Message m={{ role: "assistant", content: streamText, attachments: [] }} caseId={selected.id} onExport={() => {}} exporting={null} />
            )}
            {sending && !streamText && (
              <div className="flex items-center gap-2 text-xs text-slate-400 pl-2" data-testid="agent-thinking">
                <Loader2 className="animate-spin" size={14} /> El consultor está analizando…
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="bg-white border-t border-slate-200 p-4">
            {pendingFiles.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2" data-testid="pending-files">
                {pendingFiles.map((f, i) => (
                  <span key={i} className="inline-flex items-center gap-1.5 bg-sky-50 border border-sky-200 text-sky-800 text-xs px-3 py-1 rounded-full">
                    <FileText size={11} /> {f.name}
                    <button onClick={() => setPendingFiles(pendingFiles.filter((_, j) => j !== i))} data-testid={`remove-pending-file-${i}`}>
                      <X size={11} />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div className="flex items-end gap-2">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept={ACCEPT}
                className="hidden"
                data-testid="case-file-input"
                onChange={(e) => {
                  setPendingFiles([...pendingFiles, ...Array.from(e.target.files)]);
                  e.target.value = "";
                }}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={sending}
                data-testid="attach-file-btn"
                className="shrink-0 text-slate-400 hover:text-[#0284C7] disabled:opacity-40 transition-colors p-2.5"
                title="Adjuntar archivos (PDF, imágenes, Excel, audio, video)"
              >
                <Paperclip size={18} />
              </button>
              <textarea
                rows={2}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Consulta al abogado civil, penal y contador… (Enter para enviar)"
                data-testid="case-chat-input"
                className="flex-1 border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors resize-none rounded-xl"
              />
              <button
                onClick={sendMessage}
                disabled={sending || (!input.trim() && pendingFiles.length === 0)}
                data-testid="send-message-btn"
                className="shrink-0 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-50 text-white p-3 rounded-full transition-colors"
              >
                {sending ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Dialogo nuevo caso */}
      <Dialog open={newDialog} onOpenChange={setNewDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">Nuevo caso</DialogTitle>
            <DialogDescription>Cada caso es un expediente independiente con su propia memoria y archivos.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createCase} className="space-y-4 mt-2">
            <input
              required
              value={caseForm.title}
              onChange={(e) => setCaseForm({ ...caseForm, title: e.target.value })}
              placeholder="Título del caso *"
              data-testid="case-title-input"
              className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors"
            />
            <textarea
              rows={3}
              value={caseForm.description}
              onChange={(e) => setCaseForm({ ...caseForm, description: e.target.value })}
              placeholder="Descripción breve del caso (opcional)"
              data-testid="case-description-input"
              className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors resize-none"
            />
            <button
              type="submit"
              disabled={saving}
              data-testid="case-create-submit-btn"
              className="w-full bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold py-3 rounded-full text-sm transition-colors"
            >
              {saving ? "Creando…" : "Crear caso"}
            </button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dialogo editar caso */}
      <Dialog open={editDialog} onOpenChange={setEditDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">Editar caso</DialogTitle>
            <DialogDescription>Actualiza el título o la descripción del expediente.</DialogDescription>
          </DialogHeader>
          <form onSubmit={updateCase} className="space-y-4 mt-2">
            <input
              required
              value={caseForm.title}
              onChange={(e) => setCaseForm({ ...caseForm, title: e.target.value })}
              data-testid="case-edit-title-input"
              className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors"
            />
            <textarea
              rows={3}
              value={caseForm.description}
              onChange={(e) => setCaseForm({ ...caseForm, description: e.target.value })}
              data-testid="case-edit-description-input"
              className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors resize-none"
            />
            <button
              type="submit"
              disabled={saving}
              data-testid="case-edit-submit-btn"
              className="w-full bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold py-3 rounded-full text-sm transition-colors"
            >
              {saving ? "Guardando…" : "Guardar cambios"}
            </button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dialogo biblioteca de documentos */}
      <Dialog open={libDialog} onOpenChange={setLibDialog}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">Biblioteca de documentos</DialogTitle>
            <DialogDescription>
              Todos los documentos redactados por el consultor en este expediente, listos para descargar en PDF.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[50vh] overflow-y-auto -mx-1 px-1" data-testid="library-list">
            {!libraryDocs ? (
              <div className="py-10 flex justify-center">
                <Loader2 className="animate-spin text-[#0284C7]" size={20} />
              </div>
            ) : libraryDocs.length === 0 ? (
              <div className="py-10 text-center" data-testid="library-empty">
                <FileText className="mx-auto text-slate-300" size={32} strokeWidth={1.2} />
                <p className="text-xs text-slate-500 mt-3 max-w-xs mx-auto leading-relaxed">
                  Aún no hay documentos redactados en este caso. Pídele al consultor que redacte una carta,
                  denuncia, contrato o informe y aparecerá aquí automáticamente.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {libraryDocs.map((d) => {
                  const key = `${d.message_id}-${d.doc_index}`;
                  return (
                    <li key={key} className="py-3.5 flex items-center justify-between gap-3" data-testid={`library-doc-${key}`}>
                      <div className="flex items-start gap-3 min-w-0">
                        <FileText className="text-[#0284C7] shrink-0 mt-0.5" size={18} strokeWidth={1.5} />
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-[#0F172A] truncate">{d.title}</p>
                          <p className="text-[11px] text-slate-400 truncate">{d.preview}</p>
                          <p className="text-[10px] text-slate-400 mt-0.5">{fmtDate(d.created_at)}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => downloadLibraryDoc(d)}
                        disabled={libExporting === key}
                        data-testid={`library-download-${key}`}
                        className="shrink-0 inline-flex items-center gap-1.5 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-50 text-white font-semibold px-3.5 py-2 rounded-full text-[11px] transition-colors"
                      >
                        <Download size={12} />
                        {libExporting === key ? "Descargando…" : "PDF"}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialogo generar imagen */}
      <Dialog open={imgDialog} onOpenChange={setImgDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">Generar imagen con IA</DialogTitle>
            <DialogDescription>
              Describe la imagen (diagrama, esquema, ilustración) y Gemini la creará dentro del caso.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={generateImage} className="space-y-4 mt-2">
            <textarea
              required
              rows={4}
              value={imgPrompt}
              onChange={(e) => setImgPrompt(e.target.value)}
              placeholder="Ej.: Diagrama del flujo de fondos entre la cuenta del condominio y el proveedor…"
              data-testid="image-prompt-input"
              className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors resize-none"
            />
            <button
              type="submit"
              disabled={generatingImg}
              data-testid="image-generate-submit-btn"
              className="w-full inline-flex items-center justify-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold py-3 rounded-full text-sm transition-colors"
            >
              {generatingImg ? (
                <>
                  <Loader2 className="animate-spin" size={15} /> Generando imagen…
                </>
              ) : (
                <>
                  <ImagePlus size={15} /> Generar imagen
                </>
              )}
            </button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};
