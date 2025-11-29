const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

// Désactiver les warnings de sécurité (optionnel, pour un environnement de développement)
process.env.ELECTRON_DISABLE_SECURITY_WARNINGS = 'true';

// IMPORTANT: Configurer les chemins AVANT app.whenReady()
// Configurer un répertoire de cache personnalisé avec les bonnes permissions
// Cela évite les erreurs de cache sur Windows
const userDataPath = path.join(os.homedir(), 'AppData', 'Roaming', 'syro-frontend');
const cachePath = path.join(userDataPath, 'cache');
const gpuCachePath = path.join(userDataPath, 'gpu-cache');

// Créer les répertoires de cache s'ils n'existent pas
try {
  if (!fs.existsSync(userDataPath)) {
    fs.mkdirSync(userDataPath, { recursive: true });
  }
  if (!fs.existsSync(cachePath)) {
    fs.mkdirSync(cachePath, { recursive: true });
  }
  if (!fs.existsSync(gpuCachePath)) {
    fs.mkdirSync(gpuCachePath, { recursive: true });
  }
} catch (err) {
  // Ignorer les erreurs de création de répertoire
  console.warn('Impossible de créer les répertoires de cache:', err.message);
}

// Configurer Electron pour utiliser ces répertoires (AVANT app.whenReady())
app.setPath('userData', userDataPath);
app.setPath('cache', cachePath);
app.setPath('userCache', cachePath);

// Rediriger stderr pour filtrer les erreurs de cache non-bloquantes
const originalStderrWrite = process.stderr.write.bind(process.stderr);
process.stderr.write = function(chunk, encoding, fd) {
  // Filtrer les erreurs de cache GPU/disk qui sont non-bloquantes
  if (chunk && typeof chunk === 'string') {
    if (chunk.includes('cache_util_win.cc') ||
        chunk.includes('disk_cache.cc') ||
        chunk.includes('gpu_disk_cache.cc') ||
        chunk.includes('Unable to move the cache') ||
        chunk.includes('Unable to create cache') ||
        chunk.includes('Gpu Cache Creation failed')) {
      // Ignorer ces erreurs - elles sont non-bloquantes
      return true;
    }
  }
  // Écrire les autres erreurs normalement
  return originalStderrWrite(chunk, encoding, fd);
};

// Gérer les erreurs non capturées
process.on('uncaughtException', (error) => {
  // Ignorer les erreurs de cache GPU (déjà filtrées via stderr, mais on garde cette sécurité)
  if (error.message && (
    error.message.includes('cache') ||
    error.message.includes('Cache') ||
    error.message.includes('GPU')
  )) {
    return;
  }
  console.error('Erreur non capturée:', error);
});

let mainWindow;

