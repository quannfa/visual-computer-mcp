# visual-computer-mcp

A minimal stateless pure-visual Computer Use MCP with one shared protocol implementation and two platform backends:

- **Linux X11**: controls an existing X11/Xfce desktop with XTest and `xfce4-screenshooter`.
- **Windows via WSL**: runs in WSL and controls the Windows host through Windows PowerShell/.NET/User32.

Both expose the same four MCP tools: `screenshot`, `click`, `mouse`, and `keyboard`.

## Architecture

```text
MCP JSON-RPC + tool schema (shared)
             |
      backend interface
       /            \
 Linux X11       Windows via WSL
 XTest/X11       PowerShell/User32
```

The MCP deliberately contains no OCR, UI tree, target detection, region refinement, or planning. Those belong to the calling agent/Skill.

## Build Debian packages

```bash
./build-deb.sh all 0.2.0
```

Outputs:

```text
dist/visual-computer-mcp-linux_0.2.0_amd64.deb
dist/visual-computer-mcp-windows-wsl_0.2.0_amd64.deb
```

The packages retain the existing executable names for gateway compatibility:

- Linux: `/usr/bin/linux-visual-mcp`
- Windows via WSL: `/usr/bin/windows-visual-mcp`

## Source layout

```text
src/visual_computer_mcp/server.py
src/visual_computer_mcp/backends/linux_x11.py
src/visual_computer_mcp/backends/windows_wsl.py
skill/SKILL.md
tests/smoke.py
```

## License

Licensed under the Apache License, Version 2.0. See `LICENSE` for details.
