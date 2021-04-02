import appdirs
import os
import jsonpickle
import logging
import colorama

from neoload.neoload_cli_lib import tools,displayer
import subprocess
import asyncio
from datetime import datetime
import html

import os
from importlib_resources import files


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


__is_debug = False
def set_debug(debug_on=True):
    global __is_debug
    __is_debug = debug_on


def get_debug():
    global __is_debug
    return __is_debug


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

def os_run(command, status=False, print_stdout=False, print_line_check=None):
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
            #subprocess.run(parse_command(command), check = True)
            print(colorama.Style.RESET_ALL)

            asyncio.get_event_loop().run_until_complete(run_async(command, print_line_check))

            print(colorama.Style.RESET_ALL)

        return True
    except subprocess.CalledProcessError as err:
        tools.system_exit({'code':err.returncode,'message':"{}".format(err)})
        return False

async def run_async(cmd, print_line_check=None):
    env = os.environ
    env['PYTHONUNBUFFERED'] = "1"
    p = await asyncio.create_subprocess_shell(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if print_line_check is None: print_line_check = lambda x: True
    async for is_out, line in merge(decorate_with(p.stdout, True),
                                    decorate_with(p.stderr, False)):
        if is_out:
            if print_line_check(line.decode('UTF-8').strip()):
                c_print(line.decode('UTF-8').strip(), flush=True)
        else:
            c_print('<text color="Fore.RED">{}</text>'.format(line.decode().strip()), flush=True)

def c_print(*args, flush=True):
    final = "".join(*args)

    final = displayer.colorize_text(final)

    print(final)


async def decorate_with(it, prefix):
    async for item in it:
        yield prefix, item

async def merge(*iterables):
    iter_next = {it.__aiter__(): None for it in iterables}
    while iter_next:
        for it, it_next in iter_next.items():
            if it_next is None:
                fut = asyncio.ensure_future(it.__anext__())
                fut._orig_iter = it
                iter_next[it] = fut
        done, _ = await asyncio.wait(iter_next.values(),
                                     return_when=asyncio.FIRST_COMPLETED)
        for fut in done:
            iter_next[fut._orig_iter] = None
            try:
                ret = fut.result()
            except StopAsyncIteration:
                del iter_next[fut._orig_iter]
                continue
            yield ret

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

def get_resource_as_string(relative_path):
    """Load a textual resource file."""
    try:
        import importlib.resources as pkg_resources
    except ImportError:
        # Try backported to PY<37 `importlib_resources`.
        import importlib_resources as pkg_resources

    path = relative_path.split(os.path.sep)
    namespace = ".".join(path[:-1])
    file = path[-1]
    logging.debug({'path':path,'namespace':namespace,'file':file})
    return pkg_resources.read_text(namespace, file)
