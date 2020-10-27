import sys
import click

from compose_lib import builder_data, profile
from commands import config
import tempfile
import subprocess
import yaml

@click.command()
@click.argument("name_or_id", required=False)
@click.option('--zone', required=False, help="The zone to run this test in.")
@click.option('--scenario', required=False, help="The scenario to run.")
@click.option('--save', is_flag=True, help="Save this as the default zone and test-setting")
@click.pass_context
def cli(ctx, name_or_id, zone, scenario, save):
    """Runs whatever is in the current buffer
    """
    builder_data.register_context(ctx, auto_reset=False)

    if name_or_id and save:
        config.test_setting(name_or_id)
    if zone and save:
        config.zone(zone)

    if not name_or_id:
        name_or_id = profile.get().default_test_setting
        if not name_or_id:
            raise ValueError("No test settings [name_or_id] provided and no default test-setting configured!")

    if not zone:
        zone = profile.get().default_zone
        if not zone:
            raise ValueError("No --zone provided and no default zone configured!")

    os_run("neoload status")

    yaml_str = builder_data.convert_builder_to_yaml(builder_data.get())
    data = yaml.safe_load(yaml_str)

    if not scenario:
        scenario = data['scenarios'][0]['name']

    dir = None
    with tempfile.TemporaryDirectory() as tmp:
        dir = tmp
        builder_data.write_to_path(dir, yaml_str)
        os_run("neoload test-settings --zone {} --lgs 1 --scenario {} createorpatch {}".format(zone, scenario, name_or_id))

        os_run("neoload project --path {} up".format(dir))

    os_run("neoload run".format(scenario))

def os_run(command):
    subprocess.run(command.split(), check = True)
