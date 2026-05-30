const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  startBackend: () => ipcRenderer.send('start-backend'),
  stopBackend: () => ipcRenderer.send('stop-backend'),
  onBackendStatus: (callback) => {
    const listener = (_, data) => callback(data);
    ipcRenderer.on('backend-status', listener);
    return () => ipcRenderer.removeListener('backend-status', listener);
  },
});
