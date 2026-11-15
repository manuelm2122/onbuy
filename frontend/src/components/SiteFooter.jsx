import { Link } from "react-router-dom";
import { SERVICES } from "@/constants/services";

export const SiteFooter = () => (
  <footer className="bg-[#020617] border-t border-slate-800 py-14 text-slate-100" data-testid="site-footer">
    <div className="max-w-7xl mx-auto px-6 lg:px-10 grid md:grid-cols-12 gap-10">
      <div className="md:col-span-4">
        <p className="font-heading font-black text-lg">
          OnBuy<span className="text-[#0EA5E9]">Solutions</span>
        </p>
        <p className="text-xs text-slate-500 mt-3 leading-relaxed max-w-xs">
          Servicios digitales para personas y negocios en el Perú: inteligencia artificial, asesoría
          legal-contable y soluciones QR.
        </p>
        <p className="text-xs text-slate-600 mt-4">© {new Date().getFullYear()} OnBuySolutions · Perú</p>
      </div>
      <div className="md:col-span-5">
        <p className="text-[10px] tracking-[0.2em] uppercase text-slate-500 font-semibold mb-4">Servicios</p>
        <ul className="space-y-2.5 text-xs text-slate-400">
          {SERVICES.map((s) => (
            <li key={s.key}>
              {s.external ? (
                <a href={s.href} target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors" data-testid={`footer-service-${s.key}`}>
                  {s.title}
                </a>
              ) : (
                <Link to={s.href} className="hover:text-white transition-colors" data-testid={`footer-service-${s.key}`}>
                  {s.title}
                </Link>
              )}
            </li>
          ))}
        </ul>
      </div>
      <div className="md:col-span-3">
        <p className="text-[10px] tracking-[0.2em] uppercase text-slate-500 font-semibold mb-4">Legal</p>
        <ul className="space-y-2.5 text-xs text-slate-400">
          <li><Link to="/blog" className="hover:text-white transition-colors" data-testid="footer-link-blog">Blog</Link></li>
          <li><Link to="/terminos" className="hover:text-white transition-colors" data-testid="footer-link-terminos">Términos y Condiciones</Link></li>
          <li><Link to="/privacidad" className="hover:text-white transition-colors" data-testid="footer-link-privacidad">Política de Privacidad</Link></li>
          <li><Link to="/uso-ia" className="hover:text-white transition-colors" data-testid="footer-link-uso-ia">Aviso de Uso de IA</Link></li>
        </ul>
        <Link
          to="/libro-de-reclamaciones"
          data-testid="footer-link-libro-reclamaciones"
          className="mt-5 inline-flex items-center gap-2 border border-slate-700 hover:border-[#0EA5E9] hover:text-white text-xs text-slate-400 px-3.5 py-2 rounded transition-colors"
        >
          <img src="/libro-reclamaciones.png" alt="Libro de Reclamaciones" className="w-7 h-7 object-contain" />
          <span className="font-semibold leading-tight">Libro de<br />Reclamaciones</span>
        </Link>
      </div>
    </div>
    <div className="max-w-7xl mx-auto px-6 lg:px-10 mt-10 pt-6 border-t border-slate-900">
      <p className="text-[11px] text-slate-600 leading-relaxed max-w-4xl">
        OnBuySolutions es un proveedor de servicios tecnológicos y no una entidad financiera ni un estudio de
        abogados. Los contenidos generados con Inteligencia Artificial son orientación informativa y requieren la
        validación final del usuario, conforme a la Ley N° 31814 y su Reglamento (D.S. N° 115-2025-PCM). Tratamiento
        de datos conforme a la Ley N° 29733 y D.S. N° 016-2024-JUS.
      </p>
    </div>
  </footer>
);
