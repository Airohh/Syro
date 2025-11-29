import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import ProfileDashboard from '../components/ProfileDashboard';
import DocumentUploader from '../components/DocumentUploader';
import DocumentList from '../components/DocumentList';
import DomainSelector from '../components/DomainSelector';
import { domainService } from '../services/api';
import { getDomainConfig } from '../utils/domainConfig';

interface ProfilePageProps {
  onLogout: () => void;
}

type Tab = 'dashboard' | 'documents';

export default function ProfilePage({ onLogout }: ProfilePageProps) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [refreshKey, setRefreshKey] = useState(0);
  const [currentDomain, setCurrentDomain] = useState<string>('general');

  // Détecter le domaine actuel (comme ChatPage)
  useEffect(() => {
    const loadDomain = async () => {
      const domainsToTry = ['general', 'tech', 'medical', 'legal', 'finance', 'education'];
      
      for (const domainId of domainsToTry) {
        try {
          const data = await domainService.getDomains(domainId);
          if (data.current_domain) {
            setCurrentDomain(data.current_domain);
            console.log(`✓ Domaine chargé pour profil: ${data.current_domain}`);
            return;
          }
        } catch (error) {
          // Continue
        }
      }
      setCurrentDomain('general');
    };
    
    loadDomain();
  }, []);

  const handleUploadSuccess = () => {
    // Rafraîchir la liste des documents
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="h-14 bg-white border-b border-gray-200 flex items-center px-6 shrink-0 sticky top-0 z-40 backdrop-blur-sm bg-white/95">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-gray-900 to-gray-700 flex items-center justify-center shadow-soft">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <span className="text-sm font-semibold text-gray-900 hidden sm:inline tracking-tight">
                Syro
              </span>
            </div>
            <div className="h-5 w-px bg-gray-200" />
            <button
              onClick={() => navigate('/')}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Chat
            </button>
            <div className="h-5 w-px bg-gray-200" />
            <DomainSelector 
              currentDomain={currentDomain}
              onDomainChange={setCurrentDomain}
            />
          </div>
        </div>
      </header>
      <div className="flex">
        <Sidebar onLogout={onLogout} />
        <main className="flex-1 p-6">
          <div className="max-w-7xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Profil</h1>

            {/* Onglets */}
            <div className="border-b border-gray-200 mb-6">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveTab('dashboard')}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'dashboard'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setActiveTab('documents')}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'documents'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Documents
                </button>
              </nav>
            </div>

            {/* Avertissement domaine */}
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-700">
                📍 <strong>Domaine actuel:</strong> {getDomainConfig(currentDomain).name}
                <br />
                <span className="text-xs text-blue-600">
                  Les statistiques et documents affichés sont ceux du domaine sélectionné.
                </span>
              </p>
            </div>

            {/* Contenu des onglets */}
            <div className="mt-6">
              {activeTab === 'dashboard' && <ProfileDashboard currentDomain={currentDomain} />}
              {activeTab === 'documents' && (
                <div className="space-y-6">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900 mb-4">
                      Upload de documents
                    </h2>
                    <DocumentUploader 
                      currentDomain={currentDomain}
                      onUploadSuccess={handleUploadSuccess} 
                    />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900 mb-4">
                      Mes documents ({getDomainConfig(currentDomain).name})
                    </h2>
                    <DocumentList key={refreshKey} currentDomain={currentDomain} />
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

