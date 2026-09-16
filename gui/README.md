# OpenCraftFormation GUI

A desktop app (macOS/Windows/Linux) that wraps the CLI's `overlay/` +
`template.yaml` workflow: a form for server settings, drag-and-drop for
mods, and a one-click export that bundles everything into a zip plus the
exact steps to run in AWS CloudShell. It reads and writes the same
`../params.yaml` and `../overlay/` the CLI uses, so you can mix and match
— configure here, deploy with `../deploy.sh`, or the reverse.

**The GUI never talks to your AWS account.** It has no AWS credentials
requirement and no `boto3` dependency — it only prepares files on disk.
Deploying happens where you run `deploy.sh` yourself (locally or, more
commonly, in AWS CloudShell after uploading the zip this app builds).

Built with [pywebview](https://pywebview.flowrl.com/) (a native OS webview,
no bundled Chromium) for the shell and plain HTML/CSS/JS for the UI.

## Running from source

```sh
cd gui
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### macOS: pyobjc build errors

`pywebview` depends on `pyobjc-core` for its Cocoa backend. On some
macOS/Xcode combinations, pip tries to compile it from source and fails
with `clang` errors. If that happens, force prebuilt wheels instead:

```sh
pip install --only-binary=:all: pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit
pip install -r requirements.txt
```

## What it does (and doesn't) do

- **Screen 1 — Configure**: server settings, instance type (with a rough
  cost-per-hour hint from a static table), root volume size, Java heap
  (auto-suggested from the instance's RAM, editable), SSH CIDR (with an
  "autofill my IP" button), Elastic IP toggle, and plain text fields for
  AWS profile/region/key pair/VPC/subnet — these are written into
  `params.yaml` as-is, not validated against a real AWS account, since the
  GUI doesn't connect to one. Every value is saved to
  `~/.opencraftformation/config.json` as you go and mirrored into
  `../params.yaml`.
- **Screen 2 — Mods & Files**: drag-and-drop (or "Browse…", or "Open mods
  folder" to place files yourself) for `.jar` mods/plugins into
  `../overlay/mods/` or `../overlay/plugins/` depending on server type,
  plus a world folder shortcut and file pickers for `whitelist.json`,
  `ops.json`, and `server-icon.png`.
- **Screen 3 — Review & Export**: a read-only summary, the cost estimate,
  and a "Build zip for CloudShell" button. It zips `template.yaml`,
  `deploy.sh`, `destroy.sh`, `params.yaml`, and `overlay/` into
  `build/craftainer-cloudshell.zip`, then shows the exact steps to upload
  it to AWS CloudShell, unzip it, and run `./deploy.sh` there.

Not in this build (see the top-level spec's non-goals): no in-app deploy
or stack management, no server console/chat, no multi-server management
screen, no auto-update for the GUI itself, no mod dependency resolution.

### Drag-and-drop caveat

Real filesystem drag-and-drop (reading a dropped file's actual path)
depends on the pywebview version and OS webview backend exposing
`File.path` on dropped files. If your build/platform doesn't support it,
the UI detects this and falls back to prompting for "Browse files…" or
"Open mods folder" — both work identically either way.

## Building a standalone app

```sh
cd gui
./packaging/build.sh          # macOS/Linux
# or: packaging\build.ps1     # Windows (PowerShell)
```

This creates its own build venv, installs `requirements.txt` (including
PyInstaller), and runs `pyinstaller packaging/pyinstaller.spec`. Output
lands in `gui/dist/`:

- macOS: `OpenCraftFormation.app` (optionally wrap in a `.dmg`, see the
  script's output for the `hdiutil` command)
- Windows: `OpenCraftFormation\OpenCraftFormation.exe`
- Linux: `OpenCraftFormation` binary

These builds are **unsigned**. macOS Gatekeeper and Windows SmartScreen
will warn on first launch (right-click → Open on macOS, "More info" → "Run
anyway" on Windows) — code signing/notarization is a later milestone, not
required for hobby-project distribution.

## Code layout

```
gui/
├── main.py              entrypoint: creates the pywebview window
├── app/
│   ├── api.py            the object exposed to JS as pywebview.api
│   ├── config.py         ~/.opencraftformation/config.json + params.yaml read/write
│   ├── hints.py           static instance-type/cost data + "what's my IP" helper
│   ├── export.py          bundles template.yaml/deploy.sh/destroy.sh/params.yaml/overlay/ into one zip
│   ├── overlay.py         mods/plugins/world/whitelist/ops/icon file management
│   └── paths.py           repo-root paths (overlay/, params.yaml, template.yaml)
├── web/                  the frontend: index.html, style.css, app.js (no build step)
└── packaging/            PyInstaller spec + build scripts
```
