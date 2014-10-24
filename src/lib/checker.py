# -*- coding: utf-8 -*-

"""
Automatic config tests.

Rules should start with rule_, and are executed in alphabetical order.
To minimize namespace conflict, we encourage defining utility functions
under their parents' scope, or into other modules.

Should only access `config` and `conn` under session,
while `tags` and `params` are built accordingly in rule_99.

"""

import random

from iptools import IpRange
from boto.exception import EC2ResponseError
from base64 import urlsafe_b64encode

from .aws_conn import AWSConn
from .ui import show, ask
from .config import load_config

def chk_session(session):
    """Run through all tests; stop after first failure"""
    show.output("Checking config")

    for rule in rules:
        try:
            show.unless_quiet("Checking", rule[0])
            assert rule[1](session)
        except Exception as e:
            show.verbose(msg = "Config check `%s` failed%s%s" % (
                rule[0],
                ", %s" % e if len(str(e)) > 0 else "",
                (": %s" % rule[1].__doc__.split("\n")[0].strip())
                    if rule[1].__doc__ else "."
            ))

            return False

    return True

def cidr_overlaps(cidr1, cidr2):
    ir1, ir2 = IpRange(cidr1), IpRange(cidr2)

    if ir1.startIp < ir2.startIp:
        if ir1.endIp < ir2.startIp:
            return False
    elif ir1.startIp > ir2.endIp:
        return False

    return True

def _create_shared_secret():
    """Creates shared secret with #bits assigned in instavpn.json

    Uses random.SystemRandom.randint, which pulls randomness from /dev/urandom,
    and thus system entropy pool when it's available, then falls back to prng
    if it's empty.
    """

    randint = random.SystemRandom().randint
    bits = load_config("instavpn.json")["shared_secret_bits"]
    return urlsafe_b64encode("".join(chr(randint(0, 255)) for _ in xrange(bits/8)))

# ============================================================================
# 00: Integrity and job serial

def rule_00_config_is_dict(session):
    """config should be a dict"""
    return isinstance(session["config"], dict)

def rule_01_set_job_id(session):
    """Pick instavpn ID as hex string to identify task

    Use randint from random instead of SystemRandom, which is less secure, but
    does not consume system entropy.
    """

    my_id = "".join("%02x" % random.randint(0,255) for _ in xrange(4))

    session["config"]["tags"]["instavpn"] = my_id
    show.output("Instavpn Task ID", "is %s" % my_id)

    return True

# ============================================================================
# 20: Bring up environments and connection

def rule_20_connect(session):
    """Create the `conn` side in session"""

    c, my_id = session["config"], session["config"]["tags"]["instavpn"]

    session["conn"].update({
        "server": AWSConn(c["server"]["identity"], my_id),
        "client": AWSConn(c["client"]["identity"], my_id),
    })

    return True


def rule_20_fill_config_tags_params(session):
    """Fill in session["config"]"""
    session["config"]["tags"]['Service'] = session["config"]["client"]["name"]

    return True


# ============================================================================
# 40: Tests that rely on AWS connection

def rule_40_extend_subnet_cidr(session):
    """Adds subnet CIDR to `subnets` if it's not there"""

    config, conn = session["config"], session["conn"]

    def append_cidr(config_side, conn_vpc):

        cidr = conn_vpc.get_all_subnets([
            config_side["res"]["subnet_id"]
        ])[0].cidr_block

        for user_cidr in config_side["ipsec"]["subnets"]:
            if cidr_overlaps(cidr, user_cidr):
                return

        config_side["ipsec"]["subnets"].append(cidr)

    append_cidr(config["server"], conn["server"]("vpc"))
    append_cidr(config["client"], conn["client"]("vpc"))

    return True

def rule_40_can_create_sg(session):
    """Authorized to create security group"""

    def try_create(session, side):
        res, conn_vpc = session["config"][side]["res"], session["conn"][side]("vpc")
        subnet = conn_vpc.get_all_subnets([res["subnet_id"]])[0]

        try:
            conn_vpc.create_security_group(
                "foo", "bar", vpc_id = subnet.vpc_id, dry_run = True)
        except EC2ResponseError as e:
            if 412 != e.status:
                raise e

    try_create(session, "server")
    try_create(session, "client")

    return True

