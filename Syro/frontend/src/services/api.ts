/// <reference types="vite/client" />
import axios, { AxiosInstance } from 'axios';
import { getDomainApiUrl, getDomainPort } from '../utils/domainPorts';
import { getDomainConfig } from '../utils/domainConfig';

// Use environment variable or default to localhost
const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.MODE === 'production' 
    ? 'https://syro-api.railway.app'  // Change this to your backend URL
    : 'http://localhost:8000');

// Store current domain for API URL
let currentDomainId: string = 'general';

// Store tokens per domain (since each backend has its own database)
const domainTokens: Record<string, string> = {};

// Store login credentials for re-authentication
let loginCredentials: { username: string; password: string } | null = null;

// Create a function to get the API instance with the correct base URL
function createApiInstance(domainId?: string): AxiosInstance {
  const domain = domainId || currentDomainId;
  // Always use getDomainApiUrl to ensure correct port
  const baseURL = getDomainApiUrl(domain);
  
  const instance = axios.create({
    baseURL,
    timeout: 120000, // 120 secondes (2 minutes) pour les gros fichiers
  });

  // Add token to requests
  instance.interceptors.request.use((config) => {
    // Use domain-specific token if available, otherwise fallback to default token
    const domainToken = domainId && domainTokens[domainId] 
      ? domainTokens[domainId] 
      : localStorage.getItem('token');
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
            error.action = `Identifiants par défaut: owner@example.com / ChangeMe123!`;
          } else {
            error.message = `Authentification échouée (401 Unauthorized)`;
            error.userMessage = `Les identifiants sont incorrects ou l'utilisateur n'existe pas dans la base de données.`;
            error.solution = `Initialisez la base de données avec: python scripts/init_db.py`;
            error.action = `Identifiants par défaut: owner@example.com / ChangeMe123!`;
          }
          
          // Try to re-authenticate if we have credentials and it's a domain-specific request
          console.log(`[API] 401 Unauthorized for domain: ${domainId || 'default'}, has credentials: ${!!loginCredentials}`);
          
          if (domainId && loginCredentials) {
            try {
              console.log(`[API] Attempting re-authentication for domain: ${domainId}`);
              const formData = new URLSearchParams();
              formData.append('username', loginCredentials.username);
              formData.append('password', loginCredentials.password);
              
              const loginResponse = await axios.post(`${baseURL}/auth/login`, formData, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              });
              
              // Store the token for this domain
              domainTokens[domainId] = loginResponse.data.access_token;
              console.log(`[API] Re-authentication successful for domain: ${domainId}`);
              
              // Retry the original request with the new token
              if (error.config) {
                error.config.headers.Authorization = `Bearer ${loginResponse.data.access_token}`;
                return axios.request(error.config);
              }
            } catch (loginError: any) {
              console.error(`[API] Re-authentication failed for domain ${domainId}:`, loginError);
              
              // Si la re-authentification échoue, essayer de se connecter à tous les domaines
              if (loginCredentials) {
                try {
                  console.log(`[API] Attempting to login to all domains after re-auth failure`);
                  await authService.loginToAllDomains(loginCredentials.username, loginCredentials.password, true);
                  // Retry the original request
                  if (error.config) {
                    const retryToken = domainTokens[domainId] || localStorage.getItem('token');
                    if (retryToken) {
                      error.config.headers.Authorization = `Bearer ${retryToken}`;
                      return axios.request(error.config);
                    }
                  }
                } catch (allDomainsError) {
                  console.error(`[API] Login to all domains also failed:`, allDomainsError);
                }
              }
              
              error.message = `Non autorisé pour ${domainName}.`;
              error.userMessage = `Vous devez vous reconnecter pour utiliser ${domainName}.`;
              error.solution = 'Cliquez sur "Se déconnecter" puis reconnectez-vous.';
              error.action = 'Reconnexion nécessaire.';
            }
          } else {
            if (!domainId) {
              error.message = 'Non autorisé.';
              error.userMessage = 'Vérifiez vos identifiants de connexion.';
              error.solution = 'Vérifiez votre email et mot de passe.';
            } else if (!loginCredentials) {
              error.message = `Non autorisé pour ${domainName}.`;
              error.userMessage = `Vous devez vous reconnecter pour utiliser ${domainName}.`;
              error.solution = 'Cliquez sur "Se déconnecter" puis reconnectez-vous.';
              error.action = 'Reconnexion nécessaire.';
            }
          }
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

  return instance;
}

// Default API instance
const api = createApiInstance();

// Export createApiInstance for use in other services
export { createApiInstance };

// Function to update the API base URL when domain changes
export function updateApiDomain(domainId: string) {
  currentDomainId = domainId;
  // Note: We can't change the baseURL of an existing axios instance,
  // so we'll create a new instance for each domain-specific call
}

// Function to get API instance for a specific domain
export function getApiForDomain(domainId: string): AxiosInstance {
  return createApiInstance(domainId);
}

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle errors globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      error.message = 'La requête a pris trop de temps. Vérifiez que le backend est bien démarré.';
    } else if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
      error.message = `Impossible de se connecter au backend sur ${DEFAULT_API_BASE_URL}. Vérifiez que l'API est bien lancée sur le port 8000.`;
    } else if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      if (status === 401) {
        error.message = 'Non autorisé. Vérifiez vos identifiants.';
      } else if (status === 404) {
        error.message = 'Endpoint non trouvé. Vérifiez la configuration de l\'API.';
      } else if (status >= 500) {
        error.message = 'Erreur serveur. Vérifiez les logs du backend.';
      }
    }
    return Promise.reject(error);
  }
);

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface Message {
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
    // Store credentials for re-authentication
    loginCredentials = { username, password };
    
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    // Use domain-specific API instance if provided
    const apiInstance = domainId ? getApiForDomain(domainId) : api;
    const response = await apiInstance.post<LoginResponse>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    
    // Store token for the domain
    if (domainId) {
      domainTokens[domainId] = response.data.access_token;
    }
    
    // Also store in localStorage for backward compatibility
    localStorage.setItem('token', response.data.access_token);
    
    return response.data;
  },
  
  // Login to all domains at once (excluding general, which should be logged in separately)
  // NOTE: Avec l'architecture multi-domaines, tous les domaines utilisent le même backend (port 8000)
  // Un seul login suffit car le backend gère tous les domaines
  loginToAllDomains: async (username: string, password: string, skipGeneral: boolean = false): Promise<void> => {
    loginCredentials = { username, password };
    
    // Avec l'architecture multi-domaines, un seul login sur le backend unique suffit
    // Le backend gère tous les domaines via les routes /domains/{domain}/...
    // On ne fait qu'un seul login sur le port 8000
    console.log('[API] Architecture multi-domaines: un seul backend, login unique suffit');
    
    // Si on a déjà fait un login sur 'general', on n'a pas besoin de se connecter aux autres
    // car ils utilisent tous le même backend
    if (skipGeneral) {
      console.log('[API] Login général déjà effectué, pas besoin de login supplémentaire pour les autres domaines');
      return;
    }
    
    // Si skipGeneral est false, on fait un login sur 'general' (qui est déjà fait dans App.tsx)
    // Donc on ne fait rien ici
    console.log('[API] Login unique effectué, tous les domaines sont accessibles via le même backend');
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
    const response = await apiInstance.post('/documents/files', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
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

