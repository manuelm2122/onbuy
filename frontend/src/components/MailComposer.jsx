import { useRef, useState } from "react";
import { Send, Sparkles, Paperclip, X } from "lucide-react";
import { toast } from "sonner";
import { api, BACKEND_URL, formatApiErrorDetail } from "@/lib/api";

const label = "text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold";
const input = "mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors bg-white";

const bareAddress = (a = "") => (a.match(/<([^>]+)>/)?.[1] || a).trim();

const quote = (m) =>
  `\n\n\nEl ${new Date(m.created_at).toLocaleString("es-PE")}, ${m.from_address} escribió:\n` +
  (m.text || "").split("\n").map((l) => `> ${l}`).join("\n");

export const MailComposer = ({ addresses, replyTo, onClose, onSent }) => {
  const myAddress = replyTo?.to?.map(bareAddress).find((a) => addresses.includes(a));
  const [form, setForm] = useState({
    from_address: myAddress || addresses[0] || "",
    to: replyTo ? bareAddress(replyTo.from_address) : "",
    cc: "",
    subject: replyTo ? (/^re:/i.test(replyTo.subject) ? replyTo.subject : `Re: ${replyTo.subject}`) : "",
    text: replyTo ? quote(replyTo) : "",
  });
  const [files, setFiles] = useState([]);
  const [instructions, setInstructions] = useState("");
  const [drafting, setDrafting] = useState(false);
  const [sending, setSending] = useState(false);
  const fileRef = useRef(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const draft = async () => {
    if (instructions.trim().length < 3) return toast.error("Escribe qué debe decir el correo");
    setDrafting(true);
    const tail = replyTo ? quote(replyTo) : "";
    let raw = "";
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/mail/ai-draft`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instructions: instructions.trim(), reply_to_id: replyTo?.id || null }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Error al redactar");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        raw += decoder.decode(value, { stream: true });
        const body = raw.split("[ERROR_IA]")[0].trim();
        setForm((f) => ({ ...f, text: body + tail }));
      }
      if (raw.includes("[ERROR_IA]")) toast.error(`La IA devolvió un error: ${raw.split("[ERROR_IA]")[1].trim()}`);
      else toast.success("Borrador listo. Revísalo antes de enviar.");
    } catch (err) {
      toast.error(formatApiErrorDetail(err.message));
    } finally {
      setDrafting(false);
    }
  };

  const send = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => fd.append(k, v));
      if (replyTo) fd.append("reply_to_id", replyTo.id);
      files.forEach((f) => fd.append("files", f));
      await api.post("/admin/mail/send", fd);
      toast.success("Correo enviado");
      onSent();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setSending(false);
    }
  };

  return (
    <form onSubmit={send} className="bg-white border border-slate-200 p-6 space-y-5" data-testid="mail-composer">
      <div className="flex items-center justify-between">
        <h3 className="font-heading font-bold text-[#0F172A]">{replyTo ? "Responder" : "Nuevo correo"}</h3>
        <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-700 transition-colors" data-testid="mail-composer-close-btn">
          <X size={20} />
        </button>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label className={label}>De</label>
          <select value={form.from_address} onChange={set("from_address")} data-testid="mail-from-select" className={input}>
            {addresses.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        <div>
          <label className={label}>Para</label>
          <input required value={form.to} onChange={set("to")} placeholder="cliente@correo.com, otro@correo.com" data-testid="mail-to-input" className={input} />
        </div>
        <div>
          <label className={label}>CC (opcional)</label>
          <input value={form.cc} onChange={set("cc")} data-testid="mail-cc-input" className={input} />
        </div>
        <div>
          <label className={label}>Asunto</label>
          <input required value={form.subject} onChange={set("subject")} data-testid="mail-subject-input" className={input} />
        </div>
      </div>

      <div className="bg-sky-50 border border-sky-200 p-4">
        <div className="flex items-center gap-2 text-[#0284C7]">
          <Sparkles size={16} />
          <p className="font-heading font-bold text-sm">Redactar con IA</p>
        </div>
        <div className="mt-3 grid sm:grid-cols-3 gap-3">
          <input
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder={replyTo ? "Ej.: agradece y propone una llamada el jueves" : "Ej.: presenta el servicio de menús QR a un restaurante"}
            data-testid="mail-ai-instructions-input"
            className="sm:col-span-2 border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm bg-white"
          />
          <button type="button" onClick={draft} disabled={drafting} data-testid="mail-ai-draft-btn" className="inline-flex items-center justify-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold px-5 py-2.5 rounded-full text-sm transition-colors">
            <Sparkles size={15} /> {drafting ? "Redactando…" : "Redactar"}
          </button>
        </div>
      </div>

      <div>
        <label className={label}>Mensaje</label>
        <textarea required rows={14} value={form.text} onChange={set("text")} data-testid="mail-text-input" className={`${input} resize-y`} />
      </div>

      <div>
        <input ref={fileRef} type="file" multiple hidden data-testid="mail-files-input" onChange={(e) => { setFiles([...files, ...e.target.files]); e.target.value = ""; }} />
        <button type="button" onClick={() => fileRef.current.click()} data-testid="mail-attach-btn" className="inline-flex items-center gap-2 text-sm text-[#0284C7] hover:text-[#0EA5E9] font-semibold transition-colors">
          <Paperclip size={15} /> Adjuntar archivos (máx. 20 MB)
        </button>
        {files.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2">
            {files.map((f, i) => (
              <li key={`${f.name}-${i}`} className="inline-flex items-center gap-2 bg-slate-100 text-xs text-slate-700 px-3 py-1.5 rounded-full" data-testid={`mail-file-chip-${i}`}>
                {f.name}
                <button type="button" onClick={() => setFiles(files.filter((_, j) => j !== i))} className="text-slate-400 hover:text-red-600 transition-colors"><X size={13} /></button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <button type="submit" disabled={sending || drafting} data-testid="mail-send-btn" className="inline-flex items-center gap-2 bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold px-8 py-3 rounded-full text-sm transition-colors">
        <Send size={16} /> {sending ? "Enviando…" : "Enviar correo"}
      </button>
    </form>
  );
};
