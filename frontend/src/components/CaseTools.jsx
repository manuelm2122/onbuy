import { useState } from "react";
import { Archive, BookOpenText, Calculator, CalendarClock, ChevronDown, FileStack, ListChecks, Loader2, Wallet, Wrench } from "lucide-react";
import { toast } from "sonner";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { downloadFromApi } from "@/lib/download";
import { CaseCalculators } from "@/components/CaseCalculators";
import { CaseTimeline } from "@/components/CaseTimeline";
import { CaseChecklist } from "@/components/CaseChecklist";
import { CaseFacts } from "@/components/CaseFacts";
import { CaseLedger } from "@/components/CaseLedger";
import { CaseBundle } from "@/components/CaseBundle";

const TOOLS = [
  { key: "calculators", testId: "calculators-btn", icon: Calculator, label: "Calculadoras", hint: "Liquidaciones exactas" },
  { key: "timeline", testId: "timeline-btn", icon: CalendarClock, label: "Plazos", hint: "Línea de tiempo y recordatorios" },
  { key: "checklist", testId: "checklist-btn", icon: ListChecks, label: "Checklist de requisitos", hint: "Qué reunir para tu trámite" },
  { key: "facts", testId: "facts-btn", icon: BookOpenText, label: "Cuaderno de hechos", hint: "Cronología con pruebas" },
  { key: "ledger", testId: "ledger-btn", icon: Wallet, label: "Pagos y deudas", hint: "Saldo al día con comprobantes" },
  { key: "bundle", testId: "bundle-btn", icon: FileStack, label: "Expediente para presentar", hint: "Un PDF foliado con anexos" },
];

export const CaseTools = ({ caseId, onChanged }) => {
  const [active, setActive] = useState(null);
  const [zipping, setZipping] = useState(false);
  const dialog = (key) => ({ caseId, open: active === key, onOpenChange: (v) => setActive(v ? key : null) });

  const downloadZip = async () => {
    setZipping(true);
    toast.info("Preparando la copia completa del caso…");
    try {
      await downloadFromApi(`/cases/${caseId}/download-zip`, { fallback: "Caso.zip" });
      toast.success("Caso descargado");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setZipping(false);
    }
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button data-testid="case-tools-btn" className="inline-flex items-center gap-1.5 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-3.5 py-1.5 rounded-full text-xs transition-colors">
            {zipping ? <Loader2 className="animate-spin" size={13} /> : <Wrench size={13} />} Herramientas <ChevronDown size={12} />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-72" data-testid="case-tools-menu">
          {TOOLS.map((t) => (
            <DropdownMenuItem key={t.key} onSelect={() => setTimeout(() => setActive(t.key), 0)} data-testid={t.testId} className="gap-3 py-2 cursor-pointer">
              <t.icon size={16} className="text-[#0284C7] shrink-0" />
              <span className="flex flex-col">
                <span className="text-sm font-semibold">{t.label}</span>
                <span className="text-[11px] text-slate-500">{t.hint}</span>
              </span>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={downloadZip} disabled={zipping} data-testid="zip-btn" className="gap-3 py-2 cursor-pointer">
            <Archive size={16} className="text-[#0284C7] shrink-0" />
            <span className="flex flex-col">
              <span className="text-sm font-semibold">Descargar caso completo</span>
              <span className="text-[11px] text-slate-500">ZIP con conversación, documentos y archivos</span>
            </span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <CaseCalculators {...dialog("calculators")} onDone={onChanged} />
      <CaseTimeline {...dialog("timeline")} />
      <CaseChecklist {...dialog("checklist")} />
      <CaseFacts {...dialog("facts")} onChanged={onChanged} />
      <CaseLedger {...dialog("ledger")} onChanged={onChanged} />
      <CaseBundle {...dialog("bundle")} />
    </>
  );
};
