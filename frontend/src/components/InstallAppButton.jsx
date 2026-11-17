import { useEffect, useState } from "react";
import { Download, PlusSquare, Share } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

let deferredPrompt = null;
const listeners = new Set();
const notify = () => listeners.forEach((fn) => fn());

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    notify();
  });
  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    notify();
  });
}

const isStandalone = () => window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

export const InstallAppButton = ({ className = "" }) => {
  const [, refresh] = useState(0);
  const [help, setHelp] = useState(false);

  useEffect(() => {
    const fn = () => refresh((n) => n + 1);
    listeners.add(fn);
    return () => listeners.delete(fn);
  }, []);

  if (isStandalone() || (!deferredPrompt && !isIos())) return null;

  const install = async () => {
    if (!deferredPrompt) return setHelp(true);
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    deferredPrompt = null;
    notify();
    if (outcome === "accepted") toast.success("App instalada. Búscala en tu pantalla de inicio.");
  };

  return (
    <>
      <button onClick={install} data-testid="install-app-btn" className={`inline-flex items-center gap-2 font-semibold transition-colors ${className}`}>
        <Download size={15} /> Instalar app
      </button>
      <Dialog open={help} onOpenChange={setHelp}>
        <DialogContent className="sm:max-w-sm" data-testid="install-ios-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">Instalar en iPhone o iPad</DialogTitle>
            <DialogDescription>Abre esta página en Safari y sigue estos pasos:</DialogDescription>
          </DialogHeader>
          <ol className="space-y-3 text-sm text-slate-700">
            <li className="flex items-center gap-3"><Share size={18} className="text-[#0284C7] shrink-0" /> 1. Toca el botón Compartir.</li>
            <li className="flex items-center gap-3"><PlusSquare size={18} className="text-[#0284C7] shrink-0" /> 2. Elige "Añadir a pantalla de inicio".</li>
            <li className="flex items-center gap-3"><Download size={18} className="text-[#0284C7] shrink-0" /> 3. Confirma con "Añadir".</li>
          </ol>
        </DialogContent>
      </Dialog>
    </>
  );
};
