import { useEffect, useState, useCallback } from "react";
import { Inbox, Mail, MailOpen, Phone, Trash2, Loader2, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";

const fmtDate = (iso) =>
  new Date(iso).toLocaleString("es-PE", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

export const AdminContacts = () => {
  const [contacts, setContacts] = useState(null);
  const [acting, setActing] = useState(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/contacts");
      setContacts(data);
    } catch {
      toast.error("No se pudieron cargar los mensajes");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggleRead = async (c) => {
    setActing(c.id);
    try {
      const { data } = await api.put(`/admin/contacts/${c.id}/read`, { read: !c.read });
      toast.success(data.message);
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setActing(null);
    }
  };

  const toClient = async (c) => {
    try {
      const { data } = await api.post("/admin/audit-clients", {
        full_name: c.name, email: c.email, phone: c.phone || "", source: "formulario",
        notes: `Mensaje del formulario${c.service ? ` (${c.service})` : ""}: ${c.message}`,
      });
      toast.success(data.already_existed ? "Ya existía una ficha con ese correo" : "Ficha creada en Clientes auditoría");
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    }
  };

  const remove = async (c) => {
    if (!window.confirm(`¿Eliminar el mensaje de ${c.name}? Esta acción es irreversible.`)) return;
    setActing(c.id);
    try {
      const { data } = await api.delete(`/admin/contacts/${c.id}`);
      toast.success(data.message);
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setActing(null);
    }
  };

  const unread = contacts?.filter((c) => !c.read).length || 0;

  return (
    <div className="bg-white border border-slate-200" data-testid="admin-contacts">
      <div className="p-6 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="font-heading font-bold text-[#0F172A] flex items-center gap-2">
            <Inbox size={18} className="text-[#0284C7]" /> Mensajes de contacto
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Consultas recibidas desde el formulario de la página web.
          </p>
        </div>
        {contacts && (
          <span
            className={`text-xs font-bold px-3 py-1.5 rounded-full ${unread > 0 ? "bg-sky-50 text-[#0284C7] border border-sky-200" : "bg-slate-100 text-slate-500"}`}
            data-testid="contacts-unread-badge"
          >
            {unread > 0 ? `${unread} sin leer` : "Todo leído"}
          </span>
        )}
      </div>

      {!contacts ? (
        <div className="p-10 flex justify-center">
          <Loader2 className="animate-spin text-[#0284C7]" size={22} />
        </div>
      ) : contacts.length === 0 ? (
        <div className="p-12 text-center" data-testid="contacts-empty">
          <Inbox className="mx-auto text-slate-300" size={36} strokeWidth={1.2} />
          <p className="text-sm text-slate-500 mt-3">Aún no hay mensajes de contacto.</p>
        </div>
      ) : (
        <ul className="divide-y divide-slate-100" data-testid="contacts-list">
          {contacts.map((c) => (
            <li
              key={c.id}
              className={`px-6 py-5 ${!c.read ? "bg-sky-50/50" : ""}`}
              data-testid={`contact-item-${c.id}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    {!c.read && <span className="w-2 h-2 rounded-full bg-[#0284C7] shrink-0" data-testid={`contact-unread-dot-${c.id}`} />}
                    <p className={`text-sm truncate ${!c.read ? "font-bold text-[#0F172A]" : "font-semibold text-slate-700"}`}>{c.name}</p>
                    <a href={`mailto:${c.email}`} className="text-xs text-[#0284C7] hover:underline truncate" data-testid={`contact-email-${c.id}`}>
                      {c.email}
                    </a>
                    {c.phone && (
                      <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                        <Phone size={11} /> {c.phone}
                      </span>
                    )}
                  </div>
                  {c.service && <p className="text-[11px] font-semibold text-[#0284C7] mt-2" data-testid={`contact-service-${c.id}`}>Servicio: {c.service}</p>}
                  <p className="text-sm text-slate-600 mt-2 leading-relaxed whitespace-pre-wrap">{c.message}</p>
                  <p className="text-[11px] text-slate-400 mt-2">{fmtDate(c.created_at)}</p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <button
                    onClick={() => toggleRead(c)}
                    disabled={acting === c.id}
                    data-testid={`contact-toggle-read-${c.id}`}
                    title={c.read ? "Marcar como no leído" : "Marcar como leído"}
                    className="text-slate-400 hover:text-[#0284C7] disabled:opacity-40 transition-colors p-2"
                  >
                    {c.read ? <Mail size={16} /> : <MailOpen size={16} />}
                  </button>
                  <button
                    onClick={() => toClient(c)}
                    disabled={acting === c.id}
                    title="Crear ficha de cliente de auditoría"
                    data-testid={`contact-to-client-${c.id}`}
                    className="p-2 text-slate-400 hover:text-[#0284C7] transition-colors"
                  >
                    <UserPlus size={16} />
                  </button>
                  <button
                    onClick={() => remove(c)}
                    disabled={acting === c.id}
                    data-testid={`contact-delete-${c.id}`}
                    title="Eliminar mensaje"
                    className="text-slate-400 hover:text-red-600 disabled:opacity-40 transition-colors p-2"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
