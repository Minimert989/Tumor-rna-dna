from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from .config import load_config, project_path
from .pipeline import audit, build, export, run_sync
from .connectors.oncokb import annotate_variants
from .pipeline import context

app = typer.Typer(no_args_is_help=True)
DEFAULT_CONFIG = "config/pipeline.yaml"


def cfg(path: str):
    return load_config(path)


@app.command()
def init(config: str = DEFAULT_CONFIG):
    """Create data/export/report directories and initialize the DuckDB schema."""
    c = cfg(config)
    for key in ("raw_dir", "staged_dir", "export_dir", "report_dir"):
        project_path(c, c["project"][key]).mkdir(parents=True, exist_ok=True)
    db, _ = context(c)
    db.close()
    print("[green]Initialized atlas workspace.[/green]")


@app.command()
def sync(
    source: list[str] = typer.Option([], "--source", "-s", help="Repeatable source name."),
    config: str = DEFAULT_CONFIG,
):
    """Synchronize one or more open sources."""
    c = cfg(config)
    sources = source or ["oncotree", "drugs_at_fda", "openfda_labels", "dailymed", "clinicaltrials", "oncokb_import"]
    print(run_sync(c, sources))


@app.command("annotate-oncokb")
def annotate_oncokb(variants: str, config: str = DEFAULT_CONFIG):
    """Annotate a gene/protein-change/OncoTree table through the authenticated OncoKB API."""
    c = cfg(config)
    db, ctx = context(c)
    try:
        print({"records": annotate_variants(ctx, variants)})
    finally:
        db.close()


@app.command()
def compile(config: str = DEFAULT_CONFIG):
    """Import licensed/manual exports, map records, and build normalized atlas layers."""
    print(build(cfg(config)))


@app.command()
def qa(config: str = DEFAULT_CONFIG):
    """Run completeness and provenance audits."""
    print(audit(cfg(config)))


@app.command()
def export_atlas(config: str = DEFAULT_CONFIG):
    """Export CSV, Parquet and Excel atlas files."""
    path = export(cfg(config))
    print(f"[green]{path}[/green]")


@app.command()
def full(config: str = DEFAULT_CONFIG, skip_labels: bool = False, skip_trials: bool = False):
    """Run the full open-data pipeline, then imports, QA and export."""
    c = cfg(config)
    sources = ["oncotree", "drugs_at_fda"]
    if not skip_labels:
        sources += ["openfda_labels", "dailymed"]
    if not skip_trials:
        sources += ["clinicaltrials"]
    sources += ["oncokb_import"]
    print(run_sync(c, sources))
    print(build(c))
    print(audit(c))
    print(f"[green]{export(c)}[/green]")


if __name__ == "__main__":
    app()
