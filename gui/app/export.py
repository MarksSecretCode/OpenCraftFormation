"""Prepares everything needed for a CloudShell (or any AWS CLI shell)
deploy, without the GUI ever touching your AWS account itself: bundles
template.yaml, deploy.sh, destroy.sh, params.yaml, and overlay/ into one
zip the user uploads and unzips there, then runs ./deploy.sh themselves.
"""
import zipfile
from typing import Any, Dict, List

from . import overlay, paths

BUNDLE_NAME = "craftainer-cloudshell.zip"
BUNDLE_ROOT_FILES = ["template.yaml", "deploy.sh", "destroy.sh", "params.yaml"]


def build_bundle() -> Dict[str, Any]:
    if not paths.PARAMS_FILE.exists():
        raise RuntimeError("params.yaml not found yet — go back to Configure and save your settings first.")

    overlay_files = [
        p for p in paths.OVERLAY_DIR.rglob("*")
        if p.is_file() and p.name != ".gitkeep"
    ]
    if not overlay_files:
        raise RuntimeError("overlay/ is empty — add mods/config/world on the Mods & Files screen first.")

    paths.BUILD_DIR.mkdir(parents=True, exist_ok=True)
    bundle_path = paths.BUILD_DIR / BUNDLE_NAME
    if bundle_path.exists():
        bundle_path.unlink()

    file_count = 0
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in BUNDLE_ROOT_FILES:
            src = paths.REPO_ROOT / name
            if src.exists():
                zf.write(src, name)
                file_count += 1
        for path in sorted(overlay_files):
            arcname = "overlay/" + str(path.relative_to(paths.OVERLAY_DIR))
            zf.write(path, arcname)
            file_count += 1

    return {
        "bundle_path": str(bundle_path),
        "bundle_size": bundle_path.stat().st_size,
        "file_count": file_count,
        "overlay_file_count": len(overlay_files),
    }


def open_build_folder() -> None:
    overlay.open_in_file_manager(paths.BUILD_DIR)


def cloudshell_instructions() -> List[str]:
    return [
        "Open AWS CloudShell in your target AWS region (the terminal icon in the top-right of the AWS Console).",
        "Actions → Upload file, and select build/{} (use \"Open build folder\" to find it).".format(BUNDLE_NAME),
        "Unzip and enter it: unzip -o {} -d craftainer && cd craftainer".format(BUNDLE_NAME),
        "Make the scripts executable: chmod +x deploy.sh destroy.sh",
        "Deploy: ./deploy.sh — it creates the S3 bucket, uploads the overlay, and deploys the CloudFormation stack.",
        "When it finishes, it prints the server's public IP.",
        "Later, to tear it down: from the same craftainer/ folder in CloudShell, run ./destroy.sh",
    ]
