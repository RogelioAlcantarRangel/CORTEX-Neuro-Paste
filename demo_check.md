# Demo Check: Verifying CORTEX "Magic" for Judges

This document provides exact steps for judges to verify the seamless, zero-latency experience of CORTEX Neuro-Paste during the Logitech DevStudio 2026 Hackathon.

## Prerequisites
- Logitech MX device (e.g., MX Master 3S) connected and recognized by Logitech Options+.
- Windows 10/11 system.
- Backend compiled (`dist/backend.exe` exists; if not, run `pyinstaller --onefile --noconsole backend/main.py`).

## Step-by-Step Verification

### 1. Launch Backend Service
- Execute `dist/backend.exe` (runs silently in background).
- Verify in Task Manager: Process "backend.exe" is running.
- Check console output (if visible): "WebSocket server started on ws://localhost:8989/cortex".

### 2. Configure Logitech Plugin
- Open Logitech Options+.
- Copy `plugin/` folder to `C:\Users\[User]\AppData\Local\Logitech\Logitech Options\Plugins\`.
- Restart Logitech Options+.
- Select MX device > Actions > Add Action > Custom Action > Run Plugin > Select "CORTEX Neuro-Paste".
- Assign to a programmable button (e.g., thumb button).
- Ensure WebSocket URL is `ws://localhost:8989/cortex`.

### 3. Test Basic Functionality
- Open a text editor (e.g., Notepad).
- Copy sample text to clipboard: "hello world".
- Press assigned button: Text should paste immediately (<5ms).
- Hold button >300ms: Text should transform to "HELLO WORLD" (uppercase).
- During hold, move mouse: Refinement should abort, no change applied.

### 4. Measure Latency (Critical Metric)
- Run `backend/test_latency.py` in a separate terminal.
- Script simulates WebSocket messages and measures response times.
- Expected output:
  - Paste trigger: <5ms
  - Async processing: <10ms
  - Total loop: <16ms
- Verify logs show "Latency within spec" for all steps.

### 5. Edge Case Verification
- **Abort Safety**: During hold, move mouse – ensure no destructive action occurs.
- **No Backend Crash**: Stop backend.exe, press button – plugin should handle gracefully (no error popups).
- **Clipboard Integrity**: Paste complex text (with special chars), verify no corruption.

### 6. Judge Feedback Points
- **Seamless UX**: No perceived lag; feels like native OS paste.
- **Speculative Execution**: Paste happens before processing completes.
- **Neuro-Ergonomics**: Eliminates wait-state, maintains flow.
- **Portability**: Single .exe, no admin rights needed.

If all steps pass, CORTEX demonstrates true "zero-latency" innovation. Contact team for troubleshooting.