def rule_40_rtb_and_subnet_in_same_vpc(session):
    """Route table and subnet belongs to the same vpc"""

    conn, conf = session["conn"]["client"], session["config"]["client"]

    if conf["res"]["route_table_id"] is None:
        return True

    main_rtb = None
    subnet = conn("vpc").get_all_subnets([conf["res"]["subnet_id"]])[0]
    rtb = conn("vpc").get_all_route_tables([conf["res"]["route_table_id"]])[0]

    return rtb.vpc_id == subnet.vpc_id

def rule_40_igw_available(session):
    """igw attached to both vpcs"""
    def has_igw(session, side):
        conn_vpc = session["conn"][side]("vpc")
        subnet = conn_vpc.get_all_subnets(
            [session["config"][side]["res"]["subnet_id"]])[0]

        for igw in conn_vpc.get_all_internet_gateways():
            for att in igw.attachments:
                if att.vpc_id == subnet.vpc_id:
                    return True
        return False

    return has_igw(session, "server") and has_igw(session, "client")

# ============================================================================
# 60: Tests with Dependency

def rule_60_rtb_route_compatible(session):
    """No conflict between existing routes and what we will add"""
    # Depends on: rule_40_rtb_same_vpc

    # TODO: iterate all rtb associations
    # if another rule exists for the exact CIDR
        # if pointing to a black hole
            # show message and continue
        # else: error & end
    # elseif for overlapped (but not equal) CIDR:
        # error and end
    # else: pass

    return True

def rule_60_subnet_cidr_conflict(session):
    """Subnet CIDR conflicts"""
    # Depends on: rule_40_extend_subnet_cidr

    config = session["config"]

    pool = []
    cidrs = config["client"]["ipsec"]["subnets"] + config["server"]["ipsec"]["subnets"]

    # todo: rewrite with heap tree ?
    for cidr in cidrs:
        for against in pool:
            if cidr_overlaps(cidr, against):
                raise Exception("Conflict between subnet (%s, %s)" % (cidr, against))
        pool.append(cidr)

    return True

def rule_60_all_server_routable(session):
    """All servers belong to exposed CIDRs from Server"""
    # Depends on: rule_40_extend_subnet_cidr

    conf_server = session["config"]["server"]
    subnets = [IpRange(sn) for sn in conf_server["ipsec"]["subnets"]]

    for server in conf_server["res"]["servers_allowed"]:
        for subnet in subnets:
            if server['ip'] in subnet:
                break
        else:
            raise Exception("Unreachable server %s detected" % server['ip'])
    return True

# ============================================================================
# rule 80: Finally

def rule_80_create_keys_params(session):
    if 'tags' not in session: session['tags'] = {}
    session["tags"].update(session["config"]["tags"])

    if 'params' not in session: session['params'] = []
    session["params"] += [(k,v) for k, v in session["config"]["params"].iteritems()]

    return True

def rule_99_fill_tags_params(session):
    def _params(session, side, prefix):
        conf, conn = session["config"][side], session["conn"][side]

        subnet = conn("vpc").get_all_subnets(conf["res"]["subnet_id"])[0]

        return [
            (prefix + "SharedCIDRs" , " ".join(conf["ipsec"]["subnets"])),
            (prefix + "SubnetId"    , subnet.id),
            (prefix + "VPCId"       , subnet.vpc_id)
        ]

    session["params"] += [
        ("ServerName", "DCS"),
        ("ClientName", session["config"]["tags"]['Service']),
        ("SharedSecret", _create_shared_secret())
    ]

    session["params"] += _params(session, "server", "Server")
    session["params"] += _params(session, "client", "Client")

    return True

# ============================================================================
# List rules

rules = [] # Placeholder for all rules
l = dir()
l.sort()
for fn in l: # Iterate through all rules, sorted
    if fn.startswith('rule_'):
        rules.append((fn, globals()[fn]))
