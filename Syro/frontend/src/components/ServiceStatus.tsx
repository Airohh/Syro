import { useEffect, useState } from 'react';
import { CheckCircle2, MinusCircle, XCircle } from 'lucide-react';
import api from '../services/api';

interface Readiness {
  qdrant: { ok: boolean; points?: number };
  llm: { ok: boolean; provider: string; chat_model: string };
  reranker: { enabled: boolean; loaded: boolean; failed?: boolean };
}

/** État des dépendances du RAG (GET /health/ready). */
export default function ServiceStatus() {
  const [ready, setReady] = useState<Readiness | null>(null);

  useEffect(() => {
    const load = () => api.get<Readiness>('/health/ready').then(r => setReady(r.data)).catch(() => setReady(null));
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  if (!ready) return null;

  const rows: { label: string; detail: string; state: 'ok' | 'off' | 'ko' }[] = [
    {
      label: 'Qdrant',
      detail: ready.qdrant.ok ? `${ready.qdrant.points ?? 0} chunks` : 'injoignable',
      state: ready.qdrant.ok ? 'ok' : 'ko',
    },
    {
      label: 'LLM',
      detail: `${ready.llm.chat_model} (${ready.llm.provider})`,
      state: ready.llm.ok ? 'ok' : 'ko',
    },
    {
      label: 'Reranker',
      detail: !ready.reranker.enabled
        ? 'désactivé'
        : ready.reranker.loaded
          ? 'chargé'
          : ready.reranker.failed
            ? 'indisponible (ordre RRF)'
            : 'chargement…',
      state: ready.reranker.enabled && ready.reranker.loaded ? 'ok' : 'off',
    },
  ];

  return (
    <div className="bg-zinc-900/60 rounded-lg px-3 py-2 border border-white/5 space-y-1.5">
      {rows.map(row => (
        <div key={row.label} className="flex items-center gap-2 text-xs">
          {row.state === 'ok' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />}
          {row.state === 'off' && <MinusCircle className="w-3.5 h-3.5 text-zinc-500 shrink-0" />}
          {row.state === 'ko' && <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />}
          <span className="text-zinc-400">{row.label}</span>
          <span className="text-zinc-600 ml-auto truncate">{row.detail}</span>
        </div>
      ))}
    </div>
  );
}
