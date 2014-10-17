# -*- coding: utf-8 -*-

import unittest
from lib.checker import *

class TestChecker(unittest.TestCase):
    def test_rule_60_all_server_routable(self):
        """"""

        def session(subnets, server_ips):
            svr = {
                "res": {"servers_allowed": [
                    {'ip':ip} for ip in server_ips
                ]},
                "ipsec": {"subnets": subnets}
            }
            return {"config": {"server": svr}}

        fp = rule_60_all_server_routable

        self.assertTrue(fp(session(
            ['10.0.0.0/8'],
            ['10.0.0.0', '10.255.254.255']
        )))

        self.assertTrue(fp(session(
            ['10.0.0.0/8', '172.16/12'],
            ['10.0.0.0', '10.255.254.255', '172.19.20.20']
        )))

        self.assertRaisesRegexp(
            Exception, "Unreachable.*172\.19\.20\.20", fp,
            session(
                ['10.0.0.0/8'],
                ['10.0.0.0', '10.255.254.255', '172.19.20.20']
            ))
