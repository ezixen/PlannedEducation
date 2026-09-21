const { app, BrowserWindow, globalShortcut } = require('electron');
const path = require('path');

const isDev = process.env.NODE_ENV === 'development';

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    fullscreen: true,
    kiosk: true, // This is crucial for the exam mode
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Prevent leaving fullscreen
  mainWindow.on('leave-full-screen', () => {
    mainWindow.setFullScreen(true);
  });

  // Example: Block specific shortcuts (Alt+Tab cannot be blocked by globalShortcut easily, but we can block others)
  globalShortcut.register('CommandOrControl+Q', () => {
    console.log('User tried to quit.');
  });
  
  globalShortcut.register('CommandOrControl+W', () => {
    console.log('User tried to close window.');
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});
