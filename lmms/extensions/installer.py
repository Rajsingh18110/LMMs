"""
Extension Installer — downloads VSIX from Open VSX, validates, extracts.

VSIX files are ZIP archives with this structure:
  extension/
    package.json      ← manifest
    dist/             ← compiled JS
    ...
  [Content_Types].xml
  extension.vsixmanifest

We extract to ~/.lmms/extensions/{namespace}.{name}-{version}/
"""
from __future__ import annotations
import os
import json
import zipfile
import hashlib
import shutil
import tempfile
import requests

from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from lmms.extensions.models import ExtensionRecord, ExtState, CompatLevel, EXTENSIONS_ROOT


class InstallThread(QThread):
    """
    Downloads and extracts a VS Code extension (VSIX) from Open VSX.

    Signals
    -------
    progress(int)               0-100
    log(str)                    log line
    done(ExtensionRecord)       success
    error(str)                  failure message
    """

    progress = pyqtSignal(int)
    log      = pyqtSignal(str)
    done     = pyqtSignal(object)   # ExtensionRecord
    error    = pyqtSignal(str)

    def __init__(self, ext_dict: dict, parent=None):
        super().__init__(parent)
        self.ext_dict = ext_dict

    def run(self):
        ext   = self.ext_dict
        ns    = ext.get("namespace", "")
        name  = ext.get("name", "")
        ver   = ext.get("version", "")
        ext_id = f"{ns}.{name}"

        try:
            # ── 1. Resolve download URL ───────────────────────────────────
            self.log.emit(f"[{ext_id}] Resolving package URL…")
            self.progress.emit(5)

            files = ext.get("files") or {}
            dl_url = files.get("download", "")
            sha256_url = files.get("sha256", "")

            import time
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            session = requests.Session()
            retries = Retry(total=3, backoff_factor=1, status_forcelist=[ 500, 502, 503, 504 ])
            session.mount('http://', HTTPAdapter(max_retries=retries))
            session.mount('https://', HTTPAdapter(max_retries=retries))

            # If no download URL in ext_dict, fetch from API
            if not dl_url:
                api_url = f"https://open-vsx.org/api/{ns}/{name}"
                if ver:
                    api_url += f"/{ver}"
                r = session.get(api_url, timeout=12)
                r.raise_for_status()
                data   = r.json()
                files  = data.get("files", {})
                dl_url = files.get("download", "")
                sha256_url = files.get("sha256", "")
                ver    = data.get("version", ver)
                # Refresh manifest data
                ext = {**ext, **data}

            if not dl_url:
                raise RuntimeError("No download URL available for this extension.")

            # ── 2. Download VSIX ──────────────────────────────────────────
            self.log.emit(f"[{ext_id}] Downloading {dl_url} …")
            self.progress.emit(10)

            EXTENSIONS_ROOT.mkdir(parents=True, exist_ok=True)
            tmp_vsix = EXTENSIONS_ROOT / f"_tmp_{ns}.{name}.vsix"

            with session.get(dl_url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                sha = hashlib.sha256()
                last_emit = time.time()
                with open(tmp_vsix, "wb") as fh:
                    # 1MB chunk size instead of 64KB
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            fh.write(chunk)
                            sha.update(chunk)
                            downloaded += len(chunk)
                            if total:
                                now = time.time()
                                if now - last_emit > 0.1:  # max 10 emissions per second
                                    pct = 10 + int(50 * downloaded / total)
                                    self.progress.emit(min(pct, 60))
                                    last_emit = now

            actual_sha = sha.hexdigest()
            self.log.emit(f"[{ext_id}] Downloaded {downloaded:,} bytes — SHA256: {actual_sha[:12]}…")

            # ── 3. Validate SHA256 ────────────────────────────────────────
            if sha256_url:
                try:
                    r2 = requests.get(sha256_url, timeout=8)
                    expected = r2.text.strip().split()[0].lower()
                    if expected and expected != actual_sha.lower():
                        raise RuntimeError(
                            f"SHA256 mismatch!\n"
                            f"Expected: {expected}\n"
                            f"Got:      {actual_sha}"
                        )
                    self.log.emit(f"[{ext_id}] ✓ SHA256 verified")
                except requests.RequestException:
                    self.log.emit(f"[{ext_id}] ⚠ Could not fetch SHA256 (skipping)")

            self.progress.emit(65)

            # ── 4. Extract VSIX ───────────────────────────────────────────
            install_dir = EXTENSIONS_ROOT / f"{ns}.{name}-{ver}"
            if install_dir.exists():
                shutil.rmtree(install_dir)
            install_dir.mkdir(parents=True)

            self.log.emit(f"[{ext_id}] Extracting to {install_dir} …")

            with zipfile.ZipFile(tmp_vsix) as zf:
                zf.extractall(install_dir)

            tmp_vsix.unlink(missing_ok=True)
            self.progress.emit(80)

            # ── 5. Parse manifest ─────────────────────────────────────────
            # VSIX extracts to "extension/package.json"
            manifest_path = install_dir / "extension" / "package.json"
            if not manifest_path.exists():
                # Fallback: search for package.json
                matches = list(install_dir.rglob("package.json"))
                if matches:
                    manifest_path = matches[0]
                else:
                    raise RuntimeError("package.json not found inside VSIX.")

            with open(manifest_path, encoding="utf-8") as fh:
                manifest = json.load(fh)

            self.log.emit(f"[{ext_id}] ✓ Manifest parsed — {len(manifest.get('contributes', {}))} contribution point(s)")
            self.progress.emit(90)

            # ── 6. Check dependencies ─────────────────────────────────────
            ext_deps   = manifest.get("extensionDependencies", [])
            ext_pack   = manifest.get("extensionPack", [])
            if ext_deps:
                self.log.emit(f"[{ext_id}] ℹ Requires: {', '.join(ext_deps)}")

            # ── 7. Compute compatibility ──────────────────────────────────
            from lmms.extensions.models import compute_compat
            compat = compute_compat(manifest)
            self.log.emit(f"[{ext_id}] Compatibility: {compat.value}")

            # ── 8. Build record ───────────────────────────────────────────
            record = ExtensionRecord(
                ext_id       = ext_id,
                namespace    = ns,
                name         = name,
                display_name = manifest.get("displayName") or ext.get("displayName") or name,
                version      = ver,
                state        = ExtState.INSTALLED,
                compat       = compat,
                path         = str(install_dir),
                manifest     = manifest,
                icon_url     = (ext.get("files") or {}).get("icon") or ext.get("icon_url"),
                downloads    = int(ext.get("downloadCount") or 0),
            )
            record.log(f"Downloaded and extracted successfully.")
            record.log(f"Compatibility: {compat.value}")

            self.progress.emit(100)
            self.log.emit(f"[{ext_id}] ✓ Installation complete.")
            self.done.emit(record)

        except Exception as exc:
            tmp = EXTENSIONS_ROOT / f"_tmp_{ns}.{name}.vsix"
            tmp.unlink(missing_ok=True)
            msg = f"Installation failed: {exc}"
            self.log.emit(f"[{ext_id}] ✕ {msg}")
            self.error.emit(msg)


class UninstallThread(QThread):
    """Removes an installed extension directory."""

    done  = pyqtSignal(str)   # ext_id
    error = pyqtSignal(str)

    def __init__(self, ext_id: str, path: str, parent=None):
        super().__init__(parent)
        self.ext_id = ext_id
        self.path   = path

    def run(self):
        try:
            if self.path and os.path.isdir(self.path):
                shutil.rmtree(self.path)
            self.done.emit(self.ext_id)
        except Exception as e:
            self.error.emit(str(e))
