import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, ArrowLeft, Save, Trash2, MessagesSquare, MessageCircle, Mail, FilePlus2, Search } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";

const EMPTY = { full_name: "", dni: "", phone: "", email: "", position: "", company_name: "", company_ruc: "", company_address: "", status: "prospecto", notes: "" };
const STATUS = {
  prospecto: { label: "Prospecto", cls: "bg-sky-50 text-sky-700" },
  en_proceso: { label: "En proceso", cls: "bg-amber-50 text-amber-700" },
  entregado: { label: "Entregado", cls: "bg-emerald-50 text-emerald-700" },
  cerrado: { label: "Cerrado", cls: "bg-slate-100 text-slate-600" },
};
const FIELDS = [
  ["full_name", "Nombres y apellidos", true],
  ["dni", "DNI"],
  ["phone", "Teléfono"],
  ["email", "Correo"],
  ["position", "Cargo (ej. presidente de junta)"],
  ["company_name", "Empresa o condominio a auditar"],
  ["company_ruc", "RUC"],
  ["company_address", "Dirección"],
];
const label = "text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold";
const input = "mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors bg-white";

export const AdminAuditClients = ({ onOpenCase }) => {
  const [clients, setClients] = useState(null);
  const [form, setForm] = useState(null);
  const [audits, setAudits] = useState([]);
  const [period, setPeriod] = useState("");
  const [query, setQuery] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    api.get("/admin/audit-clients").then(({ data }) => setClients(data)).catch(() => toast.error("No se pudieron cargar los clientes"));
  }, []);
  useEffect(() => { load(); }, [load]);

  const open = async (c) => {
    setForm({ ...EMPTY, ...c });
    setAudits([]);
    const { data } = await api.get(`/admin/audit-clients/${c.id}`);
    setAudits(data.audits);
  };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (form.id) {
        await api.put(`/admin/audit-clients/${form.id}`, form);
        toast.success("Ficha guardada");
      } else {
        const { data } = await api.post("/admin/audit-clients", form);
        toast.success(data.already_existed ? "Ya existía una ficha con ese correo" : "Cliente creado con su expediente");
        setForm({ ...EMPTY, ...data });
      }
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`¿Eliminar la ficha de ${form.full_name}? El expediente y las auditorías se conservan.`)) return;
    await api.delete(`/admin/audit-clients/${form.id}`);
    toast.success("Ficha eliminada");
    setForm(null);
    load();
  };

  const createAudit = async () => {
    if (period.trim().length < 2) return toast.error("Indica el periodo a auditar (ej. 2025)");
    if (!form.company_name) return toast.error("Completa y guarda primero el nombre de la empresa o condominio");
    try {
      await api.post("/audits", { condominium_name: form.company_name, address: form.company_address || null, period: period.trim(), client_id: form.id });
      toast.success("Auditoría creada");
      setPeriod("");
      open(form);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    }
  };

  if (form)
    return (
      <div className="space-y-6" data-testid="audit-client-detail">
        <form onSubmit={save} className="bg-white border border-slate-200 p-6 space-y-5">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <button type="button" onClick={() => setForm(null)} className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-[#0F172A] transition-colors" data-testid="audit-client-back-btn">
              <ArrowLeft size={16} /> Clientes
            </button>
            {form.id && (
              <div className="flex items-center gap-2 flex-wrap">
                {form.case_id && (
                  <button type="button" onClick={() => onOpenCase(form.case_id)} data-testid="audit-client-open-case-btn" className="inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-5 py-2 rounded-full text-sm transition-colors">
                    <MessagesSquare size={15} /> Abrir expediente con IA
                  </button>
                )}
                {form.phone && (
                  <a href={`https://wa.me/${form.phone.replace(/\D/g, "")}`} target="_blank" rel="noopener noreferrer" data-testid="audit-client-whatsapp-link" className="p-2 text-slate-400 hover:text-[#25D366] transition-colors" title="WhatsApp"><MessageCircle size={18} /></a>
                )}
                {form.email && (
                  <a href={`mailto:${form.email}`} data-testid="audit-client-email-link" className="p-2 text-slate-400 hover:text-[#0284C7] transition-colors" title="Correo"><Mail size={18} /></a>
                )}
                <button type="button" onClick={remove} data-testid="audit-client-delete-btn" className="p-2 text-slate-400 hover:text-red-600 transition-colors" title="Eliminar ficha"><Trash2 size={18} /></button>
              </div>
            )}
          </div>
          <h3 className="font-heading font-bold text-[#0F172A]">{form.id ? "Ficha del cliente" : "Nuevo cliente de auditoría"}</h3>
          <div className="grid sm:grid-cols-2 gap-4">
            {FIELDS.map(([k, text, required]) => (
              <div key={k}>
                <label className={label}>{text}</label>
                <input required={!!required} value={form[k]} onChange={set(k)} data-testid={`audit-client-${k}-input`} className={input} />
              </div>
            ))}
            <div>
              <label className={label}>Estado</label>
              <select value={form.status} onChange={set("status")} data-testid="audit-client-status-select" className={input}>
                {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className={label}>Notas</label>
            <textarea rows={4} value={form.notes} onChange={set("notes")} data-testid="audit-client-notes-input" className={`${input} resize-y`} />
          </div>
          <button type="submit" disabled={saving} data-testid="audit-client-save-btn" className="inline-flex items-center gap-2 bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold px-8 py-3 rounded-full text-sm transition-colors">
            <Save size={16} /> {saving ? "Guardando…" : "Guardar ficha"}
          </button>
        </form>

        {form.id && (
          <div className="bg-white border border-slate-200 p-6" data-testid="audit-client-audits">
            <h3 className="font-heading font-bold text-[#0F172A]">Auditorías de este cliente</h3>
            <div className="mt-4 flex gap-3 flex-wrap">
              <input value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="Periodo (ej. Enero–Diciembre 2025)" data-testid="audit-client-period-input" className="flex-1 min-w-[200px] border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm" />
              <button type="button" onClick={createAudit} data-testid="audit-client-new-audit-btn" className="inline-flex items-center gap-2 border border-[#0284C7] text-[#0284C7] hover:bg-sky-50 font-semibold px-5 py-2.5 rounded-full text-sm transition-colors">
                <FilePlus2 size={15} /> Nueva auditoría
              </button>
            </div>
            <ul className="mt-4 divide-y divide-slate-200">
              {audits.map((a) => (
                <li key={a.id} className="py-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[#0F172A]">{a.condominium_name}</p>
                    <p className="text-xs text-slate-500">{a.period} · {a.status}</p>
                  </div>
                  <Link to={`/panel/auditoria/${a.id}`} data-testid={`audit-client-audit-link-${a.id}`} className="text-sm font-semibold text-[#0284C7] hover:text-[#0EA5E9] transition-colors">Abrir</Link>
                </li>
              ))}
              {audits.length === 0 && <li className="py-6 text-sm text-slate-500">Aún no hay auditorías para este cliente.</li>}
            </ul>
          </div>
        )}
      </div>
    );

  const q = query.trim().toLowerCase();
  const shown = (clients || []).filter((c) => !q || [c.full_name, c.company_name, c.email, c.dni, c.company_ruc].some((v) => (v || "").toLowerCase().includes(q)));

  return (
    <div className="bg-white border border-slate-200" data-testid="admin-audit-clients">
      <div className="p-6 flex items-center justify-between gap-3 flex-wrap border-b border-slate-200">
        <div>
          <h3 className="font-heading font-bold text-[#0F172A]">Clientes de auditoría</h3>
          <p className="text-xs text-slate-500 mt-1">{clients?.length ?? 0} cliente(s) · cada uno con su expediente de asesoramiento</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar…" data-testid="audit-clients-search-input" className="border border-slate-300 focus:border-[#0284C7] outline-none pl-9 pr-3 py-2 text-sm rounded-full" />
          </div>
          <button onClick={() => { setForm(EMPTY); setAudits([]); }} data-testid="audit-client-new-btn" className="inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-5 py-2.5 rounded-full text-sm transition-colors">
            <Plus size={16} /> Nuevo cliente
          </button>
        </div>
      </div>
      <ul className="divide-y divide-slate-200">
        {shown.map((c) => (
          <li key={c.id}>
            <button onClick={() => open(c)} data-testid={`audit-client-row-${c.id}`} className="w-full text-left px-6 py-4 hover:bg-slate-50 transition-colors flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-[#0F172A] truncate">{c.full_name}</p>
                <p className="text-xs text-slate-500 truncate">{[c.company_name, c.email, c.phone].filter(Boolean).join(" · ") || "Sin datos de contacto"}</p>
              </div>
              <span className={`shrink-0 text-[10px] font-bold tracking-[0.1em] uppercase px-2 py-0.5 rounded-full ${STATUS[c.status]?.cls}`}>{STATUS[c.status]?.label}</span>
            </button>
          </li>
        ))}
        {clients && shown.length === 0 && <li className="p-10 text-center text-sm text-slate-500" data-testid="audit-clients-empty">No hay clientes.</li>}
      </ul>
    </div>
  );
};
