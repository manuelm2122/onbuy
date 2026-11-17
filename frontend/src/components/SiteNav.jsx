import { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { InstallAppButton } from "@/components/InstallAppButton";

const LINKS = [
  { to: "/#servicios", label: "Servicios", id: "servicios" },
  { to: "/auditorias-condominios", label: "Auditorías", id: "auditorias" },
  { to: "/asesoria-legal", label: "Asesoría legal", id: "legal" },
  { to: "/blog", label: "Blog", id: "blog" },
  { to: "/#contacto", label: "Contacto", id: "contacto" },
];

export const SiteNav = () => {
  const [open, setOpen] = useState(false);
  return (
    <nav className="glass-nav fixed top-0 inset-x-0 z-50" data-testid="site-nav">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 h-16 flex items-center justify-between gap-3">
        <Link to="/" onClick={() => window.scrollTo(0, 0)} className="font-heading font-black text-lg sm:text-xl tracking-tight text-white" data-testid="nav-logo">
          OnBuy<span className="text-[#0EA5E9]">Solutions</span>
        </Link>
        <div className="hidden md:flex items-center gap-5 lg:gap-8 text-sm text-slate-300">
          {LINKS.map((l) => (
            <Link key={l.id} to={l.to} className="hover:text-white transition-colors whitespace-nowrap" data-testid={`site-nav-${l.id}`}>
              {l.label}
            </Link>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/acceso"
            data-testid="nav-login-btn"
            className="bg-[#0284C7] hover:bg-[#0EA5E9] text-white text-sm font-semibold px-4 sm:px-5 py-2.5 rounded-full transition-colors whitespace-nowrap"
          >
            <span className="sm:hidden">Acceder</span>
            <span className="hidden sm:inline">Acceder al panel</span>
          </Link>
          <button onClick={() => setOpen(!open)} aria-label={open ? "Cerrar menú" : "Abrir menú"} aria-expanded={open} data-testid="nav-menu-btn" className="md:hidden p-2 text-slate-200 hover:text-white transition-colors">
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>
      {open && (
        <div className="md:hidden bg-[#020617] border-t border-slate-800 px-6 py-4 flex flex-col" data-testid="nav-mobile-menu">
          {LINKS.map((l) => (
            <Link key={l.id} to={l.to} onClick={() => setOpen(false)} className="py-3 text-sm text-slate-200 hover:text-white border-b border-slate-900 transition-colors" data-testid={`mobile-nav-${l.id}`}>
              {l.label}
            </Link>
          ))}
          <InstallAppButton className="mt-4 self-start text-sm text-[#0EA5E9] hover:text-white" />
        </div>
      )}
    </nav>
  );
};
