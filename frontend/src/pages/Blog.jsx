import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { SiteNav } from "@/components/SiteNav";
import { SiteFooter } from "@/components/SiteFooter";
import { WhatsAppButton } from "@/components/WhatsAppButton";
import { BlogCard } from "@/components/BlogCard";

export default function Blog() {
  const [posts, setPosts] = useState(null);

  useEffect(() => {
    window.scrollTo(0, 0);
    api.get("/blog").then(({ data }) => setPosts(data)).catch(() => setPosts([]));
  }, []);

  return (
    <div className="bg-[#F8FAFC] text-[#0F172A] min-h-screen" data-testid="blog-page">
      <SiteNav />
      <header className="bg-[#020617] text-white pt-36 pb-20">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-4">Blog</p>
          <h1 className="font-heading font-black text-4xl sm:text-5xl lg:text-6xl tracking-tight max-w-3xl" data-testid="blog-title">
            Casos y guías prácticas
          </h1>
          <p className="text-slate-400 mt-6 max-w-xl leading-relaxed">
            Historias, consejos y pasos concretos para resolver problemas legales, contables y digitales.
          </p>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 lg:px-10 py-20">
        {posts === null ? (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-[#0284C7] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : posts.length === 0 ? (
          <p className="text-slate-500" data-testid="blog-empty">Aún no hay artículos publicados.</p>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {posts.map((p) => <BlogCard key={p.id} post={p} />)}
          </div>
        )}
      </main>
      <SiteFooter />
      <WhatsAppButton />
    </div>
  );
}
