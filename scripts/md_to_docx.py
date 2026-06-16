"""Convert a repo markdown doc to a self-contained Word .docx.

Rewrites relative .md links (e.g. `multi_agent_orchestrator.md`, `../PROJECT_RUNBOOK.md`)
to absolute GitHub `blob/main` URLs so the Word doc is self-contained and every link
leads somewhere useful (the file hosted on GitHub). Renders landscape (the SKU matrix
is wide) via a generated reference doc, using pandoc.

Usage: python scripts/md_to_docx.py <src.md> [<out.docx>]
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GITHUB_BASE = "https://github.com/jasmeetsb/agent-cost-estimator/blob/main"
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def rewrite_links(md_text, src_dir):
    """Rewrite relative .md links to GitHub blob URLs (resolved vs the source dir)."""
    def repl(m):
        label, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            return m.group(0)
        path_part, _, anchor = target.partition("#")
        if not path_part.endswith(".md"):
            return m.group(0)
        resolved = (src_dir / path_part).resolve()
        try:
            rel = resolved.relative_to(REPO)
        except ValueError:
            return m.group(0)
        url = f"{GITHUB_BASE}/{rel}" + (f"#{anchor}" if anchor else "")
        return f"[{label}]({url})"
    return _LINK.sub(repl, md_text)


def _landscape_reference(path):
    """Generate a minimal landscape, narrow-margin reference docx for pandoc."""
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.shared import Inches
    d = Document()
    s = d.sections[0]
    s.orientation = WD_ORIENT.LANDSCAPE
    s.page_width, s.page_height = s.page_height, s.page_width
    s.left_margin = s.right_margin = Inches(0.5)
    s.top_margin = s.bottom_margin = Inches(0.6)
    d.save(path)


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    src = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else src.with_suffix(".docx")
    text = rewrite_links(src.read_text(), src.parent)

    tmp_md = src.with_suffix(".ghlinks.md")
    ref = src.with_suffix(".ref.docx")
    tmp_md.write_text(text)
    _landscape_reference(ref)
    try:
        subprocess.run(
            ["pandoc", str(tmp_md), "-o", str(out), "--from=gfm",
             f"--reference-doc={ref}", "--toc", "--toc-depth=2"],
            check=True)
    finally:
        tmp_md.unlink(missing_ok=True)
        ref.unlink(missing_ok=True)
    n_links = len(re.findall(re.escape(GITHUB_BASE), text))
    print(f"wrote {out}  ({n_links} GitHub links rewritten)")


if __name__ == "__main__":
    main()
