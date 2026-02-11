const WebSocket = require('ws');
const robot = require('robotjs');

class CortexPlugin {
  constructor() {
    this.ws = null;
    this.isLongPress = false;
    this.timer = null;
    this.lastMouseMove = 0;
    this.currentCycleId = null;
    this.connectWS();
  }

  connectWS() {
    this.ws = new WebSocket('ws://localhost:8989/cortex');

    this.ws.on('open', () => {
      console.log('WebSocket connected to backend');
    });

    this.ws.on('message', (raw) => {
      this.handleBackendEvent(raw);
    });

    this.ws.on('error', (err) => {
      console.log('WebSocket error:', err.message);
    });

    this.ws.on('close', () => {
      console.log('WebSocket closed, reconnecting...');
      setTimeout(() => this.connectWS(), 1000);
    });
  }

  handleBackendEvent(raw) {
    let message;
    try {
      message = JSON.parse(raw);
    } catch (err) {
      console.log('Invalid backend event:', raw.toString());
      return;
    }

    const { type, action, phase, code, cycle_id: cycleId } = message;

    if (cycleId !== undefined && cycleId !== null) {
      this.currentCycleId = cycleId;
    }

    if (type === 'ack') {
      console.log(`[ACK] action=${action} cycle_id=${cycleId}`);
      return;
    }

    if (type === 'status') {
      console.log(`[STATUS] phase=${phase} cycle_id=${cycleId}`);
      return;
    }

    if (type === 'error') {
      console.log(`[ERROR] code=${code} action=${action} cycle_id=${cycleId}`);
      return;
    }

    console.log('Unknown backend event:', message);
  }

  onKeyDown() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'paste_cycle', cycle_id: this.currentCycleId }));
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
      this.ws.send(JSON.stringify({ action: 'replace', cycle_id: this.currentCycleId }));
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
      this.ws.send(JSON.stringify({ action: 'abort', cycle_id: this.currentCycleId }));
    }
    clearTimeout(this.timer);
    this.isLongPress = false;
  }
}

module.exports = CortexPlugin;
