---
name: screenshot
description: Capture a requested native-app window, desktop, or pixel region when no application-specific capture path is available. For T24 Mini Program automation, use Developer Tools internal screenshots instead.
---

# Browser-External Screenshot

Capture the smallest faithful image that proves the requested desktop or native-app state. In this repository, use this only when the user explicitly requests a desktop/tool-window image or an application-specific capture path is unavailable.

## Route before capture

1. For T24 Mini Program automation, use the existing Developer Tools internal `App.captureScreenshot` path; do not use operating-system capture, window focus, mouse or keyboard automation.
2. For Mini Program runtime evidence, use Developer Tools internal screenshots and interaction APIs before desktop capture.
3. Use an application-specific capture tool when it can capture the native source faithfully.
4. Open an existing local image directly when another tool already produced it.
5. Use this skill only for the remaining user-requested desktop, native-window, full-screen, or region capture.

Do not treat an operating-system screenshot as interaction, accessibility, API/Demo, or physical-device proof.

## Output location

- Honor a user-specified output path.
- For user-requested screenshots without a path, use the operating system's default screenshot directory.
- For Codex-only inspection, use the system temporary directory.
- Report every saved absolute path. If multiple displays or windows produce multiple files, inspect and report each one.

## Capture with the bundled helper

Use the helper for the current operating system instead of reimplementing capture logic.

### Windows

Ask the user to focus the intended app before `-ActiveWindow`. Use `-WindowHandle` only when a handle is already known.

```powershell
powershell -ExecutionPolicy Bypass -File <skill-path>/scripts/take_screenshot.ps1 -Mode temp -ActiveWindow
powershell -ExecutionPolicy Bypass -File <skill-path>/scripts/take_screenshot.ps1 -Path "C:\Temp\screen.png"
powershell -ExecutionPolicy Bypass -File <skill-path>/scripts/take_screenshot.ps1 -Mode temp -Region 100,200,800,600
```

Without `-ActiveWindow`, `-WindowHandle`, or `-Region`, the helper captures the virtual desktop.

### macOS or Linux

```bash
python3 <skill-path>/scripts/take_screenshot.py --mode temp --active-window
python3 <skill-path>/scripts/take_screenshot.py --path output/screen.png
python3 <skill-path>/scripts/take_screenshot.py --mode temp --region 100,200,800,600
```

On macOS, run `scripts/ensure_macos_permissions.sh` before app/window capture when Screen Recording permission has not been established. App-name, window-name, and window-list discovery are macOS-only; use the helper's `--help` for those conditional options. On Linux, the helper selects an available supported backend and reports when none exists.

## Inspect and report

- For T24, Developer Tools is the primary frontend rendering evidence source. H5 screenshots cannot substitute. A user-requested tool-window screenshot is contextual evidence only; automated acceptance must use internal Developer Tools screenshots plus actual interaction checks. Physical-device verification is deferred.

- View the raw captured file before drawing conclusions. Do not crop, annotate, enhance, or regenerate it unless the user asks.
- Confirm that the intended window/state is visible and that overlays, notifications, or another display did not contaminate the evidence.
- Avoid capturing tokens, credentials, personal notifications, complete student answers, hidden case data, or unrelated windows. If sensitive material is visible, narrow the target before capture rather than editing it out afterward.
- Report target, capture mode, output path, and any limitation. A saved file alone is not proof that the intended UI state is correct.
