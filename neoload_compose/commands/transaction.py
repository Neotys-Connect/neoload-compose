import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data
from compose_lib.command_category import CommandCategory

@click.command()
@click.argument("name", type=str)
@click.option('--description','-d', help="The description of this transaction")
@click.option("--inside", default='last', help="Append this transaction inside a prior transaction")
@click.pass_context
@CommandCategory("Composing")
def cli(ctx, name, description, inside):
    """Adds a transaction to the builder queue; do before requests
    """
    builder_data.register_context(ctx)

    if name is None:
        raise cli_exception.CliException("You must provide a name for this transaction")

    builder = builder_data.get() \
        .add(builder_data.Transaction(name=name, description=description, inside=inside)) \
        .save()
