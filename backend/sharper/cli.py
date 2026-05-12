"""CLI: pipe a forecasting question in, get a structured critique out."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .critic import critique_question
from .schema import Critique, Severity

app = typer.Typer(add_completion=False, help="Sharper — lint forecasting questions.")
console = Console()

SEVERITY_STYLES = {
    Severity.high: "bold red",
    Severity.medium: "yellow",
    Severity.low: "dim",
}


def _read_input(text: Optional[str], file: Optional[Path], line: int) -> str:
    if text is not None:
        return text
    if file is not None:
        if not file.exists():
            raise typer.BadParameter(f"file not found: {file}")
        if file.suffix == ".jsonl":
            with file.open("r", encoding="utf-8") as f:
                for i, raw in enumerate(f, start=1):
                    if i == line:
                        record = json.loads(raw)
                        for key in ("question", "title", "text"):
                            if key in record:
                                return record[key]
                        raise typer.BadParameter(
                            f"JSONL line {line} has no `question`/`title`/`text` field"
                        )
            raise typer.BadParameter(f"file has fewer than {line} lines")
        return file.read_text(encoding="utf-8")
    if sys.stdin.isatty():
        raise typer.BadParameter(
            "no input — pass --text, --file, or pipe a question on stdin"
        )
    return sys.stdin.read()


def _render_pretty(critique: Critique) -> None:
    if not critique.findings:
        console.print(Panel.fit(critique.overall_assessment, title="Sharper", border_style="green"))
        return

    table = Table(title="Findings", show_lines=True)
    table.add_column("Severity", style="bold")
    table.add_column("Rubric item")
    table.add_column("Quoted span", style="cyan")
    table.add_column("Issue + explanation")

    for f in critique.findings:
        table.add_row(
            f"[{SEVERITY_STYLES[f.severity]}]{f.severity.value}[/]",
            f.rubric_item.value,
            f.quoted_span,
            f"{f.issue}\n\n[dim]{f.explanation}[/]",
        )
    console.print(table)
    console.print(Panel.fit(critique.overall_assessment, title="Overall", border_style="blue"))


@app.command()
def lint(
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Inline question text."),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read from a file."),
    line: int = typer.Option(1, "--line", "-l", help="Line to read when --file is .jsonl."),
    pretty: bool = typer.Option(False, "--pretty", help="Rich-formatted output instead of JSON."),
) -> None:
    """Lint a forecasting question against the rubric."""
    load_dotenv()
    question = _read_input(text, file, line)
    critique = critique_question(question)
    if pretty:
        _render_pretty(critique)
    else:
        sys.stdout.write(critique.model_dump_json(indent=2) + "\n")


if __name__ == "__main__":
    app()
