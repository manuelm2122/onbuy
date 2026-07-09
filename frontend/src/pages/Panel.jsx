import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Building2,
  FileText,
  CheckCircle2,
  Clock,
  Plus,
  LogOut,
  Trash2,
  ChevronRight,
} from "lucide-react";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiErrorDetail } from "@/lib/api";

export const STATUS_META = {
  pendiente: { label: "Pendiente", cls: "bg-amber-50 text-amber-700 border-amber-200" },
  analizando: { label: "Analizando", cls: "bg-sky-50 text-sky-700 border-sky-200" },
  completada: { label: "Completada", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  error: { label: "Error", cls: "bg-red-50 text-red-700 border-red-200" },
};

export const StatusBadge = ({ status }) => {
  const meta = STATUS_META[status] || STATUS_META.pendiente;
  return (
    <span className={`inline-flex items-center text-xs font-semibold px-3 py-1 rounded-full border ${meta.cls}`} data-testid={`status-badge-${status}`}>
      {meta.label}
    </span>
  );
};

const emptyForm = { condominium_name: "", address: "", district: "", period: "", purpose: "", notes: "" };

export default function Panel() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [audits, setAudits] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [s, a] = await Promise.all([api.get("/dashboard/stats"), api.get("/audits")]);
      setStats(s.data);
      setAudits(a.data);
    } catch (err) {
      toast.error("No se pudieron cargar los datos");
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const createAudit = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const { data } = await api.post("/audits", form);
      toast.success("Auditoría creada. Ahora sube los documentos.");
      setDialogOpen(false);
      setForm(emptyForm);
      navigate(`/panel/auditoria/${data.id}`);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setCreating(false);
    }
  };

  const deleteAudit = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm("¿Eliminar esta auditoría y todos sus documentos?")) return;
    try {
      await api.delete(`/audits/${id}`);
      toast.success("Auditoría eliminada");
      loadData();
    } catch {
      toast.error("No se pudo eliminar");
    }
  };

  const statCards = stats
    ? [
        { icon: Building2, label: "Auditorías totales", value: stats.total_audits },
        { icon: CheckCircle2, label: "Completadas", value: stats.completed },
        { icon: Clock, label: "En proceso", value: stats.pending },
        { icon: FileText, label: "Documentos subidos", value: stats.documents },
      ]
    : [];

  return (
    <div className="min-h-screen bg-[#F8FAFC]">
      {/* Header */}
      <header className="bg-[#020617] text-white">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
          <Link to="/" className="font-heading font-black text-lg tracking-tight" data-testid="panel-logo">
            OnBuy<span className="text-[#0EA5E9]">Solutions</span>
          </Link>
          <div className="flex items-center gap-5">
            <span className="text-sm text-slate-300 hidden sm:block" data-testid="panel-user-name">
              {user?.name}
            </span>
            <button
              onClick={async () => {
                await logout();
                navigate("/");
              }}
              data-testid="panel-logout-btn"
              className="inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white transition-colors"
            >
              <LogOut size={16} /> Salir
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 lg:px-10 py-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-10">
          <div>
            <h1 className="font-heading font-black text-3xl tracking-tight text-[#0F172A]" data-testid="panel-title">
              Panel de auditorías
            </h1>
            <p className="text-slate-500 text-sm mt-1">Gestiona tus condominios y sus auditorías con IA.</p>
          </div>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <button
                data-testid="new-audit-btn"
                className="inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-6 py-3 rounded-full text-sm transition-colors"
              >
                <Plus size={18} /> Nueva auditoría
              </button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                <DialogTitle className="font-heading text-xl">Nueva auditoría</DialogTitle>
                <DialogDescription>Registra los datos del condominio a auditar.</DialogDescription>
              </DialogHeader>
              <form onSubmit={createAudit} className="space-y-4 mt-2">
                <input
                  required
                  data-testid="audit-name-input"
                  value={form.condominium_name}
                  onChange={(e) => setForm({ ...form, condominium_name: e.target.value })}
                  placeholder="Nombre del condominio *"
                  className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors"
                />
                <div className="grid grid-cols-2 gap-4">
                  <input
                    data-testid="audit-address-input"
                    value={form.address}
                    onChange={(e) => setForm({ ...form, address: e.target.value })}
                    placeholder="Dirección"
                    className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors"
                  />
                  <input
                    data-testid="audit-district-input"
                    value={form.district}
                    onChange={(e) => setForm({ ...form, district: e.target.value })}
                    placeholder="Distrito / Ciudad"
                    className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors"
                  />
                </div>
                <input
                  required
                  data-testid="audit-period-input"
                  value={form.period}
                  onChange={(e) => setForm({ ...form, period: e.target.value })}
                  placeholder="Período a auditar (ej. Enero - Diciembre 2025) *"
                  className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors"
                />
                <input
                  data-testid="audit-purpose-input"
                  value={form.purpose}
                  onChange={(e) => setForm({ ...form, purpose: e.target.value })}
                  placeholder="Finalidad del informe (ej. presentar a la junta)"
                  className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors"
                />
                <textarea
                  rows={3}
                  data-testid="audit-notes-input"
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="Notas o sospechas específicas (opcional)"
                  className="w-full border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3 text-sm transition-colors resize-none"
                />
                <button
                  type="submit"
                  disabled={creating}
                  data-testid="audit-create-submit-btn"
                  className="w-full bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold py-3.5 rounded-full text-sm transition-colors"
                >
                  {creating ? "Creando…" : "Crear auditoría"}
                </button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <Tabs defaultValue="resumen">
          <TabsList className="bg-white border border-slate-200 p-1 h-auto">
            <TabsTrigger value="resumen" data-testid="tab-resumen" className="px-6 py-2.5 text-sm data-[state=active]:bg-[#0F172A] data-[state=active]:text-white">
              Resumen
            </TabsTrigger>
            <TabsTrigger value="auditorias" data-testid="tab-auditorias" className="px-6 py-2.5 text-sm data-[state=active]:bg-[#0F172A] data-[state=active]:text-white">
              Auditorías
            </TabsTrigger>
          </TabsList>

          <TabsContent value="resumen" className="mt-8">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {statCards.map((c) => (
                <div key={c.label} className="bg-white border border-slate-200 p-6" data-testid={`stat-card-${c.label.toLowerCase().replace(/ /g, "-")}`}>
                  <c.icon className="text-[#0284C7]" size={24} strokeWidth={1.5} />
                  <p className="font-heading font-black text-3xl text-[#0F172A] mt-4">{c.value}</p>
                  <p className="text-xs text-slate-500 mt-1">{c.label}</p>
                </div>
              ))}
            </div>
            <div className="mt-10">
              <h2 className="font-heading font-bold text-lg text-[#0F172A] mb-4">Auditorías recientes</h2>
              {audits.length === 0 ? (
                <div className="bg-white border border-dashed border-slate-300 p-12 text-center" data-testid="empty-audits-message">
                  <Building2 className="mx-auto text-slate-300" size={40} strokeWidth={1.2} />
                  <p className="text-slate-500 text-sm mt-4">
                    Aún no tienes auditorías. Crea la primera con el botón "Nueva auditoría".
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {audits.slice(0, 4).map((a) => (
                    <div
                      key={a.id}
                      onClick={() => navigate(`/panel/auditoria/${a.id}`)}
                      className="bg-white border border-slate-200 hover:border-[#0284C7] p-5 flex items-center justify-between cursor-pointer transition-colors group"
                      data-testid={`recent-audit-${a.id}`}
                    >
                      <div>
                        <p className="font-semibold text-[#0F172A] text-sm">{a.condominium_name}</p>
                        <p className="text-xs text-slate-500 mt-1">
                          {a.period} · {a.document_count} documento(s)
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                        <StatusBadge status={a.status} />
                        <ChevronRight size={18} className="text-slate-300 group-hover:text-[#0284C7] transition-colors" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="auditorias" className="mt-8">
            {audits.length === 0 ? (
              <div className="bg-white border border-dashed border-slate-300 p-12 text-center">
                <Building2 className="mx-auto text-slate-300" size={40} strokeWidth={1.2} />
                <p className="text-slate-500 text-sm mt-4">No hay auditorías registradas todavía.</p>
              </div>
            ) : (
              <div className="bg-white border border-slate-200 overflow-x-auto">
                <table className="w-full text-sm" data-testid="audits-table">
                  <thead>
                    <tr className="bg-[#0F172A] text-white text-left">
                      <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase">Condominio</th>
                      <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase hidden md:table-cell">Período</th>
                      <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase hidden sm:table-cell">Docs</th>
                      <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase">Estado</th>
                      <th className="px-5 py-3.5"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {audits.map((a) => (
                      <tr
                        key={a.id}
                        onClick={() => navigate(`/panel/auditoria/${a.id}`)}
                        className="border-t border-slate-100 hover:bg-sky-50/50 cursor-pointer transition-colors"
                        data-testid={`audit-row-${a.id}`}
                      >
                        <td className="px-5 py-4">
                          <p className="font-semibold text-[#0F172A]">{a.condominium_name}</p>
                          <p className="text-xs text-slate-400">{a.district || a.address || ""}</p>
                        </td>
                        <td className="px-5 py-4 text-slate-600 hidden md:table-cell">{a.period}</td>
                        <td className="px-5 py-4 text-slate-600 hidden sm:table-cell">{a.document_count}</td>
                        <td className="px-5 py-4">
                          <StatusBadge status={a.status} />
                        </td>
                        <td className="px-5 py-4 text-right">
                          <button
                            onClick={(e) => deleteAudit(a.id, e)}
                            data-testid={`delete-audit-btn-${a.id}`}
                            className="text-slate-400 hover:text-red-600 transition-colors p-1"
                            title="Eliminar"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
