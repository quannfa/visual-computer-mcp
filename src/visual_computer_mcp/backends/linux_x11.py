#!/usr/bin/env python3
import base64
import ctypes
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault("DISPLAY", ":0")
os.environ.setdefault("XAUTHORITY", str(Path.home() / ".Xauthority"))
os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{os.getuid()}/bus")

PROTOCOL = "2025-06-18"
VERSION = "0.1.3"

# X11/XTest are already part of a normal Xfce/Xorg desktop.
X11 = ctypes.CDLL("libX11.so.6")
XTST = ctypes.CDLL("libXtst.so.6")
X11.XOpenDisplay.argtypes = [ctypes.c_char_p]
X11.XOpenDisplay.restype = ctypes.c_void_p
X11.XCloseDisplay.argtypes = [ctypes.c_void_p]
X11.XFlush.argtypes = [ctypes.c_void_p]
X11.XStringToKeysym.argtypes = [ctypes.c_char_p]
X11.XStringToKeysym.restype = ctypes.c_ulong
X11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
X11.XKeysymToKeycode.restype = ctypes.c_uint
XTST.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
XTST.XTestFakeMotionEvent.restype = ctypes.c_int
XTST.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
XTST.XTestFakeButtonEvent.restype = ctypes.c_int
XTST.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
XTST.XTestFakeKeyEvent.restype = ctypes.c_int

KEY_ALIASES = {
    "ctrl": "Control_L", "control": "Control_L", "alt": "Alt_L", "shift": "Shift_L",
    "win": "Super_L", "super": "Super_L", "meta": "Super_L",
    "enter": "Return", "return": "Return", "tab": "Tab", "esc": "Escape", "escape": "Escape",
    "backspace": "BackSpace", "delete": "Delete", "home": "Home", "end": "End",
    "left": "Left", "right": "Right", "up": "Up", "down": "Down", "space": "space",
    "pageup": "Page_Up", "pagedown": "Page_Down", "insert": "Insert",
}


def _display():
    d = X11.XOpenDisplay(None)
    if not d:
        raise RuntimeError(f"cannot open X display {os.environ.get('DISPLAY')}")
    return d


def _keysym_name(key: str) -> str:
    k = str(key)
    lk = k.lower()
    if lk in KEY_ALIASES:
        return KEY_ALIASES[lk]
    if len(k) == 1:
        return k
    if lk.startswith("f") and lk[1:].isdigit():
        return lk.upper()
    return k


def _keycode(d, key: str) -> int:
    name = _keysym_name(key)
    sym = X11.XStringToKeysym(name.encode())
    if not sym:
        raise ValueError(f"unsupported key: {key}")
    code = int(X11.XKeysymToKeycode(d, sym))
    if not code:
        raise ValueError(f"no keycode for: {key}")
    return code


