"""
Normalize Jinja HTML templates: legacy slate/emerald/red/amber/blue → GMP semantic tokens.

  python scripts/normalize_gmp_theme_templates.py

Uses substring replace only; longer patterns first (no regex word-boundary bugs).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "backend" / "templates"

# (old, new) — longer / more specific first.
REPLACEMENTS: list[tuple[str, str]] = [
    ("bg-slate-950/95", "bg-gmp-surface-inset/95"),
    ("bg-slate-950/90", "bg-gmp-surface-inset/90"),
    ("bg-slate-950/75", "bg-gmp-surface-inset/75"),
    ("bg-slate-950/50", "bg-gmp-surface-inset/50"),
    ("bg-slate-950/40", "bg-gmp-surface-inset/40"),
    ("bg-slate-900/95", "bg-gmp-surface/95"),
    ("bg-slate-900/90", "bg-gmp-surface/90"),
    ("bg-slate-900/80", "bg-gmp-surface/80"),
    ("bg-slate-900/70", "bg-gmp-surface/70"),
    ("bg-slate-900/60", "bg-gmp-surface/60"),
    ("bg-slate-900/50", "bg-gmp-surface/50"),
    ("bg-slate-900/40", "bg-gmp-surface/40"),
    ("bg-slate-800/90", "bg-gmp-surface-raised/90"),
    ("bg-slate-800/80", "bg-gmp-surface-raised/80"),
    ("bg-slate-800/70", "bg-gmp-surface-raised/70"),
    ("bg-slate-800/60", "bg-gmp-surface-raised/60"),
    ("bg-slate-800/50", "bg-gmp-surface-raised/50"),
    ("bg-slate-800/40", "bg-gmp-surface-raised/40"),
    ("bg-slate-800/30", "bg-gmp-surface-raised/30"),
    ("bg-slate-700/50", "bg-gmp-surface-raised/50"),
    ("hover:bg-slate-900/50", "hover:bg-gmp-surface/50"),
    ("hover:bg-slate-800/80", "hover:bg-gmp-surface-raised/80"),
    ("hover:bg-slate-800", "hover:bg-gmp-surface-raised"),
    ("hover:bg-slate-850", "hover:bg-gmp-surface-raised"),
    ("hover:bg-slate-700", "hover:bg-gmp-surface-popover"),
    ("hover:bg-slate-900", "hover:bg-gmp-surface"),
    ("from-slate-900", "from-gmp-surface"),
    ("to-slate-900", "to-gmp-surface"),
    ("via-slate-900", "via-gmp-surface"),
    ("border-slate-900/50", "border-gmp-surface-inset/50"),
    ("border-slate-800/80", "border-gmp-border-subtle/80"),
    ("border-slate-800/50", "border-gmp-border-subtle/50"),
    ("border-slate-700/80", "border-gmp-border/80"),
    ("border-slate-700/70", "border-gmp-border/70"),
    ("border-slate-700/60", "border-gmp-border/60"),
    ("border-slate-700/50", "border-gmp-border/50"),
    ("border-slate-600/80", "border-gmp-border/80"),
    ("border-slate-600/70", "border-gmp-border/70"),
    ("border-slate-600/60", "border-gmp-border/60"),
    ("border-slate-600/50", "border-gmp-border/50"),
    ("text-emerald-300/90", "text-success/90"),
    ("text-emerald-400/80", "text-success/80"),
    ("text-emerald-500/80", "text-success/80"),
    ("border-emerald-700/50", "border-success/50"),
    ("border-emerald-600/60", "border-success/60"),
    ("border-emerald-500/30", "border-success/30"),
    ("bg-emerald-950/95", "bg-gmp-surface-inset/95"),
    ("bg-emerald-950/90", "bg-gmp-surface-inset/90"),
    ("bg-emerald-950/50", "bg-success/10"),
    ("bg-emerald-900/40", "bg-success/10"),
    ("bg-emerald-900/30", "bg-success/10"),
    ("hover:bg-emerald-700", "hover:bg-primaryHover"),
    ("hover:bg-emerald-600", "hover:bg-primaryHover"),
    ("bg-emerald-600/20", "bg-success/20"),
    ("bg-emerald-500/10", "bg-success/10"),
    ("bg-emerald-500/20", "bg-success/20"),
    ("text-red-400/90", "text-danger/90"),
    ("border-red-900/50", "border-danger/50"),
    ("border-red-800/60", "border-danger/40"),
    ("border-red-400/20", "border-danger/20"),
    ("bg-red-950/50", "bg-danger/10"),
    ("bg-red-900/50", "bg-danger/10"),
    ("bg-red-900/40", "bg-danger/10"),
    ("bg-red-900/30", "bg-danger/10"),
    ("bg-red-900/20", "bg-danger/10"),
    ("bg-red-400/10", "bg-danger/10"),
    ("bg-red-500/10", "bg-danger/10"),
    ("bg-red-500/20", "bg-danger/20"),
    ("text-amber-400/90", "text-warning/90"),
    ("bg-amber-950/95", "bg-gmp-surface-inset/95"),
    ("bg-amber-900/30", "bg-warning/10"),
    ("border-amber-600/70", "border-warning/70"),
    ("border-blue-500/30", "border-info/30"),
    ("bg-blue-950/30", "bg-info/10"),
    ("bg-blue-900/20", "bg-info/10"),
    ("bg-blue-900/30", "bg-info/10"),
    ("bg-yellow-900/20", "bg-warning/10"),
    ("bg-slate-950", "bg-gmp-surface-inset"),
    ("bg-slate-900", "bg-gmp-surface"),
    ("bg-slate-850", "bg-gmp-surface-raised"),
    ("bg-slate-800", "bg-gmp-surface-raised"),
    ("bg-slate-750", "bg-gmp-surface-raised"),
    ("bg-slate-700", "bg-gmp-surface-raised"),
    ("border-slate-900", "border-gmp-surface-inset"),
    ("border-slate-800", "border-gmp-border-subtle"),
    ("border-slate-750", "border-gmp-border-subtle"),
    ("border-slate-700", "border-gmp-border"),
    ("border-slate-600", "border-gmp-border"),
    ("border-slate-500", "border-gmp-border"),
    ("divide-slate-800", "divide-gmp-border-subtle"),
    ("divide-slate-700", "divide-gmp-border"),
    ("divide-slate-600", "divide-gmp-border"),
    ("ring-slate-700", "ring-gmp-border"),
    ("ring-slate-600", "ring-gmp-border"),
    ("ring-slate-500", "ring-gmp-border"),
    ("focus:border-slate-700", "focus:border-gmp-border"),
    ("focus:border-slate-600", "focus:border-gmp-border"),
    ("focus:ring-slate-700", "focus:ring-gmp-border"),
    ("focus:ring-slate-600", "focus:ring-gmp-border"),
    # numeric text-slate-* longest first (avoid text-slate-50 matching inside text-slate-500)
    ("text-slate-700", "text-gmp-text-faint"),
    ("text-slate-600", "text-gmp-text-faint"),
    ("text-slate-500", "text-gmp-text-faint"),
    ("text-slate-400", "text-gmp-text-muted"),
    ("text-slate-300", "text-gmp-text-menu"),
    ("text-slate-200", "text-gmp-text"),
    ("text-slate-100", "text-gmp-text-heading"),
    ("text-slate-50", "text-gmp-text-heading"),
    ("placeholder-slate-500", "placeholder-gmp-text-faint"),
    ("placeholder-slate-400", "placeholder-gmp-text-muted"),
    ("text-emerald-100", "text-success"),
    ("text-emerald-200", "text-success"),
    ("text-emerald-300", "text-success"),
    ("text-emerald-400", "text-success"),
    ("text-emerald-500", "text-success"),
    ("text-emerald-600", "text-success"),
    ("border-emerald-700", "border-success"),
    ("border-emerald-600", "border-success"),
    ("border-emerald-500", "border-success"),
    ("bg-emerald-950", "bg-gmp-surface-inset"),
    ("bg-emerald-900", "bg-success/20"),
    ("bg-emerald-600", "bg-primaryHover"),
    ("bg-emerald-500", "bg-success"),
    ("from-emerald-500", "from-success"),
    ("to-emerald-600", "to-primaryHover"),
    ("text-red-100", "text-danger"),
    ("text-red-200", "text-danger"),
    ("text-red-300", "text-danger"),
    ("text-red-400", "text-danger"),
    ("text-red-500", "text-danger"),
    ("text-red-600", "text-danger"),
    ("border-red-800", "border-danger/40"),
    ("border-red-700", "border-danger/40"),
    ("border-red-600", "border-danger"),
    ("border-red-500", "border-danger"),
    ("border-red-400", "border-danger"),
    ("bg-red-950", "bg-gmp-surface-inset"),
    ("bg-red-900", "bg-danger/20"),
    ("text-amber-100", "text-warning"),
    ("text-amber-200", "text-warning"),
    ("text-amber-300", "text-warning"),
    ("text-amber-400", "text-warning"),
    ("text-amber-500", "text-warning"),
    ("bg-amber-950", "bg-gmp-surface-inset"),
    ("bg-amber-500", "bg-warning"),
    ("border-amber-600", "border-warning"),
    ("border-amber-500", "border-warning"),
    ("text-blue-100", "text-info"),
    ("text-blue-200", "text-info"),
    ("hover:text-blue-300", "hover:text-info"),
    ("text-blue-300", "text-info"),
    ("text-blue-400", "text-info"),
    ("text-blue-500", "text-info"),
    ("border-blue-500", "border-info"),
    ("border-blue-400", "border-info"),
    ("text-cyan-400", "text-info"),
    ("border-cyan-500", "border-info"),
    ("text-orange-400", "text-warning"),
    ("border-orange-500", "border-warning"),
    ("text-violet-400", "text-secondary"),
    ("text-purple-400", "text-secondary"),
    ("border-violet-500", "border-secondary"),
    ("text-yellow-400", "text-warning"),
    ("text-indigo-400", "text-info"),
    # second pass: leftovers from first run
    ("placeholder-slate-600", "placeholder-gmp-text-faint"),
    ("hover:bg-slate-600", "hover:bg-surfaceHover"),
    ("hover:bg-slate-500", "hover:bg-gmp-border"),
    ("bg-slate-600", "bg-surfaceHover"),
    ("bg-slate-500/10", "bg-gmp-text-faint/10"),
    ("bg-slate-500/30", "bg-gmp-text-faint/30"),
    ("bg-slate-500", "bg-gmp-text-faint"),
    ("bg-slate-400", "bg-gmp-text-muted"),
    ("bg-amber-600/80", "bg-warning/80"),
    ("hover:bg-amber-600", "hover:bg-warning"),
    ("focus:ring-amber-500", "focus:ring-warning"),
    ("accent-amber-500", "accent-warning"),
    ("bg-blue-950/60", "bg-info/15"),
    ("bg-blue-950/20", "bg-info/10"),
    ("hover:bg-blue-600", "hover:bg-infoHover"),
    ("text-yellow-500/80", "text-warning/80"),
    ("text-yellow-500/70", "text-warning/70"),
    ("border-yellow-500/40", "border-warning/40"),
    ("border-yellow-500/30", "border-warning/30"),
    ("border-yellow-500/20", "border-warning/20"),
    ("bg-yellow-500/20", "bg-warning/20"),
    ("bg-yellow-500/5", "bg-warning/5"),
    ("hover:text-purple-300", "hover:text-secondary"),
    ("hover:border-purple-500/50", "hover:border-secondary/50"),
    ("border-indigo-500/30", "border-info/30"),
]

SKIP_NAMES = frozenset({"gmp_tailwind_head.html"})


def patch_text(s: str) -> str:
    for old, new in REPLACEMENTS:
        s = s.replace(old, new)
    return s


def main() -> None:
    changed: list[Path] = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        if path.name in SKIP_NAMES:
            continue
        raw = path.read_text(encoding="utf-8")
        out = patch_text(raw)
        if out != raw:
            path.write_text(out, encoding="utf-8", newline="\n")
            changed.append(path)
    print(f"Updated {len(changed)} template(s)")
    for p in changed:
        print(" ", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
