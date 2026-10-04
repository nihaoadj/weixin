---
name: screenshot
description: Capture a user-requested desktop or native-app screenshot. Mini Program acceptance uses internal Developer Tools capture.
---

# Desktop Screenshot

For Mini Program acceptance, follow [WeChat validation](../../../docs/wechat.md): use `simulator_screenshot` and real element interactions. Desktop capture does not prove that flow; do not use old `App.*` WebSocket APIs or focus/mouse/keyboard automation.

For a user-requested desktop/tool-window image, use an application-specific capture tool if available, otherwise the bundled helper. Open existing images directly. Capture only the requested region and exclude credentials, private notifications, complete student answers and hidden case data.

## Windows

Use a known window handle or region when available; `-ActiveWindow` requires the intended app to be focused. Without a window/region option the helper captures the virtual desktop.

```powershell
powershell -ExecutionPolicy Bypass -File <skill-path>/scripts/take_screenshot.ps1 -Mode temp -ActiveWindow
powershell -ExecutionPolicy Bypass -File <skill-path>/scripts/take_screenshot.ps1 -Path "C:\Temp\screen.png"
powershell -ExecutionPolicy Bypass -File <skill-path>/scripts/take_screenshot.ps1 -Mode temp -Region 100,200,800,600
```

## macOS/Linux

```bash
python3 <skill-path>/scripts/take_screenshot.py --mode temp --active-window
```

Use the helper's `--help` for window/region options. On macOS, run `scripts/ensure_macos_permissions.sh` if Screen Recording access is not established.

Honor the user's output path; otherwise use the OS screenshot directory for requested images and the system temporary directory for inspection. Inspect the raw image, then report the target, absolute path and limitations. Do not alter it unless requested.
