# visual-computer-mcp

A minimal, stateless, pure-visual Computer Use MCP server for controlling a real desktop through screenshots, mouse input, and keyboard input.

The project provides two platform packages from one shared codebase:

- **Linux X11** — controls an existing X11/Xfce desktop using X11/XTest.
- **Windows via WSL** — runs inside WSL and controls the Windows host desktop through PowerShell, .NET, and User32.

Both variants expose the same MCP tools and follow the same interaction model.

## Design

The MCP is intentionally small. It provides only the desktop I/O primitives needed for visual computer use:

```text
             visual-computer-mcp
                     |
          shared MCP protocol layer
                     |
          screenshot / input schema
               /             \
              /               \
       Linux X11          Windows via WSL
       X11/XTest          PowerShell/User32
```

Visual reasoning is deliberately kept outside the server. The MCP does not attempt to understand the interface it is controlling.

A typical interaction is:

```text
screenshot
    ↓
visual reasoning
    ↓
click / mouse / keyboard
    ↓
screenshot again to verify the result
```

This separation keeps the server stateless and avoids coupling desktop control to a particular OCR engine, UI parser, vision model, or planning system.

## Features

- Full-desktop screenshots.
- Optional caller-selected visual grid overlay.
- Absolute-coordinate mouse clicks.
- Mouse movement, scrolling, and drag operations.
- Keyboard text input.
- Key presses and hotkeys.
- Identical MCP tool schema on Linux and Windows.
- Stateless operation: no UI model, target cache, or interaction history is stored by the MCP.
- Standard input/output transport; the server itself does not open a network listener.

## Tools

### `screenshot`

Captures the entire desktop and returns:

1. JSON metadata describing the captured desktop geometry.
2. A PNG image.

Optional arguments:

```json
{
  "grid_rows": 6,
  "grid_cols": 10
}
```

The grid is only a visual reference overlay. It does not perform element detection, region selection, OCR, or coordinate refinement.

Example metadata:

```json
{
  "left": 0,
  "top": 0,
  "width": 1920,
  "height": 1080,
  "grid_rows": 6,
  "grid_cols": 10
}
```

On Windows, the screenshot covers the Windows virtual desktop, including multi-monitor layouts. The reported `left` and `top` values may therefore be non-zero or negative.

### `click`

Moves the pointer to an absolute desktop coordinate and clicks.

```json
{
  "x": 640,
  "y": 420,
  "button": "left",
  "count": 1
}
```

Supported buttons: `left`, `right`, `middle`.

### `mouse`

Supports three actions:

- `move`
- `scroll`
- `drag`

Move example:

```json
{
  "action": "move",
  "x": 800,
  "y": 500
}
```

Scroll example:

```json
{
  "action": "scroll",
  "delta": -360
}
```

Drag example:

```json
{
  "action": "drag",
  "x": 400,
  "y": 300,
  "to_x": 900,
  "to_y": 600,
  "duration_ms": 500
}
```

### `keyboard`

Supports:

- `type` — enter text.
- `press` — press one key or a key sequence.
- `hotkey` — send a key combination.

Text example:

```json
{
  "action": "type",
  "text": "Hello world"
}
```

Hotkey example:

```json
{
  "action": "hotkey",
  "keys": ["ctrl", "l"]
}
```

## Installation

Prebuilt Debian packages are available from the project Releases page.

### Linux X11

Download:

```text
visual-computer-mcp-linux_0.2.0_amd64.deb
```

Install:

```bash
sudo apt install ./visual-computer-mcp-linux_0.2.0_amd64.deb
```

The package installs:

```text
/usr/bin/linux-visual-mcp
```

Required Linux dependencies are declared by the package and installed by `apt` when available from the configured repositories.

The controlled desktop must be an accessible X11 session. By default the launcher uses:

```text
DISPLAY=:0
XAUTHORITY=$HOME/.Xauthority
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/<uid>/bus
```

Existing environment values take precedence.

### Windows via WSL

Download:

```text
visual-computer-mcp-windows-wsl_0.2.0_amd64.deb
```

