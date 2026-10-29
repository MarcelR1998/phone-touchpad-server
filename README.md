# phone-touchpad-server

Use your phone as a wireless trackpad and keyboard for your computer. No app required, just open a URL in your phone's browser.

A small Node server serves a touch-friendly web page on your local network. Touches on the page are sent over a WebSocket to a Python helper that moves the real mouse cursor and types keys on the host machine. Works on macOS, Linux (X11), and Windows.

## Requirements

- Node.js 18 or newer
- Python 3 (no pip packages needed, it uses `ctypes` only)
- Your phone and computer on the same network

Platform notes:

- **macOS**: the first time you run it, grant Accessibility permission to your terminal app when prompted (System Settings → Privacy & Security → Accessibility). Without it, the cursor won't move.
- **Linux**: requires an X11 session with `libX11` and `libXtst` installed (present on most distros). Wayland is not supported.
- **Windows**: works out of the box using the Win32 API.

## Usage

```bash
npm install
npm start
```

The server prints the addresses it is listening on, for example:

```
Phone touchpad server running on port 3000

Open on your phone:
  http://192.168.1.42:3000
```

Open that URL in your phone's browser. The page shows a trackpad area, a scroll strip on the right edge, mouse buttons at the bottom, and a toggle for an on-screen keyboard.

## Controls

| Gesture | Action |
|---|---|
| Drag one finger on the trackpad | Move the cursor |
| Tap | Left click |
| Press and hold, then drag | Click and drag |
| Slide a finger on the right-edge strip | Scroll up / down |
| Left / Middle / Right buttons | Mouse clicks |
| Keyboard toggle (⌨) | Show or hide the on-screen keyboard |

The keyboard has letters, digits, common punctuation, arrow keys, and Shift, Ctrl, Alt, and Super modifiers that can be held while pressing other keys.

Pointer speed and scroll speed can be adjusted by editing `SENSITIVITY` and `SCROLL_SENSITIVITY` near the top of the script in `public/index.html`.

## How it works

- `server.js` serves `public/index.html` with Express and relays touch events over Socket.IO.
- `mouse.py` is spawned by the server and reads one JSON command per line from stdin. It talks to the OS directly through `ctypes` (CoreGraphics on macOS, XTest on Linux, SendInput on Windows), so there are no Python dependencies to install.

## Security

The server listens on all interfaces with no authentication. Anyone on your network who can reach port 3000 can control your mouse and keyboard. Only run it on networks you trust, and stop it when you are done.

## License

ISC
