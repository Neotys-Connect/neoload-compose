import sys
import click

from compose_lib import builder_data

import os

@click.command()
@click.argument("back", type=int, default=1)
@click.pass_context
def cli(ctx, back):
    """Rolls back the prior [back] number of builder commands
    """
    builder_data.register_context(ctx, auto_reset=False)

    data = builder_data.get()
    for i in range(0,back):
        if len(data.stack) > 0:
            data.stack.pop()

    data.save()
