import sys
import click

from compose_lib import builder_data, profile
from commands import config
import tempfile
import subprocess
import yaml
import json

from neoload.neoload_cli_lib import tools

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
            raise ValueError("There are no zones with available load generators and controllers!!!")

    if not zone:
        raise ValueError("No --zone provided and no default zone configured!")

    os_run("neoload status", status=False)

    yaml_str = builder_data.convert_builder_to_yaml(builder_data.get())
    data = yaml.safe_load(yaml_str)

    if not scenario:
        scenario = data['scenarios'][0]['name']

    dir = None
    with tempfile.TemporaryDirectory() as tmp:
        dir = tmp
        builder_data.write_to_path(dir, yaml_str)

        os_run("neoload test-settings --zone {} --lgs 1 --scenario {} createorpatch {}".format(zone, scenario, name_or_id), status=True)

        os_run("neoload project --path {} up".format(dir), status=True)


    os_run("neoload run".format(scenario), print_stdout=True)


    proc = os_return("neoload report --help", status=False)
    (stdout,strerr) = proc.communicate()
    if proc.returncode != 0 or 'Error:' in stdout.decode("UTF-8"):
        print("Test ran, but could not produce final (pretty) report. {}".format("" if strerr is None else strerr))
    else:
        import pkg_resources

        template = pkg_resources.resource_filename(__name__, 'resources/dist/jinja/builtin-console-summary.j2')
        # add_if_not('summary',default_retrieve)
        # add_if_not('statistics',default_retrieve)
        # add_if_not('slas',default_retrieve)
        # add_if_not('events',default_retrieve)
        # add_if_not('transactions',default_retrieve)
        # add_if_not('all_requests',default_retrieve)
        # add_if_not('ext_data',default_retrieve)
        # add_if_not('controller_points',default_retrieve)

        os_run("neoload report --template {} --filter '{}' --max-rps 5 cur".format(
                    template,
                    'exclude=events,slas,all_requests,ext_data,controller_points'
                ),
                status=True,
                print_stdout=True)


def os_return(command, status=False):
    if status:
        print("Running '{}'".format(command))
    p = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    p.wait()
    return p

def os_run(command, status=False, print_stdout=False):
    if status:
        print("Running '{}'".format(command))
    try:
        if not print_stdout:
            proc = os_return(command, status=False)
            (stdout,strerr) = proc.communicate()
            if proc.returncode != 0:
                tools.system_exit({'code':proc.returncode,'message':"{}".format(strerr)})
                return
        else:
            subprocess.run(command.split(), check = True)
    except subprocess.CalledProcessError as err:
        tools.system_exit({'code':err.returncode,'message':"{}".format(err)})
