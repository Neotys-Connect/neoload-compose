import appdirs
import os
import jsonpickle
import logging

from neoload.neoload_cli_lib import tools
import subprocess

__conf_name = "neoload-compose"
__version = "1.0"
__author = "neotys"
__config_dir = appdirs.user_data_dir(__conf_name, __author, __version)

class StorableConfig:

    def __init__(self):
        pass

    def save_to_file(self, config_file):
        dir = os.path.abspath(os.path.join(config_file, os.pardir))
        os.makedirs(dir, exist_ok=True)
        with open(config_file, "w") as stream:
            stream.write(jsonpickle.encode(self))
        return self

    def save(self):
        self.save_to_file(type(self).config_file)

    def __str__(self):
        jsonpickle.set_encoder_options('simplejson', sort_keys=True, indent=4)
        jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
        return jsonpickle.encode(self)

def __load_data(config_file):
    if os.path.exists(config_file):
        with open(config_file, "r") as stream:
            try:
                ret = jsonpickle.decode(stream.read())
                type(ret).config_file = config_file
                return ret
            except Exception:
                logging.warning("Could not load from file {}".format(config_file))

    return None

def remove_empty(od):
    rems = []
    for key in od.keys():
        if od[key] is None: rems.append(key)
    for key in rems:
        del od[key]
    return od

def os_return(command, status=False, connect_stdout=True):
    if status:
        print("Running '{}'".format(command))

    actual_command = parse_command(command)

    if connect_stdout:
        p = subprocess.Popen(actual_command, stdout=subprocess.PIPE)
        p.wait()
    else:
        p = subprocess.Popen(actual_command)
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
            subprocess.run(parse_command(command), check = True)

        return True
    except subprocess.CalledProcessError as err:
        tools.system_exit({'code':err.returncode,'message':"{}".format(err)})
        return False

def parse_command(command):
    actual_command = []
    parts = command.split()

    combine = False
    for part in parts:
        if combine:
            actual_command[-1] += " " + part
        else:
            if part.startswith("\"") or part.startswith("'"):
                combine = True

            actual_command.append(part)

        if part.endswith("\"") or part.endswith("'"):
            combine = False

    final_parts = []
    for p in actual_command:
        part = "{}".format(p)
        if part.startswith("\"") or part.startswith("'"):
            part = part[1:]
        if part.endswith("\"") or part.endswith("'"):
            part = part[:-1]
        final_parts.append(part)

    return final_parts

def find_nlg_app():
    return "/Applications/NeoLoad 7.6/bin/NeoLoadGUI.app/Contents/MacOS/NeoLoad"
