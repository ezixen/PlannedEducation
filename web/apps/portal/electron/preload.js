const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Expose specific IPC commands here as needed
  onExamModeTrigger: (callback) => ipcRenderer.on('trigger-exam-mode', callback)
});
