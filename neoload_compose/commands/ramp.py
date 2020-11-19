import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data
from compose_lib.command_category import CommandCategory

@click.command()
@click.option('--to', type=int, default=5, help="The max VUs/concurrency to ramp the population")
@click.option('--by', type=int, default=1, help="The # of VUs to add every 'per' interval")
@click.option('--per', default="5s", help="The interval to add VUs 'by'")
@click.option('--duration', help="The duration of this policy")
@click.pass_context
@CommandCategory("Composing")
def cli(ctx, to, by, per, duration):
    """Defines a ramp-up policy for the current User Path
    """
    builder_data.register_context(ctx)

    builder = builder_data.get() \
        .add(builder_data.RampPolicy(to=to, by=by, per=per, duration=duration)) \
        .save()