function createWindow() {
  // Créer la fenêtre du navigateur
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    backgroundColor: '#ffffff',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      // Désactiver webSecurity en développement pour permettre les connexions localhost
      webSecurity: !isDev,  // false en dev, true en production
      // Permettre les connexions locales pour le développement
      allowRunningInsecureContent: isDev,  // true en dev seulement
      experimentalFeatures: false,
    },
    icon: path.join(__dirname, 'public', 'vite.svg'),
    title: 'Syro - Assistant Multi-Domaines',
    show: false, // Ne pas afficher immédiatement
  });

  // Charger l'application
  if (isDev) {
    // En développement, charger depuis Vite
    // Essayer de charger directement - l'événement did-fail-load gérera l'erreur si le serveur n'est pas prêt
    mainWindow.loadURL('http://localhost:5173');
    
    // Ouvrir les DevTools en développement pour diagnostiquer les problèmes réseau
    mainWindow.webContents.openDevTools();
  } else {
    // En production, charger depuis les fichiers buildés
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  // Afficher la fenêtre une fois que le contenu est chargé
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // Gérer la fermeture
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Gérer les erreurs de chargement
  let retryCount = 0;
  const maxRetries = 10;
  
  function showErrorPage(message, showRetry = true) {
    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>Syro - Erreur de connexion</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            padding: 50px;
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
          }
          .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
          }
          h1 { margin-top: 0; font-size: 2em; }
          .error-code { font-size: 0.9em; opacity: 0.9; margin-top: 10px; }
          .instructions {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            text-align: left;
          }
          .instructions code {
            background: rgba(0, 0, 0, 0.3);
            padding: 2px 8px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
          }
          button {
            background: white;
            color: #667eea;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            margin-top: 20px;
            font-weight: bold;
            transition: transform 0.2s;
          }
          button:hover {
            transform: scale(1.05);
          }
          .auto-retry {
            margin-top: 20px;
            font-size: 0.9em;
            opacity: 0.8;
          }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>⚠️ Serveur de développement non démarré</h1>
          <p>${message}</p>
          <div class="error-code">Erreur: ERR_CONNECTION_REFUSED</div>
          <div class="instructions">
            <h3>📋 Instructions :</h3>
            <ol>
              <li>Ouvrez un terminal dans le dossier <code>Syro/frontend</code></li>
              <li>Exécutez : <code>npm run dev</code></li>
              <li>Attendez que le serveur démarre (vous verrez "Local: http://localhost:5173")</li>
              <li>Cliquez sur "Réessayer" ci-dessous</li>
            </ol>
            <p><strong>Ou utilisez directement :</strong></p>
            <p><code>npm run electron:dev</code></p>
            <p style="font-size: 0.9em; opacity: 0.8;">(Démarre Vite et Electron automatiquement)</p>
          </div>
          ${showRetry ? `
            <button onclick="location.reload()">🔄 Réessayer</button>
            <div class="auto-retry">Tentative automatique dans <span id="countdown">5</span> secondes...</div>
            <script>
              let countdown = 5;
              const interval = setInterval(() => {
                countdown--;
                document.getElementById('countdown').textContent = countdown;
                if (countdown <= 0) {
                  clearInterval(interval);
                  location.reload();
                }
              }, 1000);
            </script>
          ` : ''}
        </div>
      </body>
      </html>
    `;
    mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
  }
  
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Erreur de chargement:', errorCode, errorDescription);
    
    // ERR_CONNECTION_REFUSED (-102) ou ERR_INTERNET_DISCONNECTED (-106)
    if (errorCode === -102 || errorCode === -106) {
      if (retryCount < maxRetries) {
        retryCount++;
        console.log(`Tentative de reconnexion ${retryCount}/${maxRetries}...`);
        
        if (retryCount === 1) {
          // Première erreur : afficher le message d'erreur avec instructions
          showErrorPage(
            'Le serveur de développement Vite n\'est pas démarré sur le port 5173.',
            true
          );
        } else {
          // Tentatives suivantes : message plus court avec auto-retry
          showErrorPage(
            `Tentative de reconnexion ${retryCount}/${maxRetries}...`,
            true
          );
        }
        
        // Réessayer après 3 secondes
        setTimeout(() => {
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.loadURL('http://localhost:5173');
          }
        }, 3000);
      } else {
        // Après maxRetries tentatives, afficher un message final
        showErrorPage(
          `Impossible de se connecter après ${maxRetries} tentatives. Veuillez démarrer le serveur manuellement.`,
          true
        );
      }
    } else {
      // Autre type d'erreur
      showErrorPage(
        `Erreur de chargement: ${errorDescription} (Code: ${errorCode})`,
        true
      );
    }
  });
}

// Cette méthode sera appelée quand Electron aura fini de s'initialiser
app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    // Sur macOS, re-créer une fenêtre quand l'icône du dock est cliquée
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quitter quand toutes les fenêtres sont fermées, sauf sur macOS
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Le handler uncaughtException est déjà défini plus haut avec filtrage des erreurs de cache

