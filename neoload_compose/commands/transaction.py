import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data

@click.command()
@click.argument("name", type=str)
@click.option('--description','-d', help="The description of this transaction")
@click.option("--inside", is_flag=True, default=False, help="Append this transaction inside prior transaction")
@click.pass_context
def cli(ctx, name, description, inside):
    """This is the transaction command
    """
    builder_data.register_context(ctx)

    if name is None:
        raise cli_exception.CliException("You must provide a name for this transaction")

    builder = builder_data.get() \
        .add(builder_data.Transaction(name=name, description=description, inside=inside)) \
        .save()