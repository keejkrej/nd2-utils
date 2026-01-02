import os
from typing import Optional, List, Tuple, Union, Any
import typer
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.panel import Panel

from ..processors.nd2_processor import load_file
from ..processors.export_logic import TiffExportLogic
from ..core.signals import SignalsInterface, WorkerSignal

app = typer.Typer(help="ND2 Utilities CLI")
console = Console()


class RichSignal(WorkerSignal):
    def emit(self, *args: Any) -> None:
        # For progress bar updates if needed, though we use progress_wrapper for the main loop
        pass


class RichSignals(SignalsInterface):
    def __init__(self):
        self.progress = RichSignal()
        self.finished = RichSignal()
        self.error = RichSignal()


def parse_range(range_str: Optional[str]) -> Optional[Tuple[int, int]]:
    if not range_str:
        return None

    if "-" in range_str:
        parts = range_str.split("-")
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]))

    try:
        val = int(range_str)
        return (val, val)
    except ValueError:
        return None


@app.command()
def info(
    file_path: str = typer.Argument(..., help="Path to the ND2 file"),
):
    """Display information about an ND2 file."""
    if not os.path.exists(file_path):
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        raise typer.Exit(1)

    with console.status("[bold green]Loading metadata..."):
        info_dict = load_file(file_path)

    # Display basic info
    console.print(Panel(f"[bold blue]File:[/bold blue] {file_path}", title="ND2 Info"))

    # Dimensions table
    dim_table = Table(title="Dimensions")
    dim_table.add_column("Axis", style="cyan")
    dim_table.add_column("Size", style="magenta")

    dimensions = info_dict.get("dimensions", {})
    for axis, data in dimensions.items():
        dim_table.add_row(axis, str(data.get("size", 1)))

    console.print(dim_table)

    # Channel info
    channels = info_dict.get("attributes", {}).get("channelNames", [])
    if channels:
        chan_table = Table(title="Channels")
        chan_table.add_column("Index", style="cyan")
        chan_table.add_column("Name", style="green")
        for i, name in enumerate(channels):
            chan_table.add_row(str(i), name)
        console.print(chan_table)


@app.command()
def export(
    input_path: str = typer.Argument(..., help="Path to the ND2 file"),
    output_path: str = typer.Argument(..., help="Path to the output TIFF file"),
    position: Optional[str] = typer.Option(
        None, "--pos", "-p", help="Position range (e.g., '0-2' or '0')"
    ),
    channel: Optional[str] = typer.Option(None, "--chan", "-c", help="Channel range"),
    time: Optional[str] = typer.Option(None, "--time", "-t", help="Time range"),
    z: Optional[str] = typer.Option(None, "--z", "-z", help="Z-slice range"),
):
    """Export ND2 to TIFF with selected ranges."""
    if not os.path.exists(input_path):
        console.print(f"[red]Error: Input file not found: {input_path}[/red]")
        raise typer.Exit(1)

    pos_range = parse_range(position)
    chan_range = parse_range(channel)
    time_range = parse_range(time)
    z_range = parse_range(z)

    console.print(f"[yellow]Exporting:[/yellow] {input_path} -> {output_path}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        main_task = progress.add_task("Preparing export...", total=100)

        def signals_progress_emit(val: int):
            progress.update(main_task, completed=val)

        class Signals:
            def __init__(self):
                self.progress = type("obj", (object,), {"emit": signals_progress_emit})
                self.finished = type("obj", (object,), {"emit": lambda x: None})
                self.error = type(
                    "obj",
                    (object,),
                    {"emit": lambda x: console.print(f"[red]{x}[/red]")},
                )

        def rich_wrapper(iterable):
            return progress.track(iterable, description="Extracting data...")

        try:
            TiffExportLogic.export(
                nd2_path=input_path,
                output_path=output_path,
                position=pos_range,
                channel=chan_range,
                time=time_range,
                z=z_range,
                signals=Signals(),
                progress_wrapper=rich_wrapper,
            )
            console.print(
                f"[bold green]Successfully exported to {output_path}[/bold green]"
            )
        except Exception as e:
            console.print(f"[bold red]Export failed: {e}[/bold red]")
            raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
