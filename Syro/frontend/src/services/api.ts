/// <reference types="vite/client" />
import axios, { AxiosInstance } from 'axios';
import { getDomainApiUrl, getDomainPort } from '../utils/domainPorts';
import { getDomainConfig } from '../utils/domainConfig';

let currentDomainId: string = 'general';

// Cache instances by baseURL to avoid creating new Axios instances on every call
const instanceCache = new Map<string, AxiosInstance>();

// Create a function to get the API instance with the correct base URL
function createApiInstance(domainId?: string): AxiosInstance {
  const domain = domainId || currentDomainId;
  // Always use getDomainApiUrl to ensure correct port
  const baseURL = getDomainApiUrl(domain);

  if (instanceCache.has(baseURL)) return instanceCache.get(baseURL)!;
  
  const instance = axios.create({
    baseURL,
    timeout: 120000, // 120 secondes (2 minutes) pour les gros fichiers
  });

  // Add token to requests
  instance.interceptors.request.use((config) => {
    const domainToken = localStorage.getItem('token');
    if (domainToken) {
      config.headers.Authorization = `Bearer ${domainToken}`;
    }
    
    // Ne pas définir Content-Type pour FormData, laissez Axios le faire automatiquement
    // Axios définira automatiquement multipart/form-data avec boundary pour FormData
    if (!(config.data instanceof FormData)) {
      // Seulement définir Content-Type pour les requêtes JSON
      if (!config.headers['Content-Type']) {
        config.headers['Content-Type'] = 'application/json';
      }
    }
    
    return config;
  });

  // Handle errors globally
  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      // Get domain info for user-friendly messages
      const domainName = domainId ? getDomainConfig(domainId).name : 'Syro';
      const port = domainId ? getDomainPort(domainId) : 8000;
      
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        error.message = `Le backend ${domainName} met trop de temps à répondre.`;
        error.userMessage = `Le serveur ${domainName} semble surchargé ou lent. Réessayez dans quelques instants.`;
        error.solution = 'Vérifiez que le backend est bien démarré et fonctionne correctement.';
        error.action = 'Attendez quelques secondes puis réessayez.';
      } else if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
        error.message = `Impossible de se connecter au backend ${domainName}.`;
        error.userMessage = `Le backend ${domainName} n'est pas démarré ou n'est pas accessible sur le port ${port}.`;
        error.solution = 'Vérifiez que l\'API tourne : docker compose ps (ou make logs).';
      } else if (error.response) {
        // Server responded with error status
        const status = error.response.status;
        if (status === 401) {
          // 401 Unauthorized - améliorer le message d'erreur
          if (error.response.data && error.response.data.detail) {
            error.message = `Authentification échouée: ${error.response.data.detail}`;
            error.userMessage = `Les identifiants sont incorrects ou l'utilisateur n'existe pas.`;
            error.solution = `Compte de démo : demo@syro.local / syro-demo`;
          } else {
            error.message = `Authentification échouée (401 Unauthorized)`;
            error.userMessage = `Les identifiants sont incorrects ou l'utilisateur n'existe pas dans la base de données.`;
            error.solution = `Compte de démo : demo@syro.local / syro-demo`;
          }
          
          error.technicalMessage = error.message;
          error.message = 'Non autorisé. Reconnectez-vous.';
          localStorage.removeItem('token');
        } else if (status === 404) {
          error.message = 'Endpoint non trouvé.';
          error.userMessage = 'La fonctionnalité demandée n\'est pas disponible sur ce backend.';
          error.solution = 'Vérifiez que vous utilisez la bonne version du backend.';
        } else if (status === 503) {
          error.message = 'Service indisponible.';
          error.userMessage = error.response.data?.detail || 'Un service (LLM ou Qdrant) est indisponible.';
          error.solution = 'Vérifiez que tous les conteneurs tournent : docker compose ps';
        } else if (status >= 500) {
          error.message = 'Erreur serveur.';
          error.userMessage = 'Une erreur s\'est produite sur le serveur.';
          error.solution = 'Vérifiez les logs du backend pour plus de détails.';
          error.action = 'Consultez les logs : docker compose logs syro-api';
        }
      }
      return Promise.reject(error);
    }
  );

  instanceCache.set(baseURL, instance);
  return instance;
}

// Default API instance
const api = createApiInstance();

// Export createApiInstance for use in other services
export { createApiInstance };

// Function to get API instance for a specific domain
export function getApiForDomain(domainId: string): AxiosInstance {
  return createApiInstance(domainId);
}


export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  usage?: number;
}

export interface Source {
  text: string;
  score: number;
  metadata?: {
    source?: number;
    filename?: string;
    header?: string;
    domain?: string;
    rerank_score?: number | null;
    [key: string]: any;
  };
}

export interface ChatResponse {
  message: string;
  sources: Source[];
  conversation_id: number;
  usage: number;
}

export interface Domain {
  id: string;
  name: string;
  description: string;
}

export const authService = {
  login: async (username: string, password: string, domainId?: string): Promise<LoginResponse> => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const apiInstance = domainId ? getApiForDomain(domainId) : api;
    const response = await apiInstance.post<LoginResponse>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    localStorage.setItem('token', response.data.access_token);
    return response.data;
  },
  
};

export const chatService = {
  /**
   * Envoie une question. `domainId` = 'general' → recherche dans tous les
   * documents ; sinon le retrieval est filtré sur ce domaine.
   * `conversationId` = id serveur de la conversation (null pour en créer une).
   */
  sendMessage: async (
    content: string,
    conversationId: number | null = null,
    domainId: string = 'general',
  ): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/chat/message', {
      content,
      conversation_id: conversationId,
      domain: domainId === 'general' ? null : domainId,
    });
    return response.data;
  },
};

export const domainService = {
  getDomains: async (domainId?: string): Promise<{ current_domain: string; current_config: any; available_domains: Domain[] }> => {
    const apiInstance = domainId ? getApiForDomain(domainId) : api;
    const response = await apiInstance.get('/domains');
    return response.data;
  },
  
  getHealth: async (domainId?: string): Promise<{ status: string; domain: string; app_name: string }> => {
    // Avec l'architecture multi-domaines, utiliser la route /domains/{domain}/health
    // si un domaine spécifique est demandé, sinon /health
    if (domainId && domainId !== 'general') {
      const apiInstance = getApiForDomain(domainId);
      const response = await apiInstance.get(`/domains/${domainId}/health`);
      return response.data;
    } else {
      // Pour 'general' ou pas de domaine, utiliser /health
      const apiInstance = domainId ? getApiForDomain(domainId) : api;
      const response = await apiInstance.get('/health');
      return response.data;
    }
  },
};

export const documentService = {
  uploadFile: async (file: File, tags?: string, domainId?: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    if (tags) formData.append('tags', tags);
    // Domaine choisi dans l'UI ; sinon le worker classe le document lui-même.
    if (domainId && domainId !== 'general') formData.append('domain', domainId);
    const response = await api.post('/documents/files', formData);
    return response.data;
  },

  uploadText: async (title: string, content: string, tags?: string, domainId?: string): Promise<any> => {
    const apiInstance = domainId ? getApiForDomain(domainId) : api;
    const response = await apiInstance.post('/documents/text', {
      title,
      content,
      tags: tags ? tags.split(',').map(t => t.trim()) : [],
    });
    return response.data;
  },

  list: async (domainId?: string): Promise<any> => {
    const apiInstance = domainId ? getApiForDomain(domainId) : api;
    const response = await apiInstance.get('/documents');
    return response.data;
  },
};

export default api;

