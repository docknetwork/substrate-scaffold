#!/usr/bin/env python3

# This script is run on a target machine. It expects to be in the "./run"
# directory. It uses the config from run_config.yml to run a vasaplaten node.

import yaml
import pathlib
import subprocess
import threading
import time
import tempfile


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
    """
    Each element in this class is a named validator function. Validator
    functions are named callables that trow adescriptive exception on
    validation error.
    """

    # List of bootstrap nodes to connect to
    def bootstrap(obj):
        if (
            type(obj) is not list or
            any(type(e) is not str for e in obj)
        ):
            raise Exception("bootstrap must be a list of strings")

    # Private key used in p2p, edsa hex or None
    def p2p_secret_key(obj):
        allowed = "0123456789abcdefghijklmnopqrstuvABCDEFGHIJKLMNOPQRSTUV"
        if obj is None:
            return
        if (
            type(obj) is not str or
            len(obj) != 64 or
            any(c not in allowed for c in obj)
        ):
            raise Exception("p2p_secret_key string must be a 64 character hex "
                            "string or null")

    # name, Chain to run (dev/local/ved)
    def chain(obj):
        options = ["dev", "local", "ved"]
        if obj not in options:
            raise Exception("chain must be one of " + str(options))

    # Private Aura key, recovery phrase or None
    def aura_secret_key(obj):
        valid = type(obj) is str or obj is None
        if not valid:
            raise Exception("aura_secret_key must be either as string or null")

    # Private Grandpa key, recovery phrase or None
    def grandpa_secret_key(obj):
        valid = type(obj) is str or obj is None
        if not valid:
            raise Exception("grandpa_secret_key must be either as string or "
                            "null")

    # Where to store chain state and secret keys. null indicates a temporary
    # directory should be used.
    def chain_storage_base_dir(obj):
        if obj is not None and type(obj) is not str:
            raise Exception("chain_storage_base_dir must be a path or null")

    # port on which to listen for rpc over http
    def http_rpc_port(obj):
        if (
            type(obj) is not int or
            obj <= 0 or
            obj > 65535
        ):
            raise Exception("http_rpc_port must be an integer such that 0 < "
                            "port <= 65535")


def insert_sk(suri, keycode, typeflag, http_rpc_port):
    """
    Add a secret keyphrase to the node keystore.
    """
    subkey_exe = (pathlib.Path(__file__).parent / "subkey").resolve(True)
    PIPE = subprocess.PIPE
    start = time.time()
    timeout = 10
    command = [
        subkey_exe,
        typeflag,
        "insert",
        suri,
        keycode,
        f"http://localhost:{http_rpc_port}"
    ]

    assert typeflag in ["--secp256k1", "--ed25519", "--sr25519"]

    print("setting " + keycode + " key with command", command)

    while time.time() < timeout + start:
        p = subprocess.run(command, stdout=PIPE, stderr=PIPE)
        if p.stderr != b"":
            raise Exception(p.stderr)
        if b"ConnectionRefused" not in p.stdout and not p.stdout == b"":
            raise Exception("unexpected output from subkey\n" + str(p.stdout))
        if p.stdout == b"":
            print("added key to keystore")
            return
    raise Exception("timeout while trying to add " +
                    keycode + " key to keystore")


def vasaplatsen(config: Config):
    with tempfile.TemporaryDirectory() as tmp:
        vasaplatsen_exe = (pathlib.Path(__file__).parent /
                           "vasaplatsen").resolve(True)
        base_storage_path = (
            tmp if config.chain_storage_base_dir is None
            else config.chain_storage_base_dir
        )
        command = [vasaplatsen_exe, "--chain", config.chain]
        command += ["--base-path", base_storage_path]
        command += ["--rpc-port", str(config.http_rpc_port)]
        if len(config.bootstrap) > 0:
            command += ["--bootnodes", ",".join(config.bootstrap)]
        if config.p2p_secret_key is not None:
            command += ["--node-key", config.p2p_secret_key]
        if (
            config.aura_secret_key is not None or
            config.grandpa_secret_key is not None
        ):
            command += ["--validator"]

        print("starting vasaplatsen with command", command)
        child = threading.Thread(target=lambda: (subprocess.run(command)))
        child.start()
        if config.aura_secret_key is not None:
            insert_sk(config.aura_secret_key, "aura",
                      "--sr25519", config.http_rpc_port)
        if config.grandpa_secret_key is not None:
            insert_sk(config.grandpa_secret_key, "gran",
                      "--ed25519", config.http_rpc_port)
        child.join()


if __name__ == "__main__":
    rundir = pathlib.Path(__file__).parent
    rawconf = yaml.safe_load(open(rundir / "run_config.yml"))
    config = Config(rawconf)
    vasaplatsen(config)
