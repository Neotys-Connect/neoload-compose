import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data

@click.command()
@click.argument("vus", type=int)
@click.pass_context
def cli(ctx, vus):
    """Defines a ramp-up policy for the current User Path
    """
    builder_data.register_context(ctx)

    builder = builder_data.get() \
        .add(builder_data.ConstantPolicy(vus)) \
        .save()
