# Visual Computer Use

Use the platform-specific visual MCP server as a stateless full-screen visual I/O device.

- Start with `screenshot` to inspect the current desktop.
- Never invent a precise click coordinate when the target is visually uncertain.
- Call `screenshot` again with caller-selected `grid_rows` and `grid_cols` when positional reference helps.
- The screenshot is always full-screen. The MCP does not crop, OCR, identify UI elements, or expose a UI tree.
- Use `click`, `mouse`, and `keyboard` only after the target is visually clear enough.
- After consequential GUI actions, call `screenshot` again and verify the visible result.

Localization, planning, grid-density selection, iterative visual reasoning, and post-action verification belong to the calling agent/Skill, not the MCP.
