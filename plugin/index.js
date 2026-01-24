const WebSocket = require('ws');
const robot = require('robotjs');

class CortexPlugin {
  constructor() {
    this.ws = null;
    this.isLongPress = false;
    this.timer = null;
    this.lastMouseMove = 0;
    this.connectWS();
  }

  connectWS() {
    this.ws = new WebSocket('ws://localhost:8989/cortex');
    this.ws.on('open', () => {
      console.log('WebSocket connected to backend');
    });
    this.ws.on('error', (err) => {
      console.log('WebSocket error:', err.message);
    });
    this.ws.on('close', () => {
      console.log('WebSocket closed, reconnecting...');
      setTimeout(() => this.connectWS(), 1000);
    });
  }

  onKeyDown() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'paste_cycle' }));
    } else {
      // Fallback: simulate native paste (Ctrl+V)
      robot.keyTap('v', 'control');
    }
    this.timer = setTimeout(() => {
      this.isLongPress = true;
    }, 300);
  }

  onKeyUp() {
    clearTimeout(this.timer);
    if (this.isLongPress && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'replace' }));
    }
    this.isLongPress = false;
  }

  onMouseMove() {
    const now = Date.now();
    // Umbral: ignorar movimientos menores a 100ms para evitar temblor
    if (now - this.lastMouseMove < 100) {
      return;
    }
    this.lastMouseMove = now;

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'abort' }));
    }
    clearTimeout(this.timer);
    this.isLongPress = false;
  }
}

module.exports = CortexPlugin;