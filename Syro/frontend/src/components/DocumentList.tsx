import { useState, useEffect } from 'react';
import { profileService, Document } from '../services/profileService';
import { getDomainConfig } from '../utils/domainConfig';

interface DocumentListProps {
  onRefresh?: () => void;
  currentDomain?: string;
}

export default function DocumentList({ onRefresh, currentDomain = 'general' }: DocumentListProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterDomain, setFilterDomain] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadDocuments();
  }, [filterDomain, currentDomain]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const data = await profileService.getDocuments(50, 0, filterDomain || undefined, currentDomain);
      setDocuments(data.documents);
      setError(null);
    } catch (err: any) {
      console.error('Error loading documents:', err);
      setError(err?.message || 'Erreur lors du chargement des documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (onRefresh) {
      // Écouter les événements de refresh
      const handleRefresh = () => loadDocuments();
      window.addEventListener('documentUploaded', handleRefresh);
      return () => window.removeEventListener('documentUploaded', handleRefresh);
    }
  }, [onRefresh]);

  const filteredDocuments = documents.filter((doc) => {
    if (searchQuery) {
      return doc.filename.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  });

  const getDomainFromTags = (tags: string[]): string | null => {
    const domainTag = tags.find((tag) => tag.startsWith('domain:'));
    if (domainTag) {
      return domainTag.replace('domain:', '');
    }
    return null;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'complete':
        return 'text-green-600 bg-green-100';
      case 'pending':
        return 'text-yellow-600 bg-yellow-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">{error}</p>
        <button
          onClick={loadDocuments}
          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
        >
          Réessayer
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filtres et recherche */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Rechercher un document..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
        <select
          value={filterDomain || ''}
          onChange={(e) => setFilterDomain(e.target.value || null)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        >
          <option value="">Tous les domaines</option>
          <option value="general">Général</option>
          <option value="medical">Médical</option>
          <option value="legal">Juridique</option>
          <option value="finance">Finance</option>
          <option value="education">Éducation</option>
          <option value="tech">Tech</option>
        </select>
      </div>

      {/* Liste des documents */}
      {filteredDocuments.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p>Aucun document trouvé</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredDocuments.map((doc) => {
            const domain = getDomainFromTags(doc.tags);
            const domainConfig = domain ? getDomainConfig(domain) : null;

            return (
              <div
                key={doc.id}
                className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">📄</span>
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">{doc.filename}</h4>
                        <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500">
                          <span>{formatDate(doc.created_at)}</span>
                          {domainConfig && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                              {domainConfig.name}
                            </span>
                          )}
                          {doc.source_type && (
                            <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs uppercase">
                              {doc.source_type}
                            </span>
                          )}
                          <span
                            className={`px-2 py-1 rounded text-xs ${getStatusColor(
                              doc.ingestion_status
                            )}`}
                          >
                            {doc.ingestion_status}
                          </span>
                          {doc.chunk_count > 0 && (
                            <span>{doc.chunk_count} chunks</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

