# -*- coding: utf8 -*-

"""
InstaVPN - Instance-based VPN builder for AWS VPC.

Usage:
  instavpn.py [-v | -q] [-c] -i  [-o <CONFIG>]
  instavpn.py [-v | -q] [-c] -j <CONFIG>
  instavpn.py -h | -V

Options:
  -c --commit   Commit change and build stack without prompt
  -h --help     Show this screen.
  -i --interactive  Interactive UI.
  -j --json     Load config from json file.
  -o --output   Save config as json.
  -q --quiet    Quiet mode.
  -v --verbose  Verbose output.
  -V --version  Show version.
"""

from docopt import docopt
arg = docopt(__doc__, version="InstaVPN 0.1")

import sys
from json import dump, dumps
from termcolor import colored

from lib.io import load_json
from lib.ui import show, ask
from lib.config import ask_config
from lib.checker import chk_session
from lib.actuator import build_world

def build_config(arg):
    if arg["--interactive"]:
        return ask_config()
    elif arg["--json"]:
        return load_json(sys.stdin) if '-' == arg["<CONFIG>"] \
            else load_json(arg["<CONFIG>"])

    return None

def instavpn():
    """Main entry point"""

    if arg["--verbose"]:
        show.set_verbosity(show.VERBOSE)
    elif arg["--quiet"]:
        show.set_verbosity(show.QUIET)

    # Load Config
    config = None
    try:
        config = build_config(arg)
    except IOError as e:
        show.error('IOError:', "Can't read from `%s`." % arg["<CONFIG>"])
        sys.exit(1)
    except ValueError as e:
        show.error('ValueError:', "Config files should be valid json.")
        sys.exit(1)

    # Display and Save config files
    # Keep this block before chkconfig() so that only the clean config file is saved.
    show.output("Config: ", dumps(config))
    if arg["--output"]:
        try:
            with open(arg["<CONFIG>"], "w") as fp:
                dump(config, fp, indent=4)
            show.output("Saved", "to `%s`" % arg["<CONFIG>"])
        except IOError:
            show.error("Can't save to %s." % arg["<CONFIG>"])

    # `params` and `tags` are built later in `chk_session()` call, where related
    # entries in `config[*]` should also follow AWS convention to use CamelCase,
    # instead of snake_case.
    global session
    session = {
        "config": config,
        "conn": {},
    }

    # Condition and Test Config
    if not chk_session(session):
        show.error("Job terminated", "due to failed config check(s).")
        sys.exit(1)

    # Final check & go
    should_build_vpn = 'y' if arg["--commit"] else ask.yn("Build VPN ?", default='y')
    if 'y' == should_build_vpn.lower():
        build_world(session)

    return

if "__main__" == __name__:
    try:
        instavpn()
    except KeyboardInterrupt:
        show.error("\nJob Cancelled")

