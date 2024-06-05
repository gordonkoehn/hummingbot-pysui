"""Provide a python interface to the Sui Deepbook"""

import collections.abc
import json
import logging
import os

from typing import Any, Optional, Tuple

from dotenv import load_dotenv

import pysui
import pysui.sui.sui_txn


ONE_SUI = 10**9

"""'accounting' currency for calculations; outside of Sui, this is often called the "base currency".

Note: 'base currency' is **DIFFERENT** than 'BaseAsset' -- often, it is the
opposite: if one accounts for assets and taxes in terms of fiat / US dollars,
then one is interested in numbers with 'QuoteAsset' of realUSDC.

"""
ASSET_ACCOUNTING = "realusdc::REALUSDC"
ASSET_SUI = "sui::SUI"

TYPE_SUI = "0x2::sui::SUI"

ASSET_QUOTE = ASSET_ACCOUNTING
ASSET_BASE = ASSET_SUI



__all__ = [
    "ASSET_ACCOUNTING",
    "ASSET_QUOTE",
    "ASSET_BASE",
    "ASSET_SUI",
    "NETS",
    "RPC_PORT",
    "RPC_URL",
    "ONE_SUI",
    "ensure_init",
    "execute_and_handle_result",
    "init",
    "logger",
]


_logger = None


NETS = ["localnet", "testnet", "mainnet"]

RPC_PORT = {
    "testnet": 44342,
    "localnet": 44340,
}

RPC_URL = {net: f"https://rpc.{net}.sui.io:443" for net in NETS if net != "localnet"}
RPC_URL["localnet"] = f"http://0.0.0.0:{RPC_PORT['localnet']}",


_NETWORK = None
_PRVKEY = None
_USER_CONFIG = None
_CFG = None
_CLIENT = None


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
        logger()

        global _NETWORK
        _NETWORK = os.environ.get("SUIDEX_NETWORK", "localnet")
        if _NETWORK not in RPC_PORT:
            raise ValueError(f"can't find RPC_PORT for {network=}")

        global _PRVKEY
        _PRVKEY_KEY = f"{_NETWORK.upper()}_ADDR1_PRVKEY"
        _PRVKEY = os.environ.get(_PRVKEY_KEY, None)
        if _PRVKEY is None:
            raise RuntimeError(f"can't find {prvkey_key} in .env")

        RPC_URL["localnet"] = f"http://0.0.0.0:{RPC_PORT[_NETWORK]}"

        if _NETWORK not in RPC_URL:
            raise ValueError(f"can't find RPC_URL for {_NETWORK=}")

        global CFG, CLIENT
        CFG, CLIENT = _get_cfg_and_client(_NETWORK, _PRVKEY, RPC_URL[_NETWORK])
        _inited = _NETWORK, _CFG, _CLIENT
    return _inited


def _user_config_cleaned(v):
    _truncpriv = lambda s: s[:15] + "...redacted" if s.startswith("suiprivk") else s
    if isinstance(v, collections.abc.Sequence):
        if isinstance(v, str):
            return _truncpriv(v)
        elif isinstance(v, list):
            return [_truncpriv(el) for el in v]
        elif isinstance(v, tuple):
            return tuple(_truncpriv(el) for el in v)
        else:
            return (_truncpriv(el) for el in v)


def _get_cfg_and_client(network, prvkey, rpc_url) -> Tuple[pysui.SuiConfig, pysui.SyncClient]:
    """returns pysui.SuiConfig and pysui.SyncClient

    Example:

    >>> cfg, client = get_cfg_and_client()
    """

    global _USER_CONFIG
    _USER_CONFIG = {
        "rpc_url": rpc_url,
        "prv_keys": [prvkey],
    }

    user_config_clean = {k: _user_config_cleaned(v) for (k, v) in sorted(_USER_CONFIG.items())}
    logger().debug(f"user_config: {user_config_clean!r}")

    global _CFG
    _CFG = pysui.SuiConfig.user_config(**_USER_CONFIG)
    logger().info(f"CONFIGURATION: {_CFG.rpc_url}")

    global _CLIENT
    logger().info(f"The chain address being used is: {_CFG.active_address}")
    _CLIENT = pysui.SyncClient(_CFG)

    return _CFG, _CLIENT


def ensure_init():
    """safe to call multiple times"""
    if _inited is None:
        _init()
    return _inited


init = ensure_init


def _teardown():
    """only for use in unit tests"""
    global _NETWORK, _PRVKEY, _USER_CONFIG, _CFG, _CLIENT
    _NETWORK = None
    _PRVKEY = None
    _USER_CONFIG = None
    _CFG = None
    _CLIENT = None
    del RPC_URL["localnet"]


