const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('ultronAPI', {
  // App info
  getVersion: () => ipcRenderer.invoke('get-version'),
  
  // Window controls
  minimize: () => ipcRenderer.invoke('minimize'),
  maximize: () => ipcRenderer.invoke('maximize'),
  close: () => ipcRenderer.invoke('close'),
  
  // Kill switch
  killSwitch: () => ipcRenderer.invoke('kill-switch'),
  
  // System info
  platform: process.platform,
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
  
  // Event listeners
  onKillSwitch: (callback) => {
    ipcRenderer.on('kill-switch-triggered', (_, reason) => callback(reason));
    return () => ipcRenderer.removeAllListeners('kill-switch-triggered');
  },
  
  // System notifications
  showNotification: (title, body) => {
    if (Notification.permission === 'granted') {
      new Notification(title, { body });
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') new Notification(title, { body });
      });
    }
  },
});

contextBridge.exposeInMainWorld('ultronStore', {
  // Local storage helpers with encryption
  get: (key) => {
    try {
      const item = localStorage.getItem(`ultron_${key}`);
      return item ? JSON.parse(item) : null;
    } catch {
      return null;
    }
  },
  
  set: (key, value) => {
    try {
      localStorage.setItem(`ultron_${key}`, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },
  
  remove: (key) => {
    try {
      localStorage.removeItem(`ultron_${key}`);
      return true;
    } catch {
      return false;
    }
  },
  
  clear: () => {
    try {
      Object.keys(localStorage)
        .filter(k => k.startsWith('ultron_'))
        .forEach(k => localStorage.removeItem(k));
      return true;
    } catch {
      return false;
    }
  },
});