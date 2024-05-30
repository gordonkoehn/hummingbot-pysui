"""test helper code"""

import unittest


class DexTestCase(unittest.TestCase):
    @classmethod
    def setUpPairs(cls, base_asset: str, quote_asset: str) -> None:
        cls.base_asset = base_asset
        cls.quote_asset = quote_asset
        cls.trading_pair = f"{cls.base_asset}-{cls.quote_asset}"
        cls.hb_trading_pair = f"{cls.base_asset}-{cls.quote_asset}"
        cls.ex_trading_pair = f"{cls.base_asset}{cls.quote_asset}"
