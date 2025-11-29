import { useState, useEffect } from 'react';
import { profileService, ProfileStats } from '../services/profileService';
import StatsCard from './StatsCard';

interface ProfileDashboardProps {
  currentDomain?: string;
}

export default function ProfileDashboard({ currentDomain = 'general' }: ProfileDashboardProps) {
  const [stats, setStats] = useState<ProfileStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, [currentDomain]);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await profileService.getStats(currentDomain);
      setStats(data);
      setError(null);
    } catch (err: any) {
      console.error('Error loading stats:', err);
      setError(err?.message || 'Erreur lors du chargement des statistiques');
    } finally {
      setLoading(false);
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
          onClick={loadStats}
          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
        >
          Réessayer
        </button>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Cartes de statistiques principales */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatsCard
          title="Documents totaux"
          value={stats.documents.total}
          icon={<span className="text-3xl">📄</span>}
          subtitle="documents"
        />
        <StatsCard
          title="Stockage utilisé"
          value={stats.storage.total_gb.toFixed(2)}
          subtitle="GB"
          icon={<span className="text-3xl">💾</span>}
        />
        <StatsCard
          title="Conversations"
          value={stats.usage.conversations}
          icon={<span className="text-3xl">💬</span>}
        />
      </div>

      {/* Statistiques détaillées */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Documents récents</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">7 derniers jours</span>
              <span className="font-semibold">{stats.documents.last_7_days}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">30 derniers jours</span>
              <span className="font-semibold">{stats.documents.last_30_days}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">En attente</span>
              <span className="font-semibold text-yellow-600">{stats.documents.pending}</span>
            </div>
            {stats.documents.failed > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-600">Échoués</span>
                <span className="font-semibold text-red-600">{stats.documents.failed}</span>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Utilisation</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">Messages totaux</span>
              <span className="font-semibold">{stats.usage.messages}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Conversations (7j)</span>
              <span className="font-semibold">{stats.usage.recent_conversations_7d}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Chunks indexés</span>
              <span className="font-semibold">{stats.storage.chunks_indexed}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Documents par domaine */}
      {Object.keys(stats.documents.by_domain).length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Documents par domaine</h3>
          <div className="space-y-2">
            {Object.entries(stats.documents.by_domain).map(([domain, count]) => (
              <div key={domain} className="flex justify-between items-center">
                <span className="text-gray-600 capitalize">{domain}</span>
                <span className="font-semibold">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

