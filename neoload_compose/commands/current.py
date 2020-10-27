import sys
import click

from compose_lib import builder_data

import os

@click.command()
@click.option("--json", is_flag=True, default=False, help="Output internal JSON instead of YAML")
@click.option("--path", help="Write current test to a file or folder")
@click.pass_context
def cli(ctx, json, path):
    """Prints out the current builder state
    """
    builder_data.register_context(ctx, auto_reset=False)

    output = builder_data.get() if json else builder_data.convert_builder_to_yaml(builder_data.get())

    if path is not None:
        builder_data.write_to_path(path, output)

    else:
        print(output)
