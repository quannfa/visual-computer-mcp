#!/usr/bin/env python3
import base64
import json
import os
import subprocess
import sys
import textwrap

PS = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
PROTOCOL = "2025-06-18"
VERSION = "0.1.2"


def ps(command: str, timeout: int = 30) -> str:
    command = "$ErrorActionPreference=\'Stop\';$ProgressPreference=\'SilentlyContinue\';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);" + command
    encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
    p = subprocess.run(
        [PS, "-NoLogo", "-NoProfile", "-NonInteractive", "-Sta", "-EncodedCommand", encoded],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
    )
    if p.returncode:
        err = p.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(err or f"PowerShell exited {p.returncode}")
    return p.stdout.decode("utf-8-sig", "replace").strip()


def screenshot(args):
    rows = args.get("grid_rows")
    cols = args.get("grid_cols")
    rows = 0 if rows is None else int(rows)
    cols = 0 if cols is None else int(cols)
    if rows < 0 or cols < 0 or rows > 200 or cols > 200:
        raise ValueError("grid_rows/grid_cols must be between 0 and 200")
    script = rf'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WVMDpi {{
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}}
"@
[WVMDpi]::SetProcessDPIAware() | Out-Null
$v = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap($v.Width, $v.Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($v.Left, $v.Top, 0, 0, $bmp.Size, [System.Drawing.CopyPixelOperation]::SourceCopy)
$rows = {rows}
$cols = {cols}
if ($rows -gt 0 -or $cols -gt 0) {{
  $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(210, 255, 40, 40), 1.5)
  $font = New-Object System.Drawing.Font('Consolas', 10, [System.Drawing.FontStyle]::Bold)
  $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(235,255,255,255))
  $bg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(190,0,0,0))
  if ($cols -gt 0) {{
    for ($i=1; $i -lt $cols; $i++) {{
      $x = [single]($i * $v.Width / $cols)
      $g.DrawLine($pen, $x, 0, $x, $v.Height)
    }}
    $stride = [Math]::Max(1, [int][Math]::Ceiling(42.0 * $cols / $v.Width))
    for ($i=0; $i -lt $cols; $i += $stride) {{
      $cx = [single](($i + 0.5) * $v.Width / $cols)
      $s = "C$i"
      $sz = $g.MeasureString($s, $font)
      $rect = New-Object System.Drawing.RectangleF(($cx-$sz.Width/2-2), 2, ($sz.Width+4), ($sz.Height+2))
      $g.FillRectangle($bg, $rect); $g.DrawString($s, $font, $brush, ($cx-$sz.Width/2), 3)
    }}
  }}
  if ($rows -gt 0) {{
    for ($i=1; $i -lt $rows; $i++) {{
      $y = [single]($i * $v.Height / $rows)
      $g.DrawLine($pen, 0, $y, $v.Width, $y)
    }}
    $stride = [Math]::Max(1, [int][Math]::Ceiling(28.0 * $rows / $v.Height))
    for ($i=0; $i -lt $rows; $i += $stride) {{
      $cy = [single](($i + 0.5) * $v.Height / $rows)
      $s = "R$i"
      $sz = $g.MeasureString($s, $font)
      $rect = New-Object System.Drawing.RectangleF(2, ($cy-$sz.Height/2-1), ($sz.Width+4), ($sz.Height+2))
      $g.FillRectangle($bg, $rect); $g.DrawString($s, $font, $brush, 4, ($cy-$sz.Height/2))
    }}
  }}
  $pen.Dispose(); $font.Dispose(); $brush.Dispose(); $bg.Dispose()
}}
$ms = New-Object System.IO.MemoryStream
$bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
$data = [Convert]::ToBase64String($ms.ToArray())
$g.Dispose(); $bmp.Dispose(); $ms.Dispose()
[pscustomobject]@{{left=$v.Left;top=$v.Top;width=$v.Width;height=$v.Height;grid_rows=$rows;grid_cols=$cols;png=$data}} | ConvertTo-Json -Compress
'''
    obj = json.loads(ps(script, timeout=30))
    png = obj.pop("png")
    meta = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return [
        {"type": "text", "text": meta},
        {"type": "image", "data": png, "mimeType": "image/png"},
    ]


def click(args):
    x, y = int(args["x"]), int(args["y"])
    button = args.get("button", "left")
    count = int(args.get("count", 1))
    if button not in ("left", "right", "middle") or count < 1 or count > 3:
        raise ValueError("invalid button/count")
    flags = {"left": (0x0002,0x0004), "right": (0x0008,0x0010), "middle": (0x0020,0x0040)}[button]
    script = rf'''
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class WVM {{
 [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int X,int Y);
 [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint dx,uint dy,uint data,UIntPtr extra);
}}
"@
[WVM]::SetProcessDPIAware() | Out-Null
[WVM]::SetCursorPos({x},{y}) | Out-Null
1..{count} | ForEach-Object {{ [WVM]::mouse_event({flags[0]},0,0,0,[UIntPtr]::Zero); [WVM]::mouse_event({flags[1]},0,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 70 }}
"ok"
'''
    ps(script)
    return [{"type":"text","text":json.dumps({"ok":True,"x":x,"y":y,"button":button,"count":count}, separators=(",",":"))}]


def mouse(args):
    action = args["action"]
    x = args.get("x"); y = args.get("y")
    tx = args.get("to_x"); ty = args.get("to_y")
    delta = int(args.get("delta", 0))
    duration = max(0, min(5000, int(args.get("duration_ms", 300))))
    if action not in ("move", "scroll", "drag"):
        raise ValueError("action must be move, scroll, or drag")
    if action in ("move","drag") and (x is None or y is None):
        raise ValueError("x and y are required")
    if action == "drag" and (tx is None or ty is None):
        raise ValueError("to_x and to_y are required for drag")
    script = r'''
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class WVM { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); [DllImport("user32.dll")] public static extern bool SetCursorPos(int X,int Y); [DllImport("user32.dll")] public static extern int GetSystemMetrics(int n); [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint dx,uint dy,int data,UIntPtr extra); }
"@
[WVM]::SetProcessDPIAware() | Out-Null
'''
    if action == "move":
        script += f"[WVM]::SetCursorPos({int(x)},{int(y)}) | Out-Null\n"
    elif action == "scroll":
        script += f"[WVM]::mouse_event(0x0800,0,0,{delta},[UIntPtr]::Zero)\n"
    else:
        steps = max(1, min(60, duration // 16 if duration else 1))
        sleep = max(0, duration // steps)
        script += "$vx=[WVM]::GetSystemMetrics(76);$vy=[WVM]::GetSystemMetrics(77);$vw=[WVM]::GetSystemMetrics(78);$vh=[WVM]::GetSystemMetrics(79)\n"
        script += "function MoveAbs([int]$px,[int]$py){$ax=[uint32][Math]::Round(($px-$vx)*65535.0/[Math]::Max(1,$vw-1));$ay=[uint32][Math]::Round(($py-$vy)*65535.0/[Math]::Max(1,$vh-1));[WVM]::mouse_event(0xC001,$ax,$ay,0,[UIntPtr]::Zero)}\n"
        script += f"MoveAbs {int(x)} {int(y)}; Start-Sleep -Milliseconds 30; [WVM]::mouse_event(0x0002,0,0,0,[UIntPtr]::Zero)\n"
        script += f"for($i=1;$i -le {steps};$i++){{$nx=[int]({int(x)}+({int(tx)}-{int(x)})*$i/{steps});$ny=[int]({int(y)}+({int(ty)}-{int(y)})*$i/{steps});MoveAbs $nx $ny;Start-Sleep -Milliseconds {sleep}}}\n"
        script += "[WVM]::mouse_event(0x0004,0,0,0,[UIntPtr]::Zero)\n"
    ps(script)
    return [{"type":"text","text":json.dumps({"ok":True,"action":action},separators=(",",":"))}]


def keyboard(args):
    action = args["action"]
    if action == "type":
        text = str(args.get("text", ""))
        payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
        script = rf'''
