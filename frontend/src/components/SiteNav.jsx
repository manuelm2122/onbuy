import { Link } from "react-router-dom";

const LINKS = [
  { to: "/#servicios", label: "Servicios", id: "servicios" },
  { to: "/auditorias-condominios", label: "Auditorías", id: "auditorias" },
  { to: "/asesoria-legal", label: "Asesoría legal", id: "legal" },
  { to: "/blog", label: "Blog", id: "blog" },
  { to: "/#contacto", label: "Contacto", id: "contacto" },
];

export const SiteNav = () => (
  <nav className="glass-nav fixed top-0 inset-x-0 z-50" data-testid="site-nav">
    <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
      <Link to="/" onClick={() => window.scrollTo(0, 0)} className="font-heading font-black text-xl tracking-tight text-white" data-testid="nav-logo">
        OnBuy<span className="text-[#0EA5E9]">Solutions</span>
      </Link>
      <div className="hidden md:flex items-center gap-8 text-sm text-slate-300">
        {LINKS.map((l) => (
          <Link key={l.id} to={l.to} className="hover:text-white transition-colors" data-testid={`site-nav-${l.id}`}>
            {l.label}
          </Link>
        ))}
      </div>
      <Link
        to="/acceso"
        data-testid="nav-login-btn"
        className="bg-[#0284C7] hover:bg-[#0EA5E9] text-white text-sm font-semibold px-5 py-2.5 rounded-full transition-colors"
      >
        Acceder al panel
      </Link>
    </div>
  </nav>
);
