from rich.console import Console
from rich.panel import Panel

console = Console()


def success(
    algorithm,
    digest,
    elapsed,
    source,
    size=None,
):

    body = []

    body.append(f"[green]Algorithm[/green] : {algorithm}")

    body.append(f"[green]Source[/green]    : {source}")

    if size is not None:

        body.append(f"[green]Size[/green]      : {size}")

    body.append(f"[green]Time[/green]      : {elapsed:.4f} sec")

    body.append("")

    body.append("[yellow]Hash[/yellow]")

    body.append(digest)

    console.print(
        Panel(
            "\n".join(body),
            title="HashCLI",
            border_style="bright_blue",
        )
    )


def error(message):

    console.print(f"[bold red]{message}[/bold red]")