Install it inside WSL:

```bash
sudo apt install ./visual-computer-mcp-windows-wsl_0.2.0_amd64.deb
```

The package installs:

```text
/usr/bin/windows-visual-mcp
```

Requirements:

- WSL running on Windows.
- Windows interoperability enabled in WSL.
- Windows PowerShell available at the standard Windows path exposed through `/mnt/c`.
- An active Windows desktop session.

The Windows backend controls the Windows host desktop, not a Linux GUI inside WSL.

## Running

Linux:

```bash
linux-visual-mcp
```

Windows via WSL:

```bash
windows-visual-mcp
```

The process is an MCP JSON-RPC server over standard input/output. When started directly in a terminal it waits for protocol messages on stdin.

A minimal protocol check can be performed with:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | linux-visual-mcp
```

Use `windows-visual-mcp` instead for the Windows-via-WSL package.

## Platform implementation

### Linux X11 backend

The Linux backend uses:

- `xfce4-screenshooter` for full-screen capture.
- Pillow for optional grid rendering.
- `libX11` and `libXtst` for pointer and keyboard event injection.

Text is entered as X11 key events. Non-ASCII characters use the standard Linux Unicode input sequence.

### Windows-via-WSL backend

The Windows backend invokes Windows PowerShell from WSL and uses:

- .NET `System.Drawing` / `CopyFromScreen` for screenshots.
- Windows `User32` APIs for pointer input.
- Windows Forms `SendKeys` for key presses and hotkeys.

For arbitrary Unicode text, the backend temporarily writes the text to the Windows clipboard, pastes it into the active application, and then attempts to restore the previous clipboard contents.

## Security

This MCP has direct interactive control over the active desktop session. Any process that can invoke its tools can potentially:

- Capture everything visible on the desktop.
- Move and click the mouse.
- Type into the focused application.
- Trigger keyboard shortcuts.
- Interact with applications using the permissions of the logged-in desktop user.

Treat access to the MCP as equivalent to granting interactive control of the current desktop session.

Important considerations:

- Screenshots may contain passwords, messages, documents, tokens, personal information, or other sensitive data visible on screen.
- Synthetic keyboard and mouse input can trigger destructive or security-sensitive actions.
- On Linux, the process needs access to the target X11 display and its authorization context.
- On Windows, the WSL backend can operate applications in the active Windows desktop session through Windows interoperability.
- Windows Unicode text entry temporarily uses the clipboard. Although the implementation attempts to restore the previous clipboard contents and does not return them as MCP output, sensitive clipboard contents should still be treated cautiously.
- Run the MCP only in environments where the process invoking it is trusted.

The server itself communicates over stdin/stdout and does not bind a TCP or HTTP port.

## Deliberate limitations

This project intentionally does **not** provide:

- OCR.
- Accessibility/UI trees.
- Browser DOM access.
- Application-specific APIs.
- UI element detection.
- Target localization.
- Automatic cropping or region refinement.
- Visual interpretation.
- Planning or retry policies.
- Persistent interaction state.

Those features are outside the scope of this MCP. Its responsibility is limited to reliable visual input and basic desktop input primitives.

## Building from source

Build both Debian packages:

```bash
./build-deb.sh all 0.2.0
```

Build only Linux:

```bash
./build-deb.sh linux 0.2.0
```

Build only Windows via WSL:

```bash
./build-deb.sh windows-wsl 0.2.0
```

Outputs:

```text
dist/visual-computer-mcp-linux_0.2.0_amd64.deb
dist/visual-computer-mcp-windows-wsl_0.2.0_amd64.deb
```

## Source layout

```text
src/visual_computer_mcp/server.py
src/visual_computer_mcp/backends/linux_x11.py
src/visual_computer_mcp/backends/windows_wsl.py
skill/SKILL.md
tests/smoke.py
build-deb.sh
```

The shared server owns the MCP protocol and tool schema. Platform-specific screenshot and input implementations live in the backend modules.

## License

Licensed under the Apache License, Version 2.0. See `LICENSE` for details.
