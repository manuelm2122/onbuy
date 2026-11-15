import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { serviceByKey } from "@/constants/services";

export const BlogCard = ({ post, dark = false }) => {
  const svc = serviceByKey(post.service);
  return (
    <Link
      to={`/blog/${post.slug}`}
      data-testid={`blog-card-${post.slug}`}
      className={`group flex flex-col border transition-colors ${
        dark ? "border-slate-800 bg-slate-900/40 hover:border-[#0EA5E9]" : "border-slate-200 bg-white hover:border-[#0284C7]"
      }`}
    >
      <div className="aspect-[16/9] overflow-hidden bg-slate-900">
        <img
          src={post.cover_image || svc.image}
          alt={post.title}
          loading="lazy"
          className="w-full h-full object-cover opacity-90 group-hover:scale-105 transition-transform duration-500"
        />
      </div>
      <div className="p-6 lg:p-8 flex flex-col flex-1">
        <p className={`text-[10px] tracking-[0.2em] uppercase font-semibold ${dark ? "text-[#0EA5E9]" : "text-[#0284C7]"}`}>
          {svc.tag} · {new Date(post.created_at).toLocaleDateString("es-PE", { day: "numeric", month: "long", year: "numeric" })}
        </p>
        <h3 className={`font-heading font-bold text-lg mt-3 leading-snug ${dark ? "text-white" : "text-[#0F172A]"}`}>{post.title}</h3>
        <p className={`text-sm leading-relaxed mt-3 flex-1 ${dark ? "text-slate-400" : "text-slate-600"}`}>{post.excerpt}</p>
        <span className={`mt-6 inline-flex items-center gap-1.5 text-sm font-semibold ${dark ? "text-[#0EA5E9]" : "text-[#0284C7]"}`}>
          Leer artículo <ArrowUpRight size={16} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
        </span>
      </div>
    </Link>
  );
};
