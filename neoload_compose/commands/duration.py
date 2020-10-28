import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data

@click.command()
@click.argument("duration", type=str)
@click.pass_context
def cli(ctx, duration):
    """Defines a duration policy for the current scenario
    """
    builder_data.register_context(ctx)

    builder = builder_data.get() \
        .add(builder_data.DurationPolicy(duration=duration)) \
        .save()
