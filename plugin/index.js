const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');
const robot = require('robotjs');

const DEFAULT_CONFIG = {
  ws_url: 'ws://localhost:8989/cortex',
  reconnect_ms: 1000,
  hold_threshold_ms: 300,
  mouse_abort_debounce_ms: 100,
  client_token: 'dev-token',
};

function loadPluginConfig() {
  const configPath = path.join(__dirname, 'config.json');
  try {
    const raw = fs.readFileSync(configPath, 'utf8');
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') {
      return { ...DEFAULT_CONFIG };
    }

    const config = { ...DEFAULT_CONFIG };

    if (typeof parsed.ws_url === 'string' && parsed.ws_url.trim()) {
      config.ws_url = parsed.ws_url.trim();
    }

    const reconnectMs = Number(parsed.reconnect_ms);
    if (Number.isInteger(reconnectMs) && reconnectMs > 0) {
      config.reconnect_ms = reconnectMs;
    }

    const holdThresholdMs = Number(parsed.hold_threshold_ms);
    if (Number.isInteger(holdThresholdMs) && holdThresholdMs > 0) {
      config.hold_threshold_ms = holdThresholdMs;
    }

    const abortDebounceMs = Number(parsed.mouse_abort_debounce_ms);
    if (Number.isInteger(abortDebounceMs) && abortDebounceMs >= 0) {
      config.mouse_abort_debounce_ms = abortDebounceMs;
    }

    if (typeof parsed.client_token === 'string' && parsed.client_token.trim()) {
      config.client_token = parsed.client_token.trim();
    }

    return config;
  } catch (err) {
    return { ...DEFAULT_CONFIG };
  }
}

class CortexPlugin {
  constructor() {
    this.ws = null;
    this.isLongPress = false;
    this.timer = null;
    this.lastMouseMove = 0;
    this.currentCycleId = null;
    this.isAuthenticated = false;
    this.authFailed = false;
    this.config = loadPluginConfig();
    this.connectWS();
  }

  connectWS() {
    this.ws = new WebSocket(this.config.ws_url);

    this.ws.on('open', () => {
      console.log('WebSocket connected to backend');
      this.isAuthenticated = false;
      this.authFailed = false;
      this.ws.send(JSON.stringify({ action: 'hello', client_token: this.config.client_token }));
    });

    this.ws.on('message', (raw) => {
      this.handleBackendEvent(raw);
    });

    this.ws.on('error', (err) => {
      console.log('WebSocket error:', err.message);
    });

    this.ws.on('close', () => {
      console.log('WebSocket closed, reconnecting...');
      this.isAuthenticated = false;
      setTimeout(() => this.connectWS(), this.config.reconnect_ms);
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

    const {
      type, action, phase, code, cycle_id: cycleId,
    } = message;

    if (cycleId !== undefined && cycleId !== null) {
      this.currentCycleId = cycleId;
    }

    if (type === 'ack') {
      console.log(`[ACK] action=${action} cycle_id=${cycleId}`);
      if (action === 'hello') {
        this.isAuthenticated = true;
        this.authFailed = false;
      }
      return;
    }

    if (type === 'status') {
      console.log(`[STATUS] phase=${phase} cycle_id=${cycleId}`);
      return;
    }

    if (type === 'error') {
      console.log(`[ERROR] code=${code} action=${action} cycle_id=${cycleId}`);
      if (['UNAUTHORIZED', 'INVALID_TOKEN', 'EXPIRED_TOKEN'].includes(code)) {
        this.isAuthenticated = false;
        this.authFailed = true;
        console.log('[AUTH] Authentication failed. Check plugin/config.json token.');
      }
      return;
    }

    console.log('Unknown backend event:', message);
  }

  onKeyDown() {
    if (this.authFailed) {
      console.log('[AUTH] Skipping paste_cycle due to previous auth failure.');
      robot.keyTap('v', 'control');
      return;
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN && this.isAuthenticated) {
      this.currentCycleId = null;
      this.ws.send(JSON.stringify({ action: 'paste_cycle' }));
    } else {
      // Fallback: simulate native paste (Ctrl+V)
      robot.keyTap('v', 'control');
    }

    this.timer = setTimeout(() => {
      this.isLongPress = true;
    }, this.config.hold_threshold_ms);
  }

  onKeyUp() {
    clearTimeout(this.timer);
    if (this.isLongPress && this.ws && this.ws.readyState === WebSocket.OPEN && this.isAuthenticated) {
      const payload = { action: 'replace' };
      if (Number.isInteger(this.currentCycleId)) {
        payload.cycle_id = this.currentCycleId;
      }
      this.ws.send(JSON.stringify(payload));
    }
    this.isLongPress = false;
  }

  onMouseMove() {
    const now = Date.now();
    if (now - this.lastMouseMove < this.config.mouse_abort_debounce_ms) {
      return;
    }
    this.lastMouseMove = now;

    if (this.authFailed) {
      return;
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN && this.isAuthenticated) {
      const payload = { action: 'abort' };
      if (Number.isInteger(this.currentCycleId)) {
        payload.cycle_id = this.currentCycleId;
      }
      this.ws.send(JSON.stringify(payload));
    }
    clearTimeout(this.timer);
    this.isLongPress = false;
  }
}

module.exports = CortexPlugin;
