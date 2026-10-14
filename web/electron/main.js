const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, nativeImage, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow = null;
let tray = null;
let apiProcess = null;
let nextProcess = null;

const isDev = process.env.NODE_ENV === 'development';
const PORT = 3000;
const API_PORT = 8000;

function createTray() {
  const iconPath = path.join(__dirname, '../public/icon.png');
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
  
  tray = new Tray(icon);
  
  const contextMenu = Menu.buildFromTemplate([
    { label: 'ULTRON Aç', click: () => mainWindow?.show() },
    { label: 'Kill Switch', click: () => mainWindow?.webContents.send('kill-switch'), accelerator: 'Ctrl+Alt+Shift+K' },
    { type: 'separator' },
    { label: 'Çıkış', click: () => app.quit() }
  ]);
  
  tray.setToolTip('ULTRON AI Agent');
  tray.setContextMenu(contextMenu);
  
  tray.on('double-click', () => mainWindow?.show());
}

function startAPI() {
  const apiPath = path.join(__dirname, '..', '..', 'app', 'api', 'server.py');
  apiProcess = spawn('python', ['-m', 'uvicorn', 'app.api.server:app', '--host', '0.0.0.0', '--port', '8000'], {
    cwd: path.join(__dirname, '..', '..'),
    env: { ...process.env, PYTHONPATH: path.join(__dirname, '..', '..') },
    stdio: ['ignore', 'pipe', 'pipe']
  });
  
  apiProcess.stdout?.on('data', (data) => {
    console.log(`[API] ${data.toString().trim()}`);
  });
  apiProcess.stderr?.on('data', (data) => {
    console.error(`[API ERR] ${data.toString().trim()}`);
  });
}

function startNext() {
  if (isDev) {
    nextProcess = spawn('npm', ['run', 'dev'], {
      cwd: path.join(__dirname, '..'),
      stdio: 'pipe',
      shell: true
    });
    
    nextProcess.stdout?.on('data', (data) => {
      console.log(`[NEXT] ${data.toString().trim()}`);
    });
    nextProcess.stderr?.on('data', (data) => {
      console.error(`[NEXT ERR] ${data.toString().trim()}`);
    });
    
    // Wait for Next.js to compile
    setTimeout(() => createWindow(), 8000);
  } else {
    // Production: serve built files
    createWindow();
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
    icon: path.join(__dirname, '../public/icon.png'),
    title: 'ULTRON',
    show: false,
  });
  
  const url = isDev ? `http://localhost:${PORT}` : `file://${path.join(__dirname, '../out/index.html')}`;
  mainWindow.loadURL(url);
  
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });
  
  mainWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });
  
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
  
  // Dev tools in development
  if (isDev) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

// Global shortcuts
function registerShortcuts() {
  globalShortcut.register('CommandOrControl+Alt+Shift+K', () => {
    mainWindow?.webContents.send('kill-switch');
  });
}

// IPC handlers
ipcMain.handle('kill-switch', () => {
  console.log('[IPC] Kill switch activated');
  return { success: true };
});

ipcMain.handle('get-version', () => {
  return app.getVersion();
});

ipcMain.handle('minimize', () => {
  mainWindow?.minimize();
});

ipcMain.handle('maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});

ipcMain.handle('close', () => {
  mainWindow?.hide();
});

// App lifecycle
app.whenReady().then(() => {
  startAPI();
  startNext();
  createTray();
  registerShortcuts();
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
  
  if (apiProcess) {
    apiProcess.kill();
  }
  if (nextProcess) {
    nextProcess.kill();
  }
  
  globalShortcut.unregisterAll();
});

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
});