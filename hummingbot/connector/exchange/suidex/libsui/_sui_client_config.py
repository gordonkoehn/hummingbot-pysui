# The underlying configuration class
import logging
import os

from dotenv import load_dotenv
from pysui import SuiConfig, SyncClient
from pysui.abstracts.client_keypair import SignatureScheme

_logger = None


def logger():
    global _logger
    if _logger is None:
        _logger = logging.getLogger()
    return _logger


_inited = None


def _init():
    global _inited
    if not _inited:
        load_dotenv()
        _inited = True


_init()  # TODO: this should not be done at import time; find Hummingbot & py.test lifecycle event to hook into so and call this at the right time


network = os.environ.get("SUIDEX_NETWORK", "localnet")

prvkey_key = f"{network.upper()}_ADDR1_PRVKEY"


RPC_PORT = {
    "testnet": 44342,
    "localnet": 44340,
}
if network not in RPC_PORT:
    raise ValueError(f"can't find RPC_PORT for {network=}")


RPC_URL = {
    "testnet": "https://rpc.testnet.sui.io:443",
    # "testnet": f"http://0.0.0.0:{rpc_port}",
    "localnet": f"http://0.0.0.0:{RPC_PORT[network]}",
}
if network not in RPC_URL:
    raise ValueError(f"can't find RPC_URL for {network=}")

user_config = {
    "rpc_url": RPC_URL[network],
    "prv_keys": [os.getenv(prvkey_key)],
}
if not any(user_config["prv_keys"]):
    raise RuntimeError(f"can't find {prvkey_key} in .env ")

logger().debug(f"user_config: {user_config!r}")

cfg = SuiConfig.user_config(**user_config)
logger().info(f"CONFIGURATION: {cfg.rpc_url}")

logger().info(f"The address used is : {cfg.active_address}")
client = SyncClient(cfg)
