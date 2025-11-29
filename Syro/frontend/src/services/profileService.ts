import { createApiInstance } from './api';
import { getDomainPort } from '../utils/domainPorts';

export interface ProfileStats {
  documents: {
    total: number;
    by_domain: Record<string, number>;
    last_7_days: number;
    last_30_days: number;
    pending: number;
    failed: number;
  };
  storage: {
    total_bytes: number;
    total_mb: number;
    total_gb: number;
    chunks_indexed: number;
  };
  usage: {
    conversations: number;
    messages: number;
    recent_conversations_7d: number;
  };
}

export interface Document {
  id: number;
  filename: string;
  mime_type: string | null;
  status: string;
  tags: string[];
  version: number;
  ingestion_status: string;
  chunk_count: number;
  source_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentsResponse {
  documents: Document[];
  total: number;
  limit: number;
  offset: number;
}

export interface ClassificationResult {
  domain: string;
  confidence: number;
  alternatives: Array<{
    domain: string;
    confidence: number;
  }>;
}

export interface UploadWithClassificationResponse {
  document_id: number;
  version: number;
  status: string;
  chunk_count: number;
  classification: ClassificationResult;
}

export const profileService = {
  /**
   * Obtenir les statistiques du profil utilisateur/organisation
   * @param domainId - Domaine pour lequel récupérer les stats (respecte l'isolation)
   */
  async getStats(domainId: string = 'general'): Promise<ProfileStats> {
    // Utiliser le domaine spécifié pour respecter l'isolation multi-instance
    const apiInstance = createApiInstance(domainId);
    const response = await apiInstance.get<ProfileStats>('/profile/stats');
    return response.data;
  },

  /**
   * Obtenir la liste des documents
   * @param currentDomain - Domaine pour lequel récupérer les documents (respecte l'isolation)
   * @param filterDomain - Filtrer par domaine dans les tags (optionnel)
   */
  async getDocuments(
    limit: number = 50,
    offset: number = 0,
    filterDomain?: string,
    currentDomain: string = 'general'
  ): Promise<DocumentsResponse> {
    // Utiliser le domaine actuel pour respecter l'isolation multi-instance
    const apiInstance = createApiInstance(currentDomain);
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    if (filterDomain) {
      params.append('domain', filterDomain);
    }
    const response = await apiInstance.get<DocumentsResponse>(
      `/profile/documents?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Upload un document avec classification automatique
   */
  async uploadWithClassification(
    file: File,
    domain: string = 'general',
    onProgress?: (progress: number) => void
  ): Promise<UploadWithClassificationResponse> {
    // Utiliser le domaine spécifié pour respecter l'isolation multi-instance
    // Le domaine peut être détecté automatiquement ou choisi par l'utilisateur
    const apiInstance = createApiInstance(domain);
    
    // Vérifier que le token existe
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Vous devez être connecté pour uploader un document. Veuillez vous reconnecter.');
    }
    
    const formData = new FormData();
    formData.append('file', file);
    // Envoyer domain et tags comme FormData (même vides) pour éviter l'erreur 422
    // FastAPI avec Form() attend ces paramètres même s'ils sont optionnels
    formData.append('tags', '');
    formData.append('domain', domain || '');
    // Ajouter les niveaux d'accès et de qualité (par défaut: 1 = public/draft)
    formData.append('access_level_id', '1');
    formData.append('quality_level_id', '1');

    const port = getDomainPort(domain);
    console.log(`[ProfileService] Upload vers ${domain} (port ${port})`);
    console.log(`[ProfileService] Token présent: ${!!token}`);

    const response = await apiInstance.post<UploadWithClassificationResponse>(
      '/documents/upload-with-classification',
      formData,
      {
        // Timeout spécifique pour les uploads (plus long que le timeout global)
        timeout: 180000, // 3 minutes pour les gros fichiers
        // Ne pas définir Content-Type manuellement, laissez axios le faire automatiquement
        // pour multipart/form-data
        headers: {
          // Axios définira automatiquement Content-Type avec boundary pour multipart/form-data
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(progress);
          }
        },
      }
    );

    return response.data;
  },
};

