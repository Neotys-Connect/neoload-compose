import sys
import click

from compose_lib import builder_data, profile
from commands import config
import tempfile
import yaml
import json
from compose_lib.common import os_run, os_return
from compose_lib.command_category import CommandCategory

from neoload.neoload_cli_lib import tools

@click.command()
@click.argument("name_or_id", required=False)
@click.option('--zone', required=False, help="The zone to run this test in.")
@click.option('--scenario', required=False, help="The scenario to run.")
@click.option('--save', is_flag=True, help="Save this as the default zone and test-setting")
@click.pass_context
@CommandCategory("Validating")
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
            tools.system_exit({'code':3,'message':"No test settings [name_or_id] provided and no default test-setting configured!"})
            return

    if not zone:
        zone = profile.get().default_zone

    if zone == "any":
        proc = os_return("neoload zones", status=False)
        (stdout,strerr) = proc.communicate()
        result = json.loads(stdout)
        availables = list(filter(lambda z: any(filter(lambda c: c['status'] == "AVAILABLE",z['controllers'])) and any(filter(lambda lg: lg['status'] == "AVAILABLE",z['loadgenerators'])),result))
        if len(availables) > 0:
            availables = sorted(availables, key=lambda z: 0 if z['type'] == "STATIC" else 1)
            zone = availables[0]['id']
            print("Because zone is 'any', the zone '{}' ({}) has been automatically selected.".format(zone, availables[0]['name']))
        else:
            tools.system_exit({'code':3,'message':"There are no zones with available load generators and controllers!!!"})
            return

    if not zone:
        tools.system_exit({'code':3,'message':"No --zone provided and no default zone configured!"})
        return

    if not os_run("neoload status", status=False):
        return

    yaml_str = builder_data.convert_builder_to_yaml(builder_data.get())
    data = yaml.safe_load(yaml_str)

    if not scenario:
        scenario = data['scenarios'][0]['name']

    dir = None
    with tempfile.TemporaryDirectory() as tmp:
        dir = tmp
        builder_data.write_to_path(dir, yaml_str)

        if not os_run("neoload test-settings --zone {} --lgs 1 --scenario {} createorpatch {}".format(zone, scenario, name_or_id), status=True):
            return

        if not os_run("neoload project --path {} up".format(dir), status=True):
            return


    if not os_run("neoload run".format(scenario), print_stdout=True):
        print("Test failed.")


    proc = os_return("neoload report --help", status=False)
    (stdout,strerr) = proc.communicate()
    if proc.returncode != 0 or 'Error:' in stdout.decode("UTF-8"):
        print("Test ran, but could not produce final (pretty) report. {}".format("" if strerr is None else strerr))
    else:
        import pkg_resources

        template = pkg_resources.resource_filename(__name__, 'resources/dist/jinja/builtin-console-summary.j2')

        if not os_run("neoload report --template {} --filter '{}' --max-rps 5 cur".format(
                    template,
                    'exclude=events,slas,all_requests,ext_data,controller_points'
                ),
                status=True,
                print_stdout=True):
            return
