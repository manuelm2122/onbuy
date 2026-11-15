import { useEffect, useState } from "react";
import { Sparkles, Plus, Pencil, Trash2, ExternalLink, Save, X } from "lucide-react";
import { toast } from "sonner";
import { api, BACKEND_URL, formatApiErrorDetail } from "@/lib/api";
import { SERVICES } from "@/constants/services";

const EMPTY = { title: "", excerpt: "", content: "", service: "legal", cover_image: "", published: true };
const label = "text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold";
const input = "mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors bg-white";

const parseGenerated = (raw) => {
  const title = raw.match(/^\s*TITULO:\s*(.+)$/m)?.[1]?.trim() || "";
  const excerpt = raw.match(/^\s*RESUMEN:\s*(.+)$/m)?.[1]?.trim() || "";
  const content = raw.replace(/^\s*TITULO:.*$/m, "").replace(/^\s*RESUMEN:.*$/m, "").trim();
  return { title, excerpt, content };
};

export const AdminBlog = () => {
  const [posts, setPosts] = useState([]);
  const [form, setForm] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [topic, setTopic] = useState("");
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = () => api.get("/admin/blog").then(({ data }) => setPosts(data)).catch(() => toast.error("No se pudo cargar el blog"));
  useEffect(() => { load(); }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const openNew = () => { setEditingId(null); setForm(EMPTY); setTopic(""); };
  const openEdit = (p) => { setEditingId(p.id); setForm({ ...EMPTY, ...p, cover_image: p.cover_image || "" }); setTopic(""); };
  const close = () => { setForm(null); setEditingId(null); };

  const generate = async () => {
    if (topic.trim().length < 5) return toast.error("Escribe el tema del artículo");
    setGenerating(true);
    let raw = "";
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/blog/generate`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic.trim(), service: form.service }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Error al generar");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        raw += decoder.decode(value, { stream: true });
        const parsed = parseGenerated(raw);
        setForm((f) => ({ ...f, ...parsed }));
      }
      if (raw.includes("[ERROR_IA]")) {
        toast.error(`La IA devolvió un error: ${raw.split("[ERROR_IA]")[1].trim()}`);
        setForm((f) => ({ ...f, content: f.content.split("[ERROR_IA]")[0].trim() }));
      } else {
        toast.success("Artículo generado. Revísalo y guárdalo.");
      }
    } catch (err) {
      toast.error(formatApiErrorDetail(err.message));
    } finally {
      setGenerating(false);
    }
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form, cover_image: form.cover_image || null };
      if (editingId) await api.put(`/admin/blog/${editingId}`, payload);
      else await api.post("/admin/blog", payload);
      toast.success("Artículo guardado");
      close();
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (p) => {
    if (!window.confirm(`¿Eliminar "${p.title}"?`)) return;
    try {
      await api.delete(`/admin/blog/${p.id}`);
      toast.success("Artículo eliminado");
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    }
  };

  if (form)
    return (
      <form onSubmit={save} className="bg-white border border-slate-200 p-6 space-y-5" data-testid="blog-editor">
        <div className="flex items-center justify-between">
          <h3 className="font-heading font-bold text-[#0F172A]">{editingId ? "Editar artículo" : "Nuevo artículo"}</h3>
          <button type="button" onClick={close} className="text-slate-400 hover:text-slate-700 transition-colors" data-testid="blog-editor-close-btn"><X size={20} /></button>
        </div>

        <div className="bg-sky-50 border border-sky-200 p-5">
          <div className="flex items-center gap-2 text-[#0284C7]">
            <Sparkles size={18} />
            <p className="font-heading font-bold text-sm">Generar con IA</p>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            La IA escribe el artículo e incluye siempre enlaces directos para contratar el servicio elegido.
          </p>
          <div className="mt-4 grid sm:grid-cols-3 gap-3">
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Tema: ej. Cómo cobrar una deuda sin ir a juicio"
              data-testid="blog-topic-input"
              className="sm:col-span-2 border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm bg-white"
            />
            <button
              type="button"
              onClick={generate}
              disabled={generating}
              data-testid="blog-generate-btn"
              className="inline-flex items-center justify-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold px-5 py-2.5 rounded-full text-sm transition-colors"
            >
              <Sparkles size={15} /> {generating ? "Generando…" : "Generar artículo"}
            </button>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className={label}>Servicio que promociona</label>
            <select value={form.service} onChange={set("service")} data-testid="blog-service-select" className={input}>
              {SERVICES.map((s) => <option key={s.key} value={s.key}>{s.title}</option>)}
            </select>
          </div>
          <div>
            <label className={label}>Imagen de portada (URL, opcional)</label>
            <input value={form.cover_image} onChange={set("cover_image")} placeholder="https://…" data-testid="blog-cover-input" className={input} />
          </div>
        </div>
        <div>
          <label className={label}>Título</label>
          <input required minLength={3} value={form.title} onChange={set("title")} data-testid="blog-title-input" className={input} />
        </div>
        <div>
          <label className={label}>Resumen</label>
          <textarea rows={2} value={form.excerpt} onChange={set("excerpt")} data-testid="blog-excerpt-input" className={`${input} resize-y`} />
        </div>
        <div>
          <label className={label}>Contenido (Markdown)</label>
          <textarea required rows={18} value={form.content} onChange={set("content")} data-testid="blog-content-input" className={`${input} font-mono text-xs resize-y`} />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={form.published} onChange={set("published")} data-testid="blog-published-checkbox" />
          Publicado (visible en la web)
        </label>
        <button type="submit" disabled={saving || generating} data-testid="blog-save-btn" className="inline-flex items-center gap-2 bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold px-8 py-3 rounded-full text-sm transition-colors">
          <Save size={16} /> {saving ? "Guardando…" : "Guardar artículo"}
        </button>
      </form>
    );

  return (
    <div className="bg-white border border-slate-200" data-testid="admin-blog">
      <div className="p-6 flex items-center justify-between border-b border-slate-200">
        <div>
          <h3 className="font-heading font-bold text-[#0F172A]">Blog</h3>
          <p className="text-xs text-slate-500 mt-1">{posts.length} artículo(s)</p>
        </div>
        <button onClick={openNew} data-testid="blog-new-btn" className="inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-5 py-2.5 rounded-full text-sm transition-colors">
          <Plus size={16} /> Nuevo artículo
        </button>
      </div>
      <ul className="divide-y divide-slate-200">
        {posts.map((p) => (
          <li key={p.id} className="p-6 flex items-start justify-between gap-4" data-testid={`blog-row-${p.id}`}>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <p className="font-semibold text-sm text-[#0F172A]">{p.title}</p>
                <span className={`text-[10px] font-bold tracking-[0.1em] uppercase px-2 py-0.5 rounded-full ${p.published ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                  {p.published ? "Publicado" : "Borrador"}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1 line-clamp-2">{p.excerpt}</p>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              {p.published && (
                <a href={`/blog/${p.slug}`} target="_blank" rel="noopener noreferrer" className="p-2 text-slate-400 hover:text-[#0284C7] transition-colors" data-testid={`blog-view-${p.id}`}><ExternalLink size={16} /></a>
              )}
              <button onClick={() => openEdit(p)} className="p-2 text-slate-400 hover:text-[#0284C7] transition-colors" data-testid={`blog-edit-${p.id}`}><Pencil size={16} /></button>
              <button onClick={() => remove(p)} className="p-2 text-slate-400 hover:text-red-600 transition-colors" data-testid={`blog-delete-${p.id}`}><Trash2 size={16} /></button>
            </div>
          </li>
        ))}
        {posts.length === 0 && <li className="p-10 text-center text-sm text-slate-500">Aún no hay artículos.</li>}
      </ul>
    </div>
  );
};
