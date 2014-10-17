# -*- coding: utf-8 -*-
"""


"""
from boto.exception import EC2ResponseError
from time import sleep
from json import dumps

from .ui import show
from .io import load_tpl

def build_world(session):
    show.output("Building infrastructures in AWS")

    session["stacks"] = {}

    cfn_eip(session)
    cfn_main(session)

    post_conf(session)

    show.output("VPN created,", "and the supplied Route Table (if any), has been modified "
        "to route traffic via the VPN.")

    show.output("To destroy the VPN,", "delete both CloudFormation Stacks on each sides. All resources "
        "allocated by InstaVPN, except for Route Table entry, will be cleaned up automatically.")

def cfn_eip(session):
    """Allocates EIP and feed them back to params"""

    show.unless_quiet("Creating CFN stack", "to allocate EIP. Should be done in a minute.")

    def _allocate(side, MySide):
        conn_cfn = session["conn"][side]("cloudformation")

        # create_stack does not return the stack
        ret = conn_cfn.create_stack(
            _stack_name(session, side),
            template_body = dumps(load_tpl("eip.json")),
            parameters = [("MySide", MySide)],
            tags = session["tags"]
        )

        # Store stack information to session["stacks"]
        while True:
            try:
                session["stacks"][side] = conn_cfn.describe_stacks(ret)[0]
                break
            except:  sleep(1) # TODO: filter specific error

    _allocate("client", "Client")
    _allocate("server", "Server")
    _wait_cfn(session, interval = 3)

    # Revoer EIP
    for side in ("client", "server"):
        session["params"] += [(o.key, o.value) for o in session["stacks"][side].outputs]

def cfn_main(session):

    show.unless_quiet("Updating CFN Stack", "to bring up the VPN, which usually takes a few minutes.")

    def _do(side, MySide):
        conn_cfn = session["conn"][side]("cloudformation")

        conn_cfn.update_stack(
            _stack_name(session, side),
            template_body = dumps(load_tpl("main.json")),
            parameters = session["params"] + [("MySide", MySide)],
        )

    _do("client", "Client")
    _do("server", "Server")
    _wait_cfn(session, interval=10)

def post_conf(session):
    show.unless_quiet("CloudFormation stack created", "running post-config")

    _pc_server_sg(session)
    _pc_client_sg(session)
    _pc_client_rtb(session)

def _pc_server_sg(session):
    show.verbose(msg="Cleaning up default Server egress rules")

    conn_ec2 = session["conn"]["server"]("ec2")
    sg_id = _from_cfn_output("ServerSGId", Stack=session["stacks"]["server"])
    sg  = conn_ec2.get_all_security_groups(group_ids=[sg_id])[0]

    for rule in sg.rules_egress:
        conn_ec2.revoke_security_group_egress(
            group_id    = sg_id,
            ip_protocol = rule.ip_protocol,
            from_port   = rule.from_port,
            to_port     = rule.to_port,
            cidr_ip     = rule.grants[0]
        )

    for dest in session["config"]["server"]["res"]["servers_allowed"]:
        show.verbose(msg="Granting access to %s:%s:%s" % (dest["proto"], dest["ip"], dest["port"]))
        conn_ec2.authorize_security_group_egress(
            group_id = sg_id,
            ip_protocol = dest["proto"] if dest["proto"] != 'all' else "-1",
            from_port = 0 if 'all' == dest["port"] else int(dest["port"]),
            to_port = 65535 if 'all' == dest["port"] else int(dest["port"]),
            cidr_ip = "%s/32" % dest["ip"]
        )

def _pc_client_sg(session):
    show.verbose("Setting up access control with Server Security Groups")

    client_res = session["config"]["client"]["res"]
    conn_vpc = session["conn"]["client"]("vpc")
    subnet = conn_vpc.get_all_subnets([client_res["subnet_id"]])[0]
    vpc = conn_vpc.get_all_vpcs([subnet.vpc_id])[0]

    sg_id = _from_cfn_output("ClientSGId", Stack=session["stacks"]["client"])
    sg = conn_vpc.get_all_security_groups(group_ids=[sg_id])[0]

    sg.authorize(
        ip_protocol = -1,
        cidr_ip = vpc.cidr_block
    )

def _pc_client_rtb(session):
    """There is either no conflict, or only full replacements in rtb routes,
    which is enforced by rule_60_rtb_route_compatible.
    """

    rtb_id = session["config"]["client"]["res"]["route_table_id"]
    if rtb_id is None: return True

    show.verbose(msg="Changing client Route Table")

    conn = session["conn"]["client"]

    dest_cidrs = session["config"]["server"]["ipsec"]["subnets"]
    client_instnace_id = _from_cfn_output("ClientInstanceId", Stack=session["stacks"]["client"])

    rtb = conn("vpc").get_all_route_tables([rtb_id])[0]

    for route in rtb.routes:
        if route.destination_cidr_block in dest_cidrs:
            show.verbose(msg="Removing route to %s" % route.destination_cidr_block)
            conn("vpc").delete_route(rtb.id, route.destination_cidr_block)

    for cidr in dest_cidrs:
        show.verbose(msg="Creating route to %s" % cidr)
        conn("vpc").create_route(rtb.id, cidr, instance_id = client_instnace_id)

def _from_cfn_output(key, Stack=None, outputs=None):

    if outputs is None and Stack is not None:
        outputs = Stack.outputs

    filtered = [o.value for o in outputs if key == o.key]
    return filtered[0]

def _wait_cfn(session, interval = 5):
    """Wait and block until all stacks are created"""

    state_ok = ('CREATE_COMPLETE', 'UPDATE_COMPLETE', 'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS')
    state_keep_waiting = ('CREATE_IN_PROGRESS', 'UPDATE_IN_PROGRESS')

    ok_s, ok_c = False, False

    stacks = session["stacks"]
    okay = {k : False for k in stacks}

    show.verbose(msg="Waiting for AWS Cloud Formation")

    while not all(okay.values()):

        for k, stack in stacks.iteritems():
            if okay[k]: continue # done already

            stack.update()

            if stack.stack_status in state_ok: okay[k] = True
            elif stack.stack_status in state_keep_waiting: pass
            else:
                for victim in stacks:
                    if victim != stack:
                        try:
                            victim.delete()
                        except: pass
                raise Exception("Stack (%s) failed, may require manual cleanup." % stack.stack_name)

        sleep(interval)

def _stack_name(session, side):
    """Stack name for (session, side)"""
    return "instavpn-%s-%s" % (session["tags"]["instavpn"], side)
