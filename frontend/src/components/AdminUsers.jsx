import { useEffect, useState, useCallback } from "react";
import { Users, Trash2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";

export const AdminUsers = () => {
  const [users, setUsers] = useState(null);
  const [acting, setActing] = useState(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/users");
      setUsers(data);
    } catch {
      toast.error("No se pudieron cargar los clientes");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const removeUser = async (id, name) => {
    if (!window.confirm(`¿Eliminar al cliente "${name}" junto con TODAS sus auditorías y documentos? Esta acción es irreversible.`)) return;
    setActing(id);
    try {
      const { data } = await api.delete(`/admin/users/${id}`);
      toast.success(data.message);
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setActing(null);
    }
  };

  const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString("es-PE") : "—");

  return (
    <div>
      <div className="bg-sky-50 border border-sky-200 p-5 flex items-start gap-4 mb-6" data-testid="users-info-banner">
        <Users className="text-[#0284C7] shrink-0 mt-0.5" size={22} strokeWidth={1.5} />
        <div>
          <h3 className="font-heading font-bold text-[#0F172A] text-sm">Administración de clientes</h3>
          <p className="text-xs text-slate-600 leading-relaxed mt-1.5">
            Todos los usuarios registrados en la plataforma. Al eliminar un cliente se borran también
            sus auditorías y documentos. Las cuentas de administrador no pueden eliminarse.
          </p>
        </div>
      </div>

      {!users ? (
        <div className="bg-white border border-slate-200 p-12 flex justify-center">
          <div className="w-6 h-6 border-2 border-[#0284C7] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="bg-white border border-slate-200 overflow-x-auto">
          <table className="w-full text-sm" data-testid="admin-users-table">
            <thead>
              <tr className="bg-[#0F172A] text-white text-left">
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase">Cliente</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase">Rol</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase hidden md:table-cell">Registro</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase hidden sm:table-cell">Auditorías</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase hidden sm:table-cell">Docs</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase text-right">Acción</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-slate-100" data-testid={`user-row-${u.id}`}>
                  <td className="px-5 py-4">
                    <p className="font-semibold text-[#0F172A]">{u.name}</p>
                    <p className="text-xs text-slate-400">{u.email}</p>
                  </td>
                  <td className="px-5 py-4">
                    {u.role === "admin" ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[#0F172A] text-white">
                        <ShieldCheck size={11} /> Admin
                      </span>
                    ) : (
                      <span className="inline-flex text-[11px] font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
                        Cliente
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-4 text-slate-600 hidden md:table-cell">{fmtDate(u.created_at)}</td>
                  <td className="px-5 py-4 text-slate-600 hidden sm:table-cell">{u.audit_count}</td>
                  <td className="px-5 py-4 text-slate-600 hidden sm:table-cell">{u.document_count}</td>
                  <td className="px-5 py-4 text-right">
                    <button
                      onClick={() => removeUser(u.id, u.name)}
                      disabled={u.role === "admin" || acting === u.id}
                      data-testid={`delete-user-btn-${u.id}`}
                      className="inline-flex items-center gap-1.5 border border-slate-300 hover:border-red-400 hover:text-red-600 disabled:opacity-40 disabled:cursor-not-allowed text-slate-500 font-semibold px-4 py-2 rounded-full text-xs transition-colors"
                    >
                      <Trash2 size={13} />
                      {acting === u.id ? "Eliminando…" : "Eliminar"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
