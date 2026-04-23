from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "scripts" / "probe_qtranslate_capture.py"
EDGE_UIA = ROOT / "scripts" / "probe_qtranslate_edge_uia_accessibility.py"


def run_json(argv: list[str]) -> dict:
    completed = subprocess.run(
        [sys.executable, *argv],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(argv)}\n"
            f"stdout={completed.stdout!r}\n"
            f"stderr={completed.stderr!r}"
        )
    return json.loads(completed.stdout)


def summarize_clipboard(result: dict) -> dict:
    return {
        "exe": result["exe"],
        "source": result.get("ui_source_text"),
        "translation": result.get("ui_translation_text"),
        "marker": result.get("marker"),
    }


def summarize_uia(result: dict) -> dict:
    richtexts = result.get("richtexts", [])
    return {
        "exe": result["exe"],
        "source": richtexts[0] if len(richtexts) > 0 else None,
        "translation": richtexts[1] if len(richtexts) > 1 else None,
        "link_name": result.get("edge_probe", {}).get("RenderWidget", {}).get("PointProbe", {}).get("Element", {}).get("Name"),
        "link_value": result.get("edge_probe", {}).get("RenderWidget", {}).get("PointProbe", {}).get("Element", {}).get("Value"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test the stable QTranslate link-preservation paths.")
    parser.add_argument(
        "--clipboard-exe",
        default=ROOT / "QTranslate.6.9.0" / "QTranslate.patched.exe",
        type=Path,
    )
    parser.add_argument(
        "--uia-exe",
        default=ROOT / "QTranslate.6.9.0" / "QTranslate.accessibility.default_uia.exe",
        type=Path,
    )
    args = parser.parse_args()

    clipboard = run_json([str(CAPTURE), "--exe", str(args.clipboard_exe), "--mode", "html"])
    uia = run_json([str(EDGE_UIA), "--exe", str(args.uia_exe)])

    print(json.dumps({
        "clipboard": summarize_clipboard(clipboard),
        "uia": summarize_uia(uia),
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
