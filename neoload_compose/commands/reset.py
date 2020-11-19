import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data
from compose_lib.command_category import CommandCategory

@click.command()
@click.option("--confirm", is_flag=True, default=False, help="Must confirm that you want to reset the current builder data")
@click.pass_context
@CommandCategory("Composing Queue Management")
def cli(ctx, confirm):
    """Resets the current builder data; must include --confirm command
    """
    builder_data.register_context(ctx, auto_reset=False)

    if confirm != True:
        raise cli_exception.CliException("You must use the --confirm option")

    builder_data.reset()
