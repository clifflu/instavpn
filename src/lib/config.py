# -*- coding: utf8 -*-

"""
Can access to 'config' from session
"""

import re
from termcolor import colored

from .ui import show, ask
from .io import load_config, load_tpl

#
# Public functions
#

def ask_config():
    config = load_config("default_config.json")

    show.heading("Shared Config")
    _ask_client_name(config)
    _ask_instance_type(config)
    _ask_tags(config)

    def _ask_side(config_side):
        _ask_access(config_side)
        _ask_ec2_vpc(config_side)
        _ask_subnets(config_side)

    show.heading("Server (Shared Service) Side")
    _ask_side(config['server'])
    _ask_dest(config['server']['res']['servers_allowed'])

    show.heading("Client (NATed) Side")
    _ask_side(config['client'])
    _ask_route_table(config['client'])

    return config

#
# Internal functions
#

def _ask_client_name(config):
    config["client"]["name"] = ask.until("Client Name: ", "[a-zA-Z0-9\-\_]+")

def _ask_instance_type(config):
    instance_types = load_tpl("main.json")["Parameters"]["InstanceType"]["AllowedValues"]
    suggestions = load_config("instavpn.json")["suggestions"]["instance_type"]

    instance_type = ask.choose(
        "Instance type", suggestions, 2 if len(suggestions) >= 2 else 1,
        list(set(suggestions.keys()).union(set(instance_types)))
    )

    if instance_type in suggestions:
        instance_type = suggestions[instance_type]

    show.verbose('Instance type:', instance_type)

    config['params']['InstanceType'] = instance_type

def _ask_tags(config):
    """Ask about tags in `default_config`, that will be pushed to most resources
    created by this script, including EC2 Instance, ENI (automatically via CFN)
    and EBS (by script)
    """

    if 0 == len(config["tags"]):
        return

    # Update existing keys
    show.unless_quiet(msg="Enter tag values for newly created AWS resources." )

    for k, v in config["tags"].iteritems():
        v = ask.until("Tag `%s`, Value: " % k, ".*", default = v)
        if v is not None:
            config["tags"][k] = v
        else:
            del config["tags"][k]

def _ask_dest(servers_allowed):
    """Destinations to be allowed on Server SG"""
    show.unless_quiet(msg="Enter servers to be accesed from client's network. "
        "Format: [PROTOCOL:]IP[:Port], Example: `tcp:10.42.3.3:3306`. ")

    show.verbose(msg="Protocol: tcp|udp|all, default = tcp; "
        "Port should be numbers, default is all (0-65535)")

    while True:
        groups = list(ask.until(
            "Allow access to: ",
            r'(?:\.|(?:(tcp|udp|all):)?((?:\d{1,3}\.){3}\d{1,3})(?:\:(\d{1,5}))?)',
            return_groups=True))

        if groups[1] is None:
            # single dot
            break

        if groups[0] is None: groups[0] = 'tcp'
        if groups[2] is None: groups[2] = 'all'

        if 'all' == groups[0] and 'all' != groups[2]:
            show.unless_quiet(msg="Illegal input, port must be `all` if proto = `all`")
            continue

        servers_allowed.append(dict(zip(['proto', 'ip', 'port'], groups)))

def _ask_access(config_side):
    # Region
    try:
        regions = load_config("region.json")
        suggestions = load_config("instavpn.json")["suggestions"]["region"]

        show.unless_quiet(msg="AWS Region where InstaVPN should connect to.")
        config_side['identity']['region'] = ask.choose(
            "Region", suggestions, 0,
            list(set(suggestions.keys()).union(set(regions)))
        )
    except IOError:
        pass

    # Credentials
    show.unless_quiet(msg="Answer `y` to connect to AWS with defined crednetials; "
        "`n` for default ones defined in boto config or instance profile.")

    use_custom_cred = ask.until("Use custom credentials [Y/n]: ", "[yYnN]", default='y')
    if 'n' == use_custom_cred.lower():
        # remove all entries under `cred`
        for k in config_side['identity']['cred']:
            config_side['identity']['cred'][k] = None

    else:
        config_side['identity']['cred']['access'] = ask.until("Access Key: ", ".+")
        config_side['identity']['cred']['secret'] = ask.until("Secret Key: ", ".+")

        show.unless_quiet(msg="Input your session token if you acquired your credentials via "
            "STS/IAM Role. Feel free to ignore this column otherwise")
        sesskey = ask.until("Session Token: ", ".+", optional=True)
        config_side['identity']['cred']['session'] = sesskey

    # Role
    show.unless_quiet(msg="Enter Role ARN if you access those resources as an IAM Role. "
        "Leave it empty if you don't use IAM Role")

    role_arn = ask.until("Role ARN: ", "arn:aws:iam::\d{12}:role/.+", optional=True)
    config_side['identity']['role_arn'] = role_arn


def _ask_ec2_vpc(config_side):

    # Subnet

    show.unless_quiet(msg="Enter Subnet ID, eg., subnet-3345678.")
    subnet_id = ask.until("Subnet ID: ", "^subnet-[0-9a-f]{8,}$")
    config_side['res']['subnet_id'] = subnet_id

def _ask_subnets(config_side):
    show.unless_quiet(msg="Enter routable subnet CIDRs, one at a line. Enter a single dot (.) "
        "when done. Example: 10.0.0.0/24. The list will be extended with client subnet CIDR "
        "in a later stage.")

    while True:
        sn = ask.until(
            "Routed CIDR [%d]: " % len(config_side['ipsec']['subnets']),
            r"((\d{1,3}\.){3}\d{1,3}/\d{1,2})\s*|\.$")

        if sn and '.' != sn:
            config_side['ipsec']['subnets'].append(sn)
        else:
            break

def _ask_route_table(config_side):
    show.unless_quiet(msg="Enter route table ID to be modified by InstaVPN. "
        "Client should be responsible to maintain and config that route table. "
        "Example: rtb-12345678. ")

    rt_id = ask.until("Route Table ID:", r"^rtb-[a-z0-9]{8,}$", optional=True)
    config_side["res"]["route_table_id"] = rt_id
