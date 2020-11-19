import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data
from compose_lib.command_category import CommandCategory

@click.command()
@click.argument("spec", required=False, type=str)
@click.option('--name', '-n', required=False, help="The name of the header")
@click.option('--value', '-v', required=False, help="The value of the header")
@click.option('--all', is_flag=True, help="Apply this header to all prior requests")
@click.pass_context
@CommandCategory("Composing")
def cli(ctx, spec, name, value, all):
    """Defines a header for one or more request
    """
    builder_data.register_context(ctx)

    if name == "-":
        name = None

    if name and not value or value and not name:
        raise ValueError("If you specify either name or value arguments, you must provide both.")

    if spec and (name or value):
        raise ValueError("If you specify a name/value spec, you must specify a '-' for the spec.")

    if spec:
        parts = spec.split("=")
        name = parts[0]
        value = "=".join(parts[1:])

    builder = builder_data.get() \
        .add(builder_data.Header(name=name, value=value, all=all)) \
        .save()
