# -*- coding: utf8 -*-
"""
AWS Connection handler
"""

import importlib
from copy import deepcopy
from json import dumps

class AWSConn(object):
    """Helper object for AWS connector singleton"""
    __cache = {}

    def __init__(self, identity, instavpn_id = None):
        self.identity = identity
        self.instavpn_id = instavpn_id

    def _from_cache(self, service):
        key = self._serialize(self.identity)

        if not self.__cache.get(key, {}):
            self.__cache[key] = {}
            return None

        return self.__cache[key].get(service, None)

    def _build_connection(self, service):

        if self.identity.get("role_arn", False):
            user_identity = deepcopy(self.identity)
            del user_identity["role_arn"]

            conn = AWSConn(user_identity, self.instavpn_id)
            role_cred = conn("sts").assume_role(self.identity["role_arn"], self.instavpn_id).credentials

            user_identity["cred"].update({
                "access": role_cred.access_key,
                "secret": role_cred.secret_key,
                "session": role_cred.session_token
            })

            new_conn = AWSConn(user_identity, self.instavpn_id)
            return new_conn(service)

        module = importlib.import_module("boto.%s" % service)

        if self.identity["cred"]["access"]:
            return module.connect_to_region(
                self.identity["region"],
                aws_access_key_id       = self.identity["cred"]["access"],
                aws_secret_access_key   = self.identity["cred"]["secret"],
                security_token          = self.identity["cred"].get('session', None)
            )
        else:
            return module.connect_to_region(self.identity["region"])

    def __call__(self, service):
        conn = self._from_cache(service)
        if conn:
            return conn

        key = self._serialize(self.identity)
        conn = self._build_connection(service)
        self.__cache[key][service] = conn

        return conn

    @staticmethod
    def _serialize(identity):
        return dumps(identity)
