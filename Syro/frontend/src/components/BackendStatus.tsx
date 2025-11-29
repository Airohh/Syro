import { useState, useEffect } from 'react';
import { domainService } from '../services/api';
import { domains } from '../utils/domainConfig';
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface BackendStatus {
  [domainId: string]: {
    status: 'online' | 'offline' | 'checking';
    error?: string;
  };
}

export default function BackendStatus() {
  const [status, setStatus] = useState<BackendStatus>({});

  useEffect(() => {
    const checkBackend = async () => {
      // NOTE: Avec l'architecture multi-domaines, un seul backend (port 8000) gère tous les domaines
      // On vérifie uniquement le backend unique, pas chaque domaine séparément
      const newStatus: BackendStatus = {};
      
      // Initialiser tous les domaines comme "checking"
      for (const domainId of Object.keys(domains)) {
        newStatus[domainId] = { status: 'checking' };
      }
      setStatus({ ...newStatus });

      try {
        // Un seul appel health check suffit car tous les domaines utilisent le même backend
        await domainService.getHealth('general');
        
        // Si le backend est en ligne, tous les domaines sont disponibles
        for (const domainId of Object.keys(domains)) {
          newStatus[domainId] = { status: 'online' };
        }
        setStatus({ ...newStatus });
      } catch (error: any) {
        // Si le backend est hors ligne, tous les domaines sont hors ligne
        const errorMessage = error.userMessage || error.message || 'Backend non accessible';
        for (const domainId of Object.keys(domains)) {
          newStatus[domainId] = {
            status: 'offline',
            error: errorMessage,
          };
        }
        setStatus({ ...newStatus });
      }
    };

    checkBackend();
    // Vérifier périodiquement (toutes les 30 secondes) - mais un seul appel au backend unique
    const interval = setInterval(checkBackend, 30000);
    return () => clearInterval(interval);
  }, []);

  const onlineCount = Object.values(status).filter(s => s.status === 'online').length;
  const totalCount = Object.keys(status).length;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">État des Backends</h3>
        <span className={`text-xs px-2 py-1 rounded ${
          onlineCount === totalCount 
            ? 'bg-green-100 text-green-700' 
            : onlineCount > 0 
            ? 'bg-yellow-100 text-yellow-700' 
            : 'bg-red-100 text-red-700'
        }`}>
          {onlineCount}/{totalCount} disponibles
        </span>
      </div>
      
      <div className="space-y-2">
        {Object.entries(domains).map(([domainId, domain]) => {
          const backendStatus = status[domainId];
          const DomainIcon = domain.icon;
          
          return (
            <div key={domainId} className="flex items-center gap-2 text-sm">
              {backendStatus?.status === 'online' ? (
                <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
              ) : backendStatus?.status === 'offline' ? (
                <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-yellow-500 animate-pulse flex-shrink-0" />
              )}
              <DomainIcon className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1">{domain.shortName}</span>
              {backendStatus?.error && (
                <span 
                  className="text-xs text-red-600 cursor-help" 
                  title={backendStatus.error}
                >
                  ⚠️
                </span>
              )}
            </div>
          );
        })}
      </div>
      
      {onlineCount < totalCount && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-xs text-yellow-700">
            ⚠️ Certains backends ne sont pas disponibles. 
            Les domaines correspondants peuvent ne pas fonctionner.
          </p>
        </div>
      )}
    </div>
  );
}

