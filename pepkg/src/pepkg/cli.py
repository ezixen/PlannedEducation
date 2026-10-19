"""Main CLI entry point for pepkg."""

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from .commands import (
    auth,
    package,
    publish,
    search,
    validate,
)
from .config import Config

# Load environment variables from .env file
load_dotenv()


@click.group()
@click.version_option(version="1.0.0", prog_name="pepkg")
@click.option(

    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to config file",
    default=None,
)
@click.option(
    "--api-url",
    envvar="PEPKG_API_URL",
    help="API base URL (default: http://localhost:8000)",
    default="http://localhost:8000",
)
@click.option(
    "--token",
    envvar="PEPKG_TOKEN",
    help="Authentication token",
    default=None,
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Enable verbose output"
)
@click.pass_context
def cli(ctx: click.Context, config: Path | None, api_url: str, token: str | None, verbose: bool) -> None:
    """pepkg - PlannedEducation Package Registry CLI.

    Manage test packages for the PlannedEducation platform.
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config(
        config_path=config,
        api_url=api_url,
        token=token,
        verbose=verbose,
    )


# Add subcommands
cli.add_command(auth.auth)
cli.add_command(package.package)
cli.add_command(publish.publish)
cli.add_command(search.search)
cli.add_command(validate.validate)


def main() -> int:
    """Main entry point."""
    try:
        cli(obj={})
        return 0
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())