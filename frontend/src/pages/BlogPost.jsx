import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { serviceByKey } from "@/constants/services";
import { SiteNav } from "@/components/SiteNav";
import { SiteFooter } from "@/components/SiteFooter";
import { WhatsAppButton } from "@/components/WhatsAppButton";

const linkCls = "text-[#0284C7] font-semibold underline underline-offset-2 hover:text-[#0EA5E9]";

export const mdComponents = {
  a: ({ href = "", children }) =>
    href.startsWith("/") ? (
      <Link to={href} className={linkCls}>{children}</Link>
    ) : (
      <a href={href} target="_blank" rel="noopener noreferrer" className={linkCls}>{children}</a>
    ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-[#0284C7] bg-sky-50 px-5 py-3 my-5 text-sm italic">{children}</blockquote>
  ),
};

const ServiceCta = ({ svc, className, children }) =>
  svc.external ? (
    <a href={svc.href} target="_blank" rel="noopener noreferrer" className={className} data-testid="blog-post-cta">{children}</a>
  ) : (
    <Link to={svc.href} className={className} data-testid="blog-post-cta">{children}</Link>
  );

export default function BlogPost() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
    api.get(`/blog/${slug}`).then(({ data }) => setPost(data)).catch(() => setMissing(true));
  }, [slug]);

  const svc = serviceByKey(post?.service);

  return (
    <div className="bg-[#F8FAFC] text-[#0F172A] min-h-screen" data-testid="blog-post-page">
      <SiteNav />
      <header className="bg-[#020617] text-white pt-36 pb-16">
        <div className="max-w-3xl mx-auto px-6">
          <Link to="/blog" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors" data-testid="blog-back-link">
            <ArrowLeft size={16} /> Volver al blog
          </Link>
          {post && (
            <>
              <p className="mt-8 text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold">
                {svc.tag} · {new Date(post.created_at).toLocaleDateString("es-PE", { day: "numeric", month: "long", year: "numeric" })}
              </p>
              <h1 className="mt-4 font-heading font-black text-3xl sm:text-4xl lg:text-5xl tracking-tight leading-[1.1]" data-testid="blog-post-title">
                {post.title}
              </h1>
              {post.excerpt && <p className="mt-6 text-slate-300 leading-relaxed">{post.excerpt}</p>}
            </>
          )}
          {missing && <h1 className="mt-8 font-heading font-black text-3xl" data-testid="blog-post-missing">Artículo no encontrado</h1>}
        </div>
      </header>
      {post && (
        <main className="max-w-3xl mx-auto px-6 py-16">
          <article className="markdown-report" data-testid="blog-post-content">
            <ReactMarkdown components={mdComponents}>{post.content}</ReactMarkdown>
          </article>
          <div className="mt-14 bg-[#020617] text-white p-8 lg:p-10 flex flex-col sm:flex-row sm:items-center justify-between gap-6" data-testid="blog-post-cta-box">
            <div>
              <p className="text-[10px] tracking-[0.2em] uppercase text-[#0EA5E9] font-semibold">Contrata el servicio</p>
              <p className="font-heading font-bold text-xl mt-2">{svc.title}</p>
            </div>
            <ServiceCta svc={svc} className="shrink-0 inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-6 py-3.5 rounded-full text-sm transition-colors">
              Contratar ahora <ArrowRight size={16} />
            </ServiceCta>
          </div>
        </main>
      )}
      <SiteFooter />
      <WhatsAppButton defaultService={post?.service || "legal"} />
    </div>
  );
}
