import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data

@click.command()
@click.argument("duration", type=str)
@click.pass_context
def cli(ctx, duration):
    """This is the delay command
    """
    builder_data.register_context(ctx)

    if duration is None:
        raise cli_exception.CliException("You must provide a time for this delay")

    builder = builder_data.get() \
        .add(builder_data.Delay(time=duration)) \
        .save()
