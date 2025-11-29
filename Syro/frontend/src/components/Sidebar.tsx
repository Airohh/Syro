import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle, LogOut, Activity, User } from 'lucide-react';
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
  onSelectConversation 
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
      // Retry logic: try multiple times with delays
      const maxRetries = 3;
      const retryDelay = 2000; // 2 seconds
      
      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          // Utiliser le domaine actuel pour vérifier la santé
          const data = await domainService.getHealth(currentDomain);
          setHealth(data);
          setLoading(false);
          return; // Success, exit the function
        } catch (error) {
          console.log(`Health check attempt ${attempt}/${maxRetries} failed for domain ${currentDomain}`);
          
          if (attempt === maxRetries) {
            // Last attempt failed
            setHealth(null);
            setLoading(false);
          } else {
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, retryDelay));
          }
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [currentDomain]);

  return (
    <aside className="w-sidebar bg-white border-r border-gray-200 flex flex-col h-screen shrink-0">
      {/* Header compact */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center 
            ${domainClasses.bgLight} ${domainClasses.text} shadow-soft`}>
            <DomainIcon className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-semibold text-gray-900 truncate leading-tight">
              {domain.name}
            </h2>
            <p className="text-xs text-gray-500 truncate leading-tight">
              {domain.shortName}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Status */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-3.5 h-3.5 text-gray-400" />
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Statut
            </h3>
          </div>
          {loading ? (
            <div className="flex items-center gap-2 text-gray-400">
              <div className="animate-spin rounded-full h-3 w-3 border-2 border-gray-300 border-t-gray-600"></div>
              <span className="text-xs">Vérification...</span>
            </div>
          ) : health ? (
            <div className="flex items-center gap-2 text-emerald-600">
              <CheckCircle className="w-4 h-4" />
              <span className="text-xs font-medium">En ligne</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-red-600">
              <XCircle className="w-4 h-4" />
              <span className="text-xs font-medium">Hors ligne</span>
            </div>
          )}
        </div>

        {/* Domain info */}
        {health && (
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Instance
            </h3>
            <div className="space-y-2">
              {health.app_name && (
                <div className="text-xs text-gray-700 font-medium bg-gray-50 px-2.5 py-1.5 rounded-md border border-gray-100">
                  {health.app_name}
                </div>
              )}
              {health.domain && (
                <div className="text-xs text-gray-500 bg-gray-50 px-2.5 py-1.5 rounded-md border border-gray-100">
                  Domaine: {health.domain}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Backend Status - État de tous les backends */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Backends
          </h3>
          <BackendStatus />
        </div>

        {/* Historique des conversations */}
        {onNewConversation && onSelectConversation && (
          <ConversationHistory
            onSelectConversation={onSelectConversation}
            onNewConversation={onNewConversation}
          />
        )}

        {/* Upload de documents */}
        <DocumentUpload currentDomain={currentDomain} />

        {/* Lien vers profil */}
        <div>
          <button
            onClick={() => navigate('/profile')}
            className="w-full btn-secondary flex items-center justify-center gap-2 text-sm"
          >
            <User className="w-4 h-4" />
            Profil
          </button>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <button
          onClick={onLogout}
          className="w-full btn-secondary flex items-center justify-center gap-2 text-sm"
        >
          <LogOut className="w-4 h-4" />
          Déconnexion
        </button>
      </div>
    </aside>
  );
}
