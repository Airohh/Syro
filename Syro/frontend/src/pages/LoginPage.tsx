import { useState } from 'react';
import { MessageSquare } from 'lucide-react';

interface LoginPageProps {
  onLogin: (username: string, password: string) => Promise<boolean>;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState('owner@example.com');
  const [password, setPassword] = useState('ChangeMe123!');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const success = await onLogin(username, password);
      if (!success) {
        setError('Erreur de connexion. Vérifiez vos identifiants. Identifiants par défaut: owner@example.com / ChangeMe123!');
      }
    } catch (error: any) {
      // Afficher le message d'erreur avec les identifiants par défaut si c'est une erreur 401
      let errorMessage = error?.message || 'Erreur de connexion. Vérifiez que le backend est bien lancé sur http://localhost:8000';
      
      // Si c'est une erreur 401, ajouter les identifiants par défaut
      if (error?.response?.status === 401 || errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
        if (!errorMessage.includes('owner@example.com')) {
          errorMessage += ' Identifiants par défaut: owner@example.com / ChangeMe123!';
        }
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="card w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-gray-900 to-gray-700 rounded-2xl mb-4 shadow-medium">
            <MessageSquare className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-semibold text-gray-900 mb-2 tracking-tight">Syro</h1>
          <p className="text-gray-600 text-sm">Assistant IA Multi-Domaines</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              id="username"
              type="email"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input-field"
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
              Mot de passe
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Assurez-vous que l'API Syro est lancée</p>
        </div>
      </div>
    </div>
  );
}

