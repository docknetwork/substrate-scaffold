#!/usr/bin/env python3

# This script is run on a target machine with "./run" as pwd.
# It uses the config from run_config.yml to run a vasaplaten node.

from typing import Any, Callable
import yaml


def istype(typ) -> Callable[[Any], None]:
    "return a validation function that ensures its arg is typ"
    def validate(obj):
        if not type(obj) is typ:
            raise Exception("{} has wrong type, expected {}, got {}".format(
                obj, typ, type(obj)
            ))
    return validate


def islistof(inner_validate: Callable[[Any], None]) -> Callable[[Any], None]:
    """
    return a validation function that ensures its arg is a list of items that
    pass inner_validate.
    """
    def islistof_validate(obj):
        istype(list)(obj)
        for element in obj:
            inner_validate(element)
    return islistof_validate


def isoneof_literal(*options):
    """
    return a validation function that ensures its arg is one of the allowed
    literal options
    """
    def isoneof_literal_validate(obj):
        if obj not in options:
            raise Exception("Value {} is not valid. Must be one of: {}".format(
                obj, ", ".join(options)
            ))
    return isoneof_literal_validate


class Validate:
    def __init__(self, parsed_toml):
        """
        Take a dict parsed from toml and ensure it contains the correct fields
        with the correct types using own class members as a template
        results in a validated instance of Class with fields populated.
        """

        fields = [f for f in dir(self) if not f.startswith(
            "__") and not f.endswith("__")]

        if rawconf is None:
            raise "Config is empty!"
        for key in rawconf.keys():
            if key not in fields:
                raise Exception("Unexpected key, \"{}\"".format(key))
        for field in fields:
            if field not in rawconf.keys():
                raise Exception("\"{}\" not in config".format(field))

        for field in fields:
            validate_field = getattr(self.__class__, field)
            val = parsed_toml[field]
            validate_field(val)
            setattr(self, field, val)


class CONFIG(Validate):
    # List of bootstrap nodes to connect to
    bootstrap = islistof(istype(str))
    # Private key, let them provide one (or we create one for them if none)
    node_key = istype(str)
    # name, Chain to run (dev/main)
    chain = isoneof_literal("dev", "main")
    # Bool expose RPC
    expose_rpc = istype(bool)


if __name__ == "__main__":
    rawconf = yaml.safe_load(open("run_config.yml"))
    config = CONFIG(rawconf)
    print(config.bootstrap)
    print(config.chain)
    print(config.expose_rpc)
    print(config.node_key)
