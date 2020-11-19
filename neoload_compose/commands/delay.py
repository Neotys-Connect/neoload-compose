import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data
from compose_lib.command_category import CommandCategory

@click.command()
@click.argument("duration", type=str)
@click.pass_context
@CommandCategory("Composing")
def cli(ctx, duration):
    """Adds a delay (think time) to the builder queue
    """
    builder_data.register_context(ctx)

    if duration is None:
        raise cli_exception.CliException("You must provide a time for this delay")

    builder = builder_data.get() \
        .add(builder_data.Delay(time=duration)) \
        .save()
