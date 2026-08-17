#!/usr/bin/env python3
import argparse
import importlib
import json
import os
import sys

PROTOCOL = "2025-06-18"
VERSION = "0.2.0"

TOOLS = [
    {"name":"screenshot","description":"Capture the full desktop and optionally overlay a caller-selected visual grid. The MCP does not crop, OCR, localize, or interpret UI elements.","inputSchema":{"type":"object","properties":{"grid_rows":{"type":"integer","minimum":0,"maximum":200},"grid_cols":{"type":"integer","minimum":0,"maximum":200}},"additionalProperties":False}},
    {"name":"click","description":"Move the pointer to an absolute desktop coordinate and click.","inputSchema":{"type":"object","properties":{"x":{"type":"integer"},"y":{"type":"integer"},"button":{"type":"string","enum":["left","right","middle"],"default":"left"},"count":{"type":"integer","minimum":1,"maximum":3,"default":1}},"required":["x","y"],"additionalProperties":False}},
    {"name":"mouse","description":"Perform a basic mouse action: move, scroll, or left-button drag using absolute desktop coordinates.","inputSchema":{"type":"object","properties":{"action":{"type":"string","enum":["move","scroll","drag"]},"x":{"type":"integer"},"y":{"type":"integer"},"to_x":{"type":"integer"},"to_y":{"type":"integer"},"delta":{"type":"integer"},"duration_ms":{"type":"integer","minimum":0,"maximum":5000,"default":300}},"required":["action"],"additionalProperties":False}},
    {"name":"keyboard","description":"Send keyboard input to the active desktop application. Supports text entry and key/hotkey events.","inputSchema":{"type":"object","properties":{"action":{"type":"string","enum":["type","press","hotkey"]},"text":{"type":"string"},"keys":{"oneOf":[{"type":"string"},{"type":"array","items":{"type":"string"}}]}},"required":["action"],"additionalProperties":False}},
]

BACKENDS = {
    "linux-x11": "visual_computer_mcp.backends.linux_x11",
    "windows-wsl": "visual_computer_mcp.backends.windows_wsl",
}

def detect_backend():
    forced = os.environ.get("VISUAL_COMPUTER_MCP_BACKEND")
    if forced:
        if forced not in BACKENDS:
            raise RuntimeError(f"unknown backend: {forced}")
        return forced
    if os.environ.get("WSL_DISTRO_NAME") or "microsoft" in os.uname().release.lower():
        ps = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
        if os.path.exists(ps):
            return "windows-wsl"
    if os.environ.get("DISPLAY") or os.path.exists("/tmp/.X11-unix"):
        return "linux-x11"
    raise RuntimeError("cannot auto-detect backend; set VISUAL_COMPUTER_MCP_BACKEND=linux-x11|windows-wsl")

def reply(mid, result=None, error=None):
    obj = {"jsonrpc":"2.0","id":mid}
    if error is not None:
        obj["error"] = error
    else:
        obj["result"] = result
    sys.stdout.write(json.dumps(obj,separators=(",",":"),ensure_ascii=False)+"\n")
    sys.stdout.flush()

def run(backend_name):
    backend = importlib.import_module(BACKENDS[backend_name])
    handlers = backend.HANDLERS
    server_name = backend.SERVER_NAME
    for line in sys.stdin:
        mid = None
        try:
            msg = json.loads(line)
            method = msg.get("method")
            mid = msg.get("id")
            if method == "initialize":
                reply(mid,{"protocolVersion":msg.get("params",{}).get("protocolVersion",PROTOCOL),"capabilities":{"tools":{}},"serverInfo":{"name":server_name,"version":VERSION}})
            elif method == "tools/list":
                reply(mid,{"tools":TOOLS})
            elif method == "tools/call":
                p = msg.get("params",{})
                name = p.get("name")
                args = p.get("arguments") or {}
                if name not in handlers:
                    raise ValueError(f"unknown tool: {name}")
                try:
                    reply(mid,{"content":handlers[name](args),"isError":False})
                except Exception as e:
                    reply(mid,{"content":[{"type":"text","text":str(e)}],"isError":True})
            elif method == "ping":
                reply(mid,{})
            elif mid is not None:
                reply(mid,error={"code":-32601,"message":"Method not found"})
        except Exception as e:
            if mid is not None:
                reply(mid,error={"code":-32603,"message":str(e)})

def main():
    ap = argparse.ArgumentParser(description="Minimal stateless visual Computer Use MCP")
    ap.add_argument("--backend", choices=sorted(BACKENDS))
    ap.add_argument("--version", action="store_true")
    ns = ap.parse_args()
    if ns.version:
        print(VERSION)
        return
    run(ns.backend or detect_backend())

if __name__ == "__main__":
    main()
