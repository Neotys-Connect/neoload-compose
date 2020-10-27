import appdirs
import os
import jsonpickle
import logging

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