Add-Type -AssemblyName System.Windows.Forms
$old = [System.Windows.Forms.Clipboard]::GetDataObject()
$text = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{payload}'))
[System.Windows.Forms.Clipboard]::SetText($text)
[System.Windows.Forms.SendKeys]::SendWait('^v')
Start-Sleep -Milliseconds 120
if ($null -ne $old) {{ [System.Windows.Forms.Clipboard]::SetDataObject($old, $true) }}
'''
        ps(script)
    elif action in ("press", "hotkey"):
        keys = args.get("keys")
        if isinstance(keys, str): keys = [keys]
        if not keys: raise ValueError("keys required")
        aliases = {"ctrl":"^","control":"^","alt":"%","shift":"+","enter":"{ENTER}","tab":"{TAB}","esc":"{ESC}","escape":"{ESC}","backspace":"{BACKSPACE}","delete":"{DELETE}","home":"{HOME}","end":"{END}","left":"{LEFT}","right":"{RIGHT}","up":"{UP}","down":"{DOWN}","space":" ","win":"^{ESC}"}
        mods=[]; normals=[]
        for k in keys:
            lk=str(k).lower()
            if lk in ("ctrl","control","alt","shift"): mods.append(aliases[lk])
            else: normals.append(aliases.get(lk, str(k) if len(str(k))==1 else "{"+str(k).upper()+"}"))
        seq="".join(mods)+"".join(normals)
        payload=base64.b64encode(seq.encode()).decode()
        script=rf'''Add-Type -AssemblyName System.Windows.Forms
$s=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{payload}'))
[System.Windows.Forms.SendKeys]::SendWait($s)
'''
        ps(script)
    else:
        raise ValueError("action must be type, press, or hotkey")
    return [{"type":"text","text":json.dumps({"ok":True,"action":action},separators=(",",":"))}]

BACKEND_NAME = 'windows-wsl'
SERVER_NAME = 'windows-visual-mcp'
HANDLERS = {"screenshot": screenshot, "click": click, "mouse": mouse, "keyboard": keyboard}
