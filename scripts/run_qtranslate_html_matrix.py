import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts" / "probe_qtranslate_capture.py"
PATCHED_EXE = ROOT / "QTranslate.6.9.0" / "QTranslate.patched.exe"
ORIGINAL_EXE = ROOT / "QTranslate.6.9.0" / "QTranslate.exe"


CASES = [
    {
        "name": "simple_double_quoted",
        "visible_text": "AA ЧИТАТЬ BB",
        "html_fragment": '<div>AA <a href="https://case1.example/link">ЧИТАТЬ</a> BB</div>',
    },
    {
        "name": "simple_single_quoted",
        "visible_text": "AA ЧИТАТЬ BB",
        "html_fragment": "<div>AA <a href='https://case2.example/link'>ЧИТАТЬ</a> BB</div>",
    },
    {
        "name": "simple_unquoted",
        "visible_text": "AA ЧИТАТЬ BB",
        "html_fragment": "<div>AA <a href=https://case3.example/link>ЧИТАТЬ</a> BB</div>",
    },
    {
        "name": "uppercase_href",
        "visible_text": "AA ЧИТАТЬ BB",
        "html_fragment": '<div>AA <a HREF="https://case4.example/link">ЧИТАТЬ</a> BB</div>',
    },
    {
        "name": "nested_markup_inside_anchor",
        "visible_text": "AA ЧИТАТЬ BB",
        "html_fragment": '<div>AA <a href="https://case5.example/link"><b>ЧИ</b><i>ТАТЬ</i></a> BB</div>',
    },
    {
        "name": "multiple_links_all_appended",
        "visible_text": "Alpha + Beta",
        "html_fragment": (
            '<div><a href="https://first.example/a">Alpha</a> + '
            '<a href="https://second.example/b">Beta</a></div>'
        ),
    },
    {
        "name": "non_anchor_href_before_anchor",
        "visible_text": "Meta Go",
        "html_fragment": (
            '<div><span href="https://wrong.example/meta">Meta</span> '
            '<a href="https://good.example/go">Go</a></div>'
        ),
    },
    {
        "name": "three_links_mixed_markup",
        "visible_text": "One / Two / Three",
        "html_fragment": (
            '<div><a href="https://one.example/a"><b>One</b></a> / '
            '<a HREF=\'https://two.example/b\'>Two</a> / '
            '<a href=https://three.example/c>Three</a></div>'
        ),
    },
    {
        "name": "named_entity_inside_anchor",
        "visible_text": "AA A & B BB",
        "html_fragment": '<div>AA <a href="https://entity.example/ab">A &amp; B</a> BB</div>',
    },
    {
        "name": "named_entity_before_anchor",
        "visible_text": "Fish & Chips Go",
        "html_fragment": '<div>Fish &amp; Chips <a href="https://entity.example/go">Go</a></div>',
    },
    {
        "name": "numeric_entity_emoji_before_anchor",
        "visible_text": "Smile 😀 Go",
        "html_fragment": '<div>Smile &#x1F600; <a href="https://entity.example/emoji-go">Go</a></div>',
    },
    {
        "name": "no_href_in_html",
        "visible_text": "Plain Text Only",
        "html_fragment": "<div><b>Plain</b> Text Only</div>",
    },
]


def run_probe(exe_path, case):
    command = [
        sys.executable,
        str(PROBE),
        "--exe",
        str(exe_path),
        "--mode",
        "html",
        "--trigger",
        "sendkeys",
        "--startup-delay",
        "4",
        "--timeout",
        "8",
        "--visible-text",
        case["visible_text"],
        "--html-fragment",
        case["html_fragment"],
    ]
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    payload = json.loads(completed.stdout)
    return {
        "returncode": completed.returncode,
        "payload": payload,
    }


def main():
    summary = []

    baseline_case = CASES[0]
    baseline_original = run_probe(ORIGINAL_EXE, baseline_case)
    summary.append({
        "name": "original_baseline",
        "exe": ORIGINAL_EXE.name,
        "ui_source_text": baseline_original["payload"].get("ui_source_text"),
        "ui_translation_text": baseline_original["payload"].get("ui_translation_text"),
        "error": baseline_original["payload"].get("error"),
        "returncode": baseline_original["returncode"],
    })

    for case in CASES:
        result = run_probe(PATCHED_EXE, case)
        payload = result["payload"]
        summary.append({
            "name": case["name"],
            "exe": PATCHED_EXE.name,
            "visible_text": case["visible_text"],
            "html_fragment": case["html_fragment"],
            "ui_source_text": payload.get("ui_source_text"),
            "ui_translation_text": payload.get("ui_translation_text"),
            "error": payload.get("error"),
            "returncode": result["returncode"],
        })

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
