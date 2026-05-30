import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, XCircle, LogOut, User, Wifi } from 'lucide-react';
import { domainService } from '../services/api';
import { getDomainConfig } from '../utils/domainConfig';
import { getDomainClasses } from '../utils/domainStyles';
import ConversationHistory from './ConversationHistory';
import DocumentUpload from './DocumentUpload';
import BackendStatus from './BackendStatus';

interface SidebarProps {
  onLogout: () => void;
  currentDomain?: string;
  onNewConversation?: () => void;
  onSelectConversation?: (messages: any[], conversationId?: string) => void;
}

export default function Sidebar({
  onLogout,
  currentDomain = 'general',
  onNewConversation,
  onSelectConversation,
}: SidebarProps) {
  const navigate = useNavigate();
  const [health, setHealth] = useState<{ status: string; domain?: string; app_name?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const domain = getDomainConfig(currentDomain);
  const domainClasses = getDomainClasses(currentDomain);
  const DomainIcon = domain.icon;

  useEffect(() => {
    const checkHealth = async () => {
      setLoading(true);
      for (let attempt = 1; attempt <= 3; attempt++) {
        try {
          const data = await domainService.getHealth(currentDomain);
          setHealth(data);
          setLoading(false);
          return;
        } catch {
          if (attempt === 3) {
            setHealth(null);
            setLoading(false);
          } else {
            await new Promise(r => setTimeout(r, 2000));
          }
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [currentDomain]);

  return (
    <aside className="w-sidebar bg-zinc-950 border-r border-white/5 flex flex-col h-screen shrink-0">
      {/* Domain header */}
      <div className="px-4 py-3.5 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0
            ${domainClasses.bgLight} ${domainClasses.text}`}>
            <DomainIcon className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-zinc-200 truncate leading-tight">{domain.name}</p>
            <p className="text-xs text-zinc-600 truncate leading-tight">{domain.shortName}</p>
          </div>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-5">

        {/* Status */}
        <section>
          <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-widest mb-2 px-1">
            Statut
          </p>
          <div className="bg-zinc-900/60 rounded-lg px-3 py-2.5 border border-white/5">
            {loading ? (
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-zinc-600 animate-pulse" />
                <span className="text-xs text-zinc-600">Vérification...</span>
              </div>
            ) : health ? (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span className="text-xs text-emerald-400 font-medium">En ligne</span>
                {health.app_name && (
                  <span className="text-xs text-zinc-600 ml-auto truncate">{health.app_name}</span>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                <span className="text-xs text-red-400 font-medium">Hors ligne</span>
              </div>
            )}
          </div>
        </section>

        {/* Backends */}
        <section>
          <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-widest mb-2 px-1 flex items-center gap-1.5">
            <Wifi className="w-3 h-3" /> Backends
          </p>
          <BackendStatus />
        </section>

        {/* Conversation history */}
        {onNewConversation && onSelectConversation && (
          <ConversationHistory
            onSelectConversation={onSelectConversation}
            onNewConversation={onNewConversation}
          />
        )}

        {/* Document upload */}
        <DocumentUpload currentDomain={currentDomain} />
      </div>

      {/* Footer actions */}
      <div className="p-3 border-t border-white/5 space-y-1.5">
        <button
          onClick={() => navigate('/profile')}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-zinc-400
            hover:text-zinc-100 hover:bg-zinc-800 transition-all duration-150 cursor-pointer text-sm"
        >
          <User className="w-4 h-4 shrink-0" />
          <span>Profil</span>
        </button>
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-zinc-500
            hover:text-red-400 hover:bg-red-500/10 transition-all duration-150 cursor-pointer text-sm"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          <span>Déconnexion</span>
        </button>
      </div>
    </aside>
  );
}
