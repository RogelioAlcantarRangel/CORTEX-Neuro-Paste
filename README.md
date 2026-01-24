![alt text](https://img.shields.io/badge/Status-Prototype-green)
![alt text](https://img.shields.io/badge/Stack-Node.js_|_Python_FastAPI-blue)
![alt text](https://img.shields.io/badge/Latency-%3C16ms-red)

⚡ The Problem: The "AI Wait"

In the current era of AI tools, productivity has a new friction: Latency.
When a developer or creator wants to use AI (e.g., to refactor code or clean text), they have to:

Copy text.

Open a separate tool/window.

Paste & Wait.

Copy result.

Paste back.

Even integrated plugins suffer from "Request Latency": you press a button, and nothing happens for 500ms while the API responds. This breaks the flow state.

🧠 The Solution: CORTEX Neuro-Paste

CORTEX is a hybrid architecture (Logi Plugin + Local Python Core) designed to eliminate cognitive load by adhering to a strict rule: The Downstroke Law.

We don't ask the user to wait for the AI. We assume the user's intention and execute immediately, refining the result in the background.

Key Features

0ms Instant Paste: Pressing the button triggers a native OS paste immediately on the keyDown event. No lag.

Speculative Refinement: If the button is held (>300ms), Cortex processes the clipboard content locally (cleaning JSON, formatting code, fixing grammar) and morphs the pasted text in real-time.

Motion Safety: If the user moves the mouse during the "hold" phase, Cortex detects a context switch and cancels the refinement to prevent data loss.

Privacy-First: All processing happens on localhost via a dedicated Python backend. No data leaves the machine.

📐 Engineering Philosophy: The 16ms Imperative

Most plugins feel "digital" because they wait for confirmation (API response, keyUp events). CORTEX feels "analog" because it acts on contact.

We implemented a proprietary Downstroke-First Architecture:

Speculative Execution: 100% of primary actions trigger on electrical contact (onKeyDown). We never force the user's brain to wait for a timer.

Additive Intelligence: AI enhances the output after the output exists, never delaying it. The user sees the raw result instantly; the "smart" result follows seamlessly.

Proprioceptive Contract: Visual feedback happens within the first 16ms (1 frame), ensuring the Logitech hardware feels like a physical instrument, not a remote control.

🛠️ Technical Architecture

CORTEX bypasses the limitations of standard web-based plugins by establishing a high-speed WebSocket tunnel to a native OS backend.

code
Mermaid
download
content_copy
expand_less
graph LR
    A[Logitech Hardware] -- onKeyDown --> B(Node.js Plugin)
    B -- WebSocket (<2ms) --> C{CORTEX Core}
    C -- Win32 API --> D[OS Clipboard]
    C -- Local LLM/Script --> D
The Stack

Frontend (Logi Plugin): Node.js / TypeScript. Handles raw input events and haptic feedback triggers.

Communication: Persistent WebSockets (Zero-Handshake delay).

Backend (The Brain): Python 3.10 + FastAPI + Uvicorn.

pyperclip / win32 for low-level OS clipboard manipulation.

pynput for sub-millisecond keystroke injection.

Compiled to a standalone .exe for seamless deployment.

🚀 Installation & Usage
Prerequisites

Logitech Options+ installed.

A Logitech MX device (Keyboard or Mouse).

Setup

Download the latest release.

Double-click install_cortex.bat (This installs the plugin profile and starts the silent background service).

Open Logitech Options+ and map any button to the "CORTEX Paste" Smart Action.

How to use

Click: Works exactly like Ctrl+V (Instant).

Click & Hold: Watch your messy text automatically format itself into clean code/prose before your eyes.

🔮 Future Roadmap

Context Awareness: Using the active window handle (IDE vs Browser) to decide how to format the text (e.g., Python indentation vs Email tone).

MX Ink Integration: applying the "Downstroke Law" to spatial drawing (Instant Ink).

Local LLM Support: Swapping regex-based cleaning for a local Llama-3 model for complex text refactoring with zero latency.

Built for the Logitech DevStudio 2026 Hackathon.
An experiment in neuro-ergonomics.
