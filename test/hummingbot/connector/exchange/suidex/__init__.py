"""test helper code"""

import logging
import unittest
import warnings

_LOGGING_SQUELCHES = {
    # inspect logging.root.manager.loggerDict to confirm
    "asyncio": logging.WARNING,
    "httpcore.connection": logging.INFO,
    "httpcore.http11": logging.INFO,
    "httpx": logging.WARNING,
    "httpx:_client.py": logging.WARNING,
    "matplotlib.font_manager": logging.WARNING,
    "pysui": logging.WARNING,
    "pysui.config": logging.INFO,
    "pysui.sync_client": logging.INFO,
    "pysui.sync_transaction": logging.INFO,
    "pysui.transaction_builder": logging.INFO,
    "sqlalchemy.dialects.postgresql": logging.INFO,
    # TODO(martin): matplotlib
    # TODO(martin): pandas
}


_inited = None


def _init():
    global _inited
    if not _inited:
        # adjust libraries' logging
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        for logger_name, logger_squelch_level in _LOGGING_SQUELCHES.items():
            logging.getLogger(logger_name).setLevel(logger_squelch_level)
        _inited = True


_init()  # TODO: this should not be done at import time; find Hummingbot & py.test lifecycle event to hook into so and call this at the right time


class DexTestCase(unittest.TestCase):
    @classmethod
    def setUpPairs(cls, base_asset: str, quote_asset: str) -> None:
        cls.base_asset = base_asset
        cls.quote_asset = quote_asset
        cls.trading_pair = f"{cls.base_asset}-{cls.quote_asset}"
        cls.hb_trading_pair = f"{cls.base_asset}-{cls.quote_asset}"
        cls.ex_trading_pair = f"{cls.base_asset}{cls.quote_asset}"
