import { useCallback, useEffect, useState } from "react";
import { Inbox, Send, PenSquare, RefreshCw, Reply, Trash2, Paperclip, ArrowLeft, MailOpen, Download } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";
import { MailComposer } from "@/components/MailComposer";

const fmtDate = (iso) =>
  new Date(iso).toLocaleString("es-PE", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
const fmtSize = (n) => (n ? (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`) : "");

const frameDoc = (html) =>
  `<!doctype html><html><head><meta charset="utf-8"><base target="_blank"><style>body{font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:#0F172A;margin:0;word-break:break-word}img{max-width:100%;height:auto}</style></head><body>${html}</body></html>`;

const MailReader = ({ mail, onBack, onReply, onDelete, onUnread }) => {
  const inbound = mail.direction === "inbound";
  const download = async (att) => {
    try {
      const res = await api.get(`/admin/mail/${mail.id}/attachments/${att.id}`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = att.filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("No se pudo descargar el adjunto");
    }
  };
  return (
    <div className="bg-white border border-slate-200" data-testid="mail-reader">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between gap-3 flex-wrap">
        <button onClick={onBack} className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-[#0F172A] transition-colors" data-testid="mail-back-btn">
          <ArrowLeft size={16} /> Volver
        </button>
        <div className="flex items-center gap-2">
          {inbound && (
            <>
              <button onClick={onReply} data-testid="mail-reply-btn" className="inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-5 py-2 rounded-full text-sm transition-colors">
                <Reply size={15} /> Responder
              </button>
              <button onClick={onUnread} title="Marcar como no leído" data-testid="mail-unread-btn" className="p-2 text-slate-400 hover:text-[#0284C7] transition-colors"><MailOpen size={17} /></button>
            </>
          )}
          <button onClick={onDelete} title="Eliminar" data-testid="mail-delete-btn" className="p-2 text-slate-400 hover:text-red-600 transition-colors"><Trash2 size={17} /></button>
        </div>
      </div>
      <div className="p-6">
        <h3 className="font-heading font-bold text-lg text-[#0F172A]" data-testid="mail-reader-subject">{mail.subject}</h3>
        <dl className="mt-3 text-xs text-slate-500 space-y-1">
          <div><dt className="inline font-semibold">De: </dt><dd className="inline" data-testid="mail-reader-from">{mail.from_address}</dd></div>
          <div><dt className="inline font-semibold">Para: </dt><dd className="inline">{mail.to.join(", ")}</dd></div>
          {mail.cc.length > 0 && <div><dt className="inline font-semibold">CC: </dt><dd className="inline">{mail.cc.join(", ")}</dd></div>}
          <div>{fmtDate(mail.created_at)}</div>
        </dl>
        {mail.content_pending && (
          <p className="mt-5 bg-amber-50 border border-amber-200 text-amber-800 text-xs p-3" data-testid="mail-content-pending">
            No se pudo descargar el contenido de este correo desde Resend. Revisa que la API Key de Resend tenga acceso completo y vuelve a abrirlo.
          </p>
        )}
        <div className="mt-6 border-t border-slate-200 pt-6" data-testid="mail-reader-body">
          {mail.html && inbound ? (
            <iframe title="Contenido del correo" sandbox="allow-popups allow-popups-to-escape-sandbox" srcDoc={frameDoc(mail.html)} className="w-full min-h-[420px] border-0" />
          ) : (
            <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 leading-relaxed">{mail.text}</pre>
          )}
        </div>
        {mail.attachments.length > 0 && (
          <ul className="mt-6 pt-6 border-t border-slate-200 flex flex-wrap gap-2" data-testid="mail-attachments">
            {mail.attachments.map((a, i) => (
              <li key={a.id || i}>
                {inbound && a.id ? (
                  <button onClick={() => download(a)} data-testid={`mail-attachment-${i}`} className="inline-flex items-center gap-2 border border-slate-300 hover:border-[#0284C7] text-xs text-slate-700 px-3 py-2 transition-colors">
                    <Download size={14} className="text-[#0284C7]" /> {a.filename} <span className="text-slate-400">{fmtSize(a.size)}</span>
                  </button>
                ) : (
                  <span className="inline-flex items-center gap-2 bg-slate-100 text-xs text-slate-700 px-3 py-2" data-testid={`mail-attachment-${i}`}>
                    <Paperclip size={14} /> {a.filename} <span className="text-slate-400">{fmtSize(a.size)}</span>
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export const AdminMail = ({ onUnreadChange }) => {
  const [folder, setFolder] = useState("inbox");
  const [mails, setMails] = useState(null);
  const [meta, setMeta] = useState({ unread: 0, addresses: [], can_send: true, can_receive: true });
  const [open, setOpen] = useState(null);
  const [composing, setComposing] = useState(null);
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [list, m] = await Promise.all([api.get("/admin/mail", { params: { folder } }), api.get("/admin/mail/meta")]);
      setMails(list.data);
      setMeta(m.data);
      onUnreadChange?.(m.data.unread);
    } catch {
      toast.error("No se pudieron cargar los correos");
    }
  }, [folder, onUnreadChange]);

  useEffect(() => { load(); }, [load]);

  const openMail = async (id) => {
    try {
      const { data } = await api.get(`/admin/mail/${id}`);
      setOpen(data);
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    }
  };

  const sync = async () => {
    setSyncing(true);
    try {
      const { data } = await api.post("/admin/mail/sync");
      toast.success(data.message);
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setSyncing(false);
    }
  };

  const remove = async () => {
    if (!window.confirm("¿Eliminar este correo del panel? Esta acción es irreversible.")) return;
    try {
      await api.delete(`/admin/mail/${open.id}`);
      toast.success("Correo eliminado");
      setOpen(null);
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    }
  };

  const markUnread = async () => {
    await api.put(`/admin/mail/${open.id}/read`, { read: false });
    setOpen(null);
    load();
  };

  if (composing)
    return (
      <MailComposer
        addresses={meta.addresses}
        replyTo={composing.replyTo}
        onClose={() => setComposing(null)}
        onSent={() => { setComposing(null); setOpen(null); setFolder("sent"); load(); }}
      />
    );

  if (open)
    return <MailReader mail={open} onBack={() => setOpen(null)} onReply={() => setComposing({ replyTo: open })} onDelete={remove} onUnread={markUnread} />;

  const tab = (key, Icon, text) => (
    <button
      onClick={() => { setMails(null); setFolder(key); }}
      data-testid={`mail-folder-${key}`}
      className={`inline-flex items-center gap-2 px-4 py-2 text-sm rounded-full transition-colors ${folder === key ? "bg-[#0F172A] text-white" : "text-slate-600 hover:bg-slate-100"}`}
    >
      <Icon size={15} /> {text}
      {key === "inbox" && meta.unread > 0 && <span className="bg-[#0284C7] text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full" data-testid="mail-unread-count">{meta.unread}</span>}
    </button>
  );

  return (
    <div className="bg-white border border-slate-200" data-testid="admin-mail">
      <div className="p-4 flex items-center justify-between gap-3 flex-wrap border-b border-slate-200">
        <div className="flex items-center gap-2">
          {tab("inbox", Inbox, "Recibidos")}
          {tab("sent", Send, "Enviados")}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={sync} disabled={syncing} data-testid="mail-sync-btn" className="inline-flex items-center gap-2 border border-slate-300 hover:border-[#0284C7] text-slate-700 px-4 py-2 rounded-full text-sm transition-colors disabled:opacity-60">
            <RefreshCw size={15} className={syncing ? "animate-spin" : ""} /> Sincronizar
          </button>
          <button onClick={() => setComposing({})} data-testid="mail-compose-btn" className="inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-5 py-2 rounded-full text-sm transition-colors">
            <PenSquare size={15} /> Redactar
          </button>
        </div>
      </div>
      {(!meta.can_send || !meta.can_receive) && (
        <p className="bg-amber-50 border-b border-amber-200 text-amber-800 text-xs px-6 py-3" data-testid="mail-config-warning">
          {!meta.can_send ? "Falta la API Key de Resend: no se pueden enviar correos. " : ""}
          {!meta.can_receive ? "Falta la clave del webhook de Resend: los correos nuevos no llegarán solos (puedes usar Sincronizar). " : ""}
          Complétalo en Configuración → Correos.
        </p>
      )}
      {mails === null ? (
        <div className="flex justify-center py-16"><div className="w-7 h-7 border-2 border-[#0284C7] border-t-transparent rounded-full animate-spin" /></div>
      ) : mails.length === 0 ? (
        <p className="p-12 text-center text-sm text-slate-500" data-testid="mail-empty">{folder === "inbox" ? "No hay correos recibidos." : "Aún no has enviado correos."}</p>
      ) : (
        <ul className="divide-y divide-slate-200">
          {mails.map((m) => (
            <li key={m.id}>
              <button onClick={() => openMail(m.id)} data-testid={`mail-row-${m.id}`} className={`w-full text-left px-6 py-4 hover:bg-slate-50 transition-colors ${!m.read ? "bg-sky-50/60" : ""}`}>
                <div className="flex items-baseline justify-between gap-4">
                  <p className={`text-sm truncate ${!m.read ? "font-bold text-[#0F172A]" : "text-slate-700"}`}>
                    {folder === "inbox" ? m.from_address : `Para: ${m.to.join(", ")}`}
                  </p>
                  <span className="text-[11px] text-slate-400 shrink-0">{fmtDate(m.created_at)}</span>
                </div>
                <p className={`text-sm mt-1 truncate ${!m.read ? "font-semibold text-[#0F172A]" : "text-slate-600"}`}>
                  {m.attachments.length > 0 && <Paperclip size={12} className="inline mr-1.5 text-slate-400" />}
                  {m.subject}
                </p>
                <p className="text-xs text-slate-400 mt-1 truncate">{m.preview}</p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
