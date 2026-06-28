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
        error.solution = `Vérifiez que le backend ${domainName} est lancé. Consultez les logs de démarrage (syro-startup.log dans le dossier frontend).`;
        error.action = 'Relancer l\'application ou vérifier les fenêtres PowerShell des backends.';
      } else if (error.response) {
        // Server responded with error status
        const status = error.response.status;
        if (status === 401) {
          // 401 Unauthorized - améliorer le message d'erreur
          if (error.response.data && error.response.data.detail) {
            error.message = `Authentification échouée: ${error.response.data.detail}`;
            error.userMessage = `Les identifiants sont incorrects ou l'utilisateur n'existe pas.`;
            error.solution = `Vérifiez vos identifiants ou initialisez la base de données avec: python scripts/init_db.py`;
          } else {
            error.message = `Authentification échouée (401 Unauthorized)`;
            error.userMessage = `Les identifiants sont incorrects ou l'utilisateur n'existe pas dans la base de données.`;
            error.solution = `Initialisez la base de données avec: python scripts/init_db.py`;
          }
          
          error.technicalMessage = error.message;
          error.message = 'Non autorisé. Reconnectez-vous.';
          localStorage.removeItem('token');
        } else if (status === 404) {
          error.message = 'Endpoint non trouvé.';
          error.userMessage = 'La fonctionnalité demandée n\'est pas disponible sur ce backend.';
          error.solution = 'Vérifiez que vous utilisez la bonne version du backend.';
        } else if (status >= 500) {
          error.message = 'Erreur serveur.';
          error.userMessage = 'Une erreur s\'est produite sur le serveur.';
          error.solution = 'Vérifiez les logs du backend pour plus de détails.';
          error.action = 'Consultez les fenêtres PowerShell des backends ou les logs.';
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
  metadata?: Record<string, any>;
}

export interface ChatResponse {
  message: string;
  sources: Source[];
  conversation_id: string;
  usage: number;
}

export interface Domain {
  id: string;
  name: string;
  description: string;
  document_types: string[];
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
  sendMessage: async (
    content: string,
    conversationId: string | null = null,
    agentName?: string,
    domainId?: string
  ): Promise<ChatResponse> => {
    const url = agentName 
      ? `/agents/chat/${agentName}`
      : '/chat/message';
    
    // Use domain-specific API instance if domainId is provided
    const apiInstance = domainId ? getApiForDomain(domainId) : api;
    
    const response = await apiInstance.post<ChatResponse>(url, {
      content,
      conversation_id: conversationId,
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

export const agentService = {
  list: async (): Promise<{ agents: Array<{ name: string; personality: string }> }> => {
    const response = await api.get('/agents/list');
    return response.data;
  },
};

export const documentService = {
  uploadFile: async (file: File, tags?: string, domainId?: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    if (tags) {
      formData.append('tags', tags);
    }
    
    const apiInstance = domainId ? getApiForDomain(domainId) : api;
    const response = await apiInstance.post('/documents/files', formData);
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

