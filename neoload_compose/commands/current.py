import sys
import click

from compose_lib import builder_data
from compose_lib.command_category import CommandCategory

import os

@click.command()
@click.option("--json", 'output_to_json', is_flag=True, default=False, help="Output internal JSON instead of YAML")
@click.option("--path", help="Write current test to a file or folder")
@click.pass_context
@CommandCategory("Validating")
def cli(ctx, output_to_json, path):
    """Prints out the current builder state
    """
    builder_data.register_context(ctx, auto_reset=False)

    output = builder_data.get() if output_to_json else builder_data.convert_builder_to_yaml(builder_data.get())

    if path is not None:
        builder_data.write_to_path(path, output)

    else:
        print(output)
