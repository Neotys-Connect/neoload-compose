import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data
from compose_lib.command_category import CommandCategory

@click.command()
@click.option('--duration', help="The duration of this policy")
@click.argument("vus", type=int)
@click.pass_context
@CommandCategory("Composing")
def cli(ctx, duration, vus):
    """Defines a constant load policy for the current User Path
    """
    builder_data.register_context(ctx)

    builder = builder_data.get() \
        .add(builder_data.ConstantPolicy(vus, duration=duration)) \
        .save()
