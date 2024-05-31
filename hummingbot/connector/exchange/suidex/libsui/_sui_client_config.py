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


load_dotenv()

network = "localnet"

prvkey_key = f"{network.upper()}_ADDR1_PRVKEY"
rpc_port = 44342 if network == "testnet" else 44340

user_config = {
    "rpc_url": f"http://0.0.0.0:{rpc_port}",
    "prv_keys": [os.getenv(prvkey_key)],
}
if not any(user_config["prv_keys"]):
    raise RuntimeError(f"can't find {prvkey_key} in .env ")

logger().debug(f"user_config: {user_config!r}")

cfg = SuiConfig.user_config(**user_config)
logger().info(f"CONFIGURATION: {cfg.rpc_url}")

logger().info(f"The address used is : {cfg.active_address}")
client = SyncClient(cfg)
