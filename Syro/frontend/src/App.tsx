import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import LoginPage from './pages/LoginPage';
import ChatPage from './pages/ChatPage';
import ProfilePage from './pages/ProfilePage';
import LaunchScreen from './components/LaunchScreen';
import { authService, domainService } from './services/api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [showLaunch, setShowLaunch] = useState(false);

  useEffect(() => {
    const checkBackend = async () => {
      const maxRetries = 3;
      const retryDelay = 1500;
      
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          console.log(`[Backend Check] Tentative ${attempt}/${maxRetries} - Connexion à http://localhost:8000/health...`);
          
          // Essayer d'abord avec le domaine général (port 8000)
          const startTime = Date.now();
          await domainService.getHealth('general');
          const duration = Date.now() - startTime;
          
          setBackendError(null);
          console.log(`✓ Backend health check successful (attempt ${attempt}, duration: ${duration}ms)`);
          return; // Success, exit the function
        } catch (error: any) {
          const errorDetails = {
            message: error?.message || 'Unknown error',
            code: error?.code || 'NO_CODE',
            response: error?.response ? {
              status: error.response.status,
              statusText: error.response.statusText,
              data: error.response.data
            } : null,
            request: error?.request ? 'Request made but no response' : 'No request made'
          };
          
          console.error(`[Backend Check] Tentative ${attempt}/${maxRetries} échouée:`, errorDetails);
          console.error(`[Backend Check] Erreur complète:`, error);
          
          if (attempt === maxRetries) {
            // Last attempt failed, show detailed error
            let errorMsg = 'Impossible de se connecter au backend Tech. Vérifiez que l\'API est bien lancée sur http://localhost:8000';
            
            if (error?.code === 'ERR_NETWORK' || error?.code === 'ECONNREFUSED') {
              errorMsg = `Erreur réseau: ${error.code}. Le backend n'est pas accessible sur http://localhost:8000`;
            } else if (error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT') {
              errorMsg = `Timeout: Le backend met trop de temps à répondre sur http://localhost:8000`;
            } else if (error?.response) {
              errorMsg = `Erreur HTTP ${error.response.status}: ${error.response.statusText}`;
            } else if (error?.message) {
              errorMsg = error.message;
            }
            
            setBackendError(errorMsg);
            setShowLaunch(true);
            console.error('[Backend Check] Échec après toutes les tentatives:', errorDetails);
          } else {
            // Wait before retrying
            console.log(`[Backend Check] Attente de ${retryDelay}ms avant la prochaine tentative...`);
            await new Promise(resolve => setTimeout(resolve, retryDelay));
          }
        }
      }
    };

    const token = localStorage.getItem('token');
    setIsAuthenticated(!!token);
    
    // Check backend health with retries
    checkBackend().finally(() => setLoading(false));
  }, []);

  const handleLogin = async (username: string, password: string): Promise<boolean> => {
    try {
      // Try to login to the general domain first (required)
      try {
        await authService.login(username, password, 'general');
        setIsAuthenticated(true);
      } catch (error: any) {
        console.error('Login to general domain failed:', error);
        
        // Si c'est une erreur 401, c'est un problème d'authentification
        if (error?.response?.status === 401) {
          throw new Error('Identifiants incorrects. Vérifiez votre email et mot de passe.');
        }
        
        // Sinon, c'est un problème de connexion
        if (error?.code === 'ERR_NETWORK' || error?.code === 'ECONNREFUSED') {
          throw new Error('Impossible de se connecter au backend Tech. Vérifiez que l\'API est bien lancée sur http://localhost:8000');
        }
        
        throw new Error(error?.message || 'Erreur de connexion. Vérifiez que l\'API est bien lancée sur http://localhost:8000');
      }
      
      // NOTE: Avec l'architecture multi-domaines, un seul login suffit
      // Tous les domaines utilisent le même backend (port 8000)
      // Pas besoin de se connecter séparément à chaque domaine
      console.log('[App] Login réussi sur le backend unique, tous les domaines sont accessibles');
      
      return true;
    } catch (error: any) {
      console.error('Login error:', error);
      // Re-throw with better error message
      if (error?.message) {
        throw new Error(error.message);
      }
      throw new Error('Impossible de se connecter au backend. Vérifiez que l\'API est bien lancée sur http://localhost:8000');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      {showLaunch && (
        <LaunchScreen onBackendReady={() => {
          setShowLaunch(false);
          setBackendError(null);
        }} />
      )}
      <Routes>
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to="/" replace />
            ) : (
              <LoginPage onLogin={handleLogin} />
            )
          }
        />
        <Route
          path="/"
          element={
            isAuthenticated ? (
              <ChatPage onLogout={handleLogout} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/profile"
          element={
            isAuthenticated ? (
              <ProfilePage onLogout={handleLogout} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

