#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET=${1:-all}
VER=${2:-0.2.0}
mkdir -p "$ROOT/build" "$ROOT/dist"

build_one() {
    kind="$1"
    case "$kind" in
      linux)
        pkgname="visual-computer-mcp-linux"
        cmd="linux-visual-mcp"
        backend="linux-x11"
        depends="python3, python3-pil, xfce4-screenshooter, libx11-6, libxtst6"
        desc="Minimal stateless visual Computer Use MCP for Linux X11"
        ;;
      windows-wsl)
        pkgname="visual-computer-mcp-windows-wsl"
        cmd="windows-visual-mcp"
        backend="windows-wsl"
        depends="python3"
        desc="Minimal stateless visual Computer Use MCP for Windows through WSL"
        ;;
      *) echo "unknown target: $kind" >&2; exit 2 ;;
    esac
    pkg="$ROOT/build/${pkgname}_${VER}_amd64"
    rm -rf "$pkg"
    mkdir -p "$pkg/DEBIAN" "$pkg/usr/lib/visual-computer-mcp/visual_computer_mcp/backends" "$pkg/usr/bin"
    install -m644 "$ROOT/src/visual_computer_mcp/__init__.py" "$pkg/usr/lib/visual-computer-mcp/visual_computer_mcp/__init__.py"
    install -m755 "$ROOT/src/visual_computer_mcp/server.py" "$pkg/usr/lib/visual-computer-mcp/visual_computer_mcp/server.py"
    install -m644 "$ROOT/src/visual_computer_mcp/backends/__init__.py" "$pkg/usr/lib/visual-computer-mcp/visual_computer_mcp/backends/__init__.py"
    install -m644 "$ROOT/src/visual_computer_mcp/backends/linux_x11.py" "$pkg/usr/lib/visual-computer-mcp/visual_computer_mcp/backends/linux_x11.py"
    install -m644 "$ROOT/src/visual_computer_mcp/backends/windows_wsl.py" "$pkg/usr/lib/visual-computer-mcp/visual_computer_mcp/backends/windows_wsl.py"
    cat > "$pkg/usr/bin/$cmd" <<EOF
#!/bin/sh
export PYTHONPATH=/usr/lib/visual-computer-mcp
export VISUAL_COMPUTER_MCP_BACKEND=$backend
EOF
    if [ "$kind" = linux ]; then
      cat >> "$pkg/usr/bin/$cmd" <<'EOF'
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"
EOF
    fi
    cat >> "$pkg/usr/bin/$cmd" <<'EOF'
exec /usr/bin/python3 -m visual_computer_mcp.server "$@"
EOF
    chmod 755 "$pkg/usr/bin/$cmd"
    cat > "$pkg/DEBIAN/control" <<EOF
Package: $pkgname
Version: $VER
Section: utils
Priority: optional
Architecture: amd64
Depends: $depends
Maintainer: quannfa
Description: $desc
 Provides screenshot, click, mouse, and keyboard tools with a shared MCP protocol layer.
EOF
    dpkg-deb --build --root-owner-group "$pkg" "$ROOT/dist/${pkgname}_${VER}_amd64.deb" >/dev/null
    echo "$ROOT/dist/${pkgname}_${VER}_amd64.deb"
}
case "$TARGET" in
  all) build_one linux; build_one windows-wsl ;;
  linux|windows-wsl) build_one "$TARGET" ;;
  *) echo "usage: $0 [all|linux|windows-wsl] [version]" >&2; exit 2 ;;
esac