def _font(size=16):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def screenshot(args):
    rows = int(args.get("grid_rows") or 0)
    cols = int(args.get("grid_cols") or 0)
    if not 0 <= rows <= 200 or not 0 <= cols <= 200:
        raise ValueError("grid_rows/grid_cols must be between 0 and 200")
    with tempfile.TemporaryDirectory(prefix="linux-visual-") as td:
        path = os.path.join(td, "screen.png")
        p = subprocess.run(
            ["/usr/bin/xfce4-screenshooter", "-f", "-s", path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
            env=os.environ.copy(),
        )
        if p.returncode != 0 or not os.path.exists(path):
            raise RuntimeError(p.stderr.decode("utf-8", "replace").strip() or "screenshot failed")
        im = Image.open(path).convert("RGB")
        w, h = im.size
        if rows or cols:
            draw = ImageDraw.Draw(im, "RGBA")
            font = _font(15)
            line = (255, 35, 35, 220)
            fg = (255, 255, 255, 255)
            bg = (0, 0, 0, 190)
            if cols:
                for i in range(1, cols):
                    x = round(i * w / cols)
                    draw.line((x, 0, x, h), fill=line, width=2)
                cellw = w / cols
                stride = max(1, math.ceil(52 / max(1, cellw)))
                for i in range(0, cols, stride):
                    s = f"C{i}"
                    box = draw.textbbox((0, 0), s, font=font)
                    tw, th = box[2]-box[0], box[3]-box[1]
                    cx = (i + 0.5) * cellw
                    x0 = int(cx - tw/2 - 3)
                    draw.rectangle((x0, 2, x0+tw+6, th+8), fill=bg)
                    draw.text((x0+3, 4), s, font=font, fill=fg)
            if rows:
                for i in range(1, rows):
                    y = round(i * h / rows)
                    draw.line((0, y, w, y), fill=line, width=2)
                cellh = h / rows
                stride = max(1, math.ceil(34 / max(1, cellh)))
                for i in range(0, rows, stride):
                    s = f"R{i}"
                    box = draw.textbbox((0, 0), s, font=font)
                    tw, th = box[2]-box[0], box[3]-box[1]
                    cy = (i + 0.5) * cellh
                    y0 = int(cy - th/2 - 3)
                    draw.rectangle((2, y0, tw+8, y0+th+6), fill=bg)
                    draw.text((5, y0+2), s, font=font, fill=fg)
        out = io.BytesIO()
        im.save(out, format="PNG", optimize=True)
        png = base64.b64encode(out.getvalue()).decode("ascii")
    meta = json.dumps({"left":0,"top":0,"width":w,"height":h,"grid_rows":rows,"grid_cols":cols}, separators=(",", ":"))
    return [{"type":"text","text":meta},{"type":"image","data":png,"mimeType":"image/png"}]


def click(args):
    x, y = int(args["x"]), int(args["y"])
    button = args.get("button", "left")
    count = int(args.get("count", 1))
    bmap = {"left":1,"middle":2,"right":3}
    if button not in bmap or not 1 <= count <= 3:
        raise ValueError("invalid button/count")
    d = _display()
    try:
        XTST.XTestFakeMotionEvent(d, 0, x, y, 0); X11.XFlush(d); time.sleep(0.03)
        for _ in range(count):
            XTST.XTestFakeButtonEvent(d, bmap[button], 1, 0)
            XTST.XTestFakeButtonEvent(d, bmap[button], 0, 0)
            X11.XFlush(d); time.sleep(0.08)
    finally:
        X11.XCloseDisplay(d)
    return [{"type":"text","text":json.dumps({"ok":True,"x":x,"y":y,"button":button,"count":count},separators=(",",":"))}]


def mouse(args):
    action = args["action"]
    if action not in ("move","scroll","drag"):
        raise ValueError("action must be move, scroll, or drag")
    d = _display()
    try:
        if action == "move":
            x, y = int(args["x"]), int(args["y"])
            XTST.XTestFakeMotionEvent(d, 0, x, y, 0); X11.XFlush(d)
        elif action == "scroll":
            delta = int(args.get("delta", 0))
            if delta == 0:
                return [{"type":"text","text":"{\"ok\":true,\"action\":\"scroll\"}"}]
            button = 4 if delta > 0 else 5
            steps = max(1, min(50, int(math.ceil(abs(delta) / 120))))
            for _ in range(steps):
                XTST.XTestFakeButtonEvent(d, button, 1, 0); XTST.XTestFakeButtonEvent(d, button, 0, 0)
                X11.XFlush(d); time.sleep(0.03)
        else:
            x, y = int(args["x"]), int(args["y"])
            tx, ty = int(args["to_x"]), int(args["to_y"])
            duration = max(0, min(5000, int(args.get("duration_ms", 300))))
            steps = max(2, min(120, duration // 12 if duration else 2))
            XTST.XTestFakeMotionEvent(d, 0, x, y, 0); X11.XFlush(d); time.sleep(0.03)
            XTST.XTestFakeButtonEvent(d, 1, 1, 0); X11.XFlush(d)
            delay = duration / steps / 1000 if duration else 0
            for i in range(1, steps+1):
                nx = round(x + (tx-x)*i/steps); ny = round(y + (ty-y)*i/steps)
                XTST.XTestFakeMotionEvent(d, 0, nx, ny, 0); X11.XFlush(d)
                if delay: time.sleep(delay)
            XTST.XTestFakeButtonEvent(d, 1, 0, 0); X11.XFlush(d)
    finally:
        X11.XCloseDisplay(d)
    return [{"type":"text","text":json.dumps({"ok":True,"action":action},separators=(",",":"))}]


def _send_keys(keys):
    if isinstance(keys, str): keys = [keys]
    if not keys: raise ValueError("keys required")
    d = _display()
    try:
        codes = [_keycode(d, k) for k in keys]
        for c in codes:
            XTST.XTestFakeKeyEvent(d, c, 1, 0); X11.XFlush(d); time.sleep(0.02)
        for c in reversed(codes):
            XTST.XTestFakeKeyEvent(d, c, 0, 0); X11.XFlush(d); time.sleep(0.02)
    finally:
        X11.XCloseDisplay(d)


ASCII_KEYS = {
    " ": ("space", False), "-": ("minus", False), "_": ("minus", True),
    "=": ("equal", False), "+": ("equal", True), "[": ("bracketleft", False),
    "{": ("bracketleft", True), "]": ("bracketright", False), "}": ("bracketright", True),
    "\\": ("backslash", False), "|": ("backslash", True), ";": ("semicolon", False),
    ":": ("semicolon", True), "'": ("apostrophe", False), '"': ("apostrophe", True),
    ",": ("comma", False), "<": ("comma", True), ".": ("period", False),
    ">": ("period", True), "/": ("slash", False), "?": ("slash", True),
    "`": ("grave", False), "~": ("grave", True), "!": ("1", True), "@": ("2", True),
    "#": ("3", True), "$": ("4", True), "%": ("5", True), "^": ("6", True),
    "&": ("7", True), "*": ("8", True), "(": ("9", True), ")": ("0", True),
    "\n": ("Return", False), "\t": ("Tab", False),
}


def _tap(d, name: str, shift=False):
    code = _keycode(d, name)
    shift_code = _keycode(d, "shift") if shift else None
    if shift_code:
        XTST.XTestFakeKeyEvent(d, shift_code, 1, 0)
    XTST.XTestFakeKeyEvent(d, code, 1, 0); XTST.XTestFakeKeyEvent(d, code, 0, 0)
    if shift_code:
        XTST.XTestFakeKeyEvent(d, shift_code, 0, 0)
    X11.XFlush(d); time.sleep(0.012)


def _type_ascii_char(d, ch: str):
    if 'a' <= ch <= 'z' or '0' <= ch <= '9':
        _tap(d, ch, False)
    elif 'A' <= ch <= 'Z':
        _tap(d, ch.lower(), True)
    elif ch in ASCII_KEYS:
        name, shift = ASCII_KEYS[ch]; _tap(d, name, shift)
    else:
        raise ValueError(f"unsupported ASCII character: {ch!r}")


def _type_unicode_char(d, ch: str):
    # Standard Linux/GTK Unicode entry: Ctrl+Shift+U, hexadecimal code point, Enter.
    ctrl = _keycode(d, "ctrl"); shift = _keycode(d, "shift"); u = _keycode(d, "u")
    XTST.XTestFakeKeyEvent(d, ctrl, 1, 0); XTST.XTestFakeKeyEvent(d, shift, 1, 0)
    XTST.XTestFakeKeyEvent(d, u, 1, 0); XTST.XTestFakeKeyEvent(d, u, 0, 0)
    XTST.XTestFakeKeyEvent(d, shift, 0, 0); XTST.XTestFakeKeyEvent(d, ctrl, 0, 0)
    X11.XFlush(d); time.sleep(0.025)
    for h in f"{ord(ch):x}":
        _type_ascii_char(d, h)
    _tap(d, "Return", False)


def _type_text(text: str):
    d = _display()
    try:
        for ch in text:
            if ord(ch) < 128:
                _type_ascii_char(d, ch)
            else:
                _type_unicode_char(d, ch)
    finally:
        X11.XCloseDisplay(d)

def keyboard(args):
    action = args["action"]
    if action == "type":
        _type_text(str(args.get("text", "")))
    elif action in ("press", "hotkey"):
        _send_keys(args.get("keys"))
    else:
        raise ValueError("action must be type, press, or hotkey")
    return [{"type":"text","text":json.dumps({"ok":True,"action":action},separators=(",",":"))}]

BACKEND_NAME = 'linux-x11'
SERVER_NAME = 'linux-visual-mcp'
HANDLERS = {"screenshot": screenshot, "click": click, "mouse": mouse, "keyboard": keyboard}
