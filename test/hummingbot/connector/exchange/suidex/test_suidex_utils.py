import unittest

from hummingbot.connector.exchange.suidex import suidex_utils as utils

from tests.hummingbot.connector.exchange.suidex import DexTestCase


class SUIDexUtilTestCases(DexTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        base_asset = "COINALPHA_FIXME"
        quote_asset = "USD_FIXME"
        return cls.setUpPairs(base_asset, quote_asset)

    def test_is_exchange_information_valid(self):
        invalid_info_1 = {
            "status": "BREAK",
            "permissionSets": [["MARGIN"]],
        }

        self.assertFalse(utils.is_exchange_information_valid(invalid_info_1))

        invalid_info_2 = {
            "status": "BREAK",
            "permissionSets": [["SPOT"]],
        }

        self.assertFalse(utils.is_exchange_information_valid(invalid_info_2))

        invalid_info_3 = {
            "status": "TRADING",
            "permissionSets": [["MARGIN"]],
        }

        self.assertFalse(utils.is_exchange_information_valid(invalid_info_3))

        invalid_info_4 = {
            "status": "TRADING",
            "permissionSets": [["SPOT"]],
        }

        self.assertTrue(utils.is_exchange_information_valid(invalid_info_4))
