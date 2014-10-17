# -*- coding: utf-8 -*-

import json
from os.path import realpath, dirname

__root_path = dirname(dirname(realpath(__file__)))

def load_config(config_name):
    """ Load json config file from /conf/ """
    conf_path = "%s/conf/" % __root_path
    return load_json("%s%s" % (conf_path, config_name))

def load_tpl(tpl_name):
    tpl_path = "%s/cfn-tpl/" % __root_path
    return load_json("%s%s" % (tpl_path, tpl_name))

def load_json(filename):
    """ Load json from user-supplied filename

        Raises exception if the file is unaccessible or malformatted
    """
    if type(filename) is str:
        with open(filename) as fp:
            return json.load(fp)

    return json.load(filename)

