from compose_lib import common
import os

from collections import OrderedDict
from ruamel.yaml.comments import CommentedMap as ordereddict

__profile_config_file = os.path.join(common.__config_dir, "profile.yaml")

def reset():
    global __profile_data_singleton
    __profile_data_singleton = None
    if os.path.exists(__profile_config_file):
        os.remove(__profile_config_file)

def get(throw=True):
    global __profile_data_singleton
    if __profile_data_singleton is None:
        __profile_data_singleton = init()
    return __profile_data_singleton


def init():
    global __profile_data_singleton
    __profile_data_singleton = ProfileData()
    ProfileData.config_file = __profile_config_file
    return __profile_data_singleton

class ProfileData(common.StorableConfig):
    config_file = None

    def __init__(self):
        super(ProfileData, self).__init__()
        self.default_zone = None
        self.default_test_setting = None

    def set_default_zone(self, zone):
        self.default_zone = zone
        return self

    def set_default_test_setting(self, zone):
        self.default_test_setting = zone
        return self

    @classmethod
    def to_yaml(cls,dumper,self):
        #logging.debug(cls.yaml_flow_style)
        data = common.remove_empty(ordereddict(self.__dict__))

        return dumper.represent_data(data)




__profile_data_singleton = common.__load_data(__profile_config_file)
