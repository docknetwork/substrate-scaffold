#!/usr/bin/env python3

# This script is run on a target machine. It expects to be in the "./run"
# directory. It uses the config from run_config.yml to run a vasaplaten node.

from typing import Any, Callable
import yaml
import pathlib
import subprocess
import shlex
from inspect import cleandoc


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
            r = inner_validate(element)
            assert r is None, """
            Validation functions should not return values. Perhaps you wrote
            "islistof(str)" but meant "islistof(istype(str))"
            """
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


class Config(Validate):
    # List of bootstrap nodes to connect to
    bootstrap = islistof(istype(str))
    # Private key, let them provide one (or we create one for them if none)
    node_key = istype(str)
    # name, Chain to run (dev/main)
    chain = isoneof_literal("dev", "local")
    # 
    # p2p_key = None


def script(contents):
    """
    Run contents in interpreter indicated by shebang on first line, indentation
    is cleaned up using magic (inspect.cleandoc) before running the script.
    """
    dedented = cleandoc(contents)
    assert dedented.startswith("#!"), "shebang required"
    interpreter = dedented.splitlines()[0][2:]
    subprocess.run(shlex.split(interpreter), input=dedented, encoding="utf8")


def vasaplatsen(config: Config):
    exe = pathlib.Path(__file__).parent / "vasaplatsen"
    command = [exe, "--chain", config.chain]
    if len(config.bootstrap) > 0:
        command += ["--bootnodes", ",".join(config.bootstrap)]
    subprocess.run(command)


if __name__ == "__main__":
    rundir = pathlib.Path(__file__).parent
    rawconf = yaml.safe_load(open(rundir / "run_config.yml"))
    config = Config(rawconf)
    vasaplatsen(config)
