const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');
const robot = require('robotjs');

const DEFAULT_CONFIG = {
  ws_url: 'ws://localhost:8989/cortex',
  reconnect_ms: 1000,
  hold_threshold_ms: 300,
  mouse_abort_debounce_ms: 100,
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

    if (Number.isInteger(parsed.reconnect_ms) && parsed.reconnect_ms > 0) {
      config.reconnect_ms = parsed.reconnect_ms;
    }

    if (Number.isInteger(parsed.hold_threshold_ms) && parsed.hold_threshold_ms > 0) {
      config.hold_threshold_ms = parsed.hold_threshold_ms;
    }

    if (Number.isInteger(parsed.mouse_abort_debounce_ms) && parsed.mouse_abort_debounce_ms >= 0) {
      config.mouse_abort_debounce_ms = parsed.mouse_abort_debounce_ms;
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
    this.config = loadPluginConfig();
    this.connectWS();
  }

  connectWS() {
    this.ws = new WebSocket(this.config.ws_url);

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
    }, this.config.hold_threshold_ms);
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
    if (now - this.lastMouseMove < this.config.mouse_abort_debounce_ms) {
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
