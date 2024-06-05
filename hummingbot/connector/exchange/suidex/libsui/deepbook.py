"""Implementing the pysui connection to the Deep Book"""

import datetime
import json
import logging
import numpy as np
import os

from pprint import pprint
from typing import Optional

from dotenv import load_dotenv

# from numpy.random import PCG64, Generator
from pysui.sui.sui_builders.get_builders import GetObjectsOwnedByAddress
from pysui.sui.sui_txn import SyncTransaction

# from pysui.sui.sui_types.address import SuiAddress
from pysui.sui.sui_types.scalars import ObjectID, SuiBoolean, SuiU8, SuiU64

import hummingbot.connector.exchange.suidex.libsui as libsui

from hummingbot.logger import HummingbotLogger

########################
# Paramaters to be set

##
amount_to_deposit = 10**9 * 10  # 10 SUI
price = 10**9 * 1.5  # 1.5 SUI per REALUSDC
quantity = 1_000_000_000
is_bid = False
order_id = 136375



_DEEPBOOK = None




class DeepbookConnector:
    _logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(HummingbotLogger.logger_name_for_class(cls))
        return cls._logger

    def __init__(self, client=None, cfg=None, package_id=None, pool_object_id=None, net=None, account_cap=None):
        load_dotenv()

        if not all((client, cfg, net)):
            NETWORK, CFG, CLIENT = libsui.init()
        client = CLIENT if client is None else client
        cfg = CFG if cfg is None else cfg
        net = NETWORK if net is None else net
        package_id_key = f"{net.upper()}_PACKAGE_ID"
        package_id = os.getenv(package_id_key, None) if package_id is None else package_id
        pool_object_id_key = f"{net.upper()}_POOL_OBJECT_ID"
        pool_object_id = os.getenv(pool_object_id_key, None) if pool_object_id is None else pool_object_id
        account_cap_key = f"{net.upper()}_ACCOUNT_CAP"
        account_cap = os.getenv(account_cap_key, account_cap) if account_cap is None else account_cap

        self.client = client
        self.cfg = cfg
        self.account_cap = account_cap
        self.package_id = package_id
        self.pool_object_id = pool_object_id

        if self.account_cap is None:
            self.account_cap = self.get_account_cap(create_if_needed=True)

        # check that package_id and pool_object_id are set
        if self.package_id is None:
            raise ValueError(
                f"DeepbookConnector.__init__(..): package_id cannot be None (check .env::{package_id_key}?)"
            )
        if self.pool_object_id is None:
            raise ValueError(
                f"DeepbookConnector.__init__(..): pool_object_id cannot be None (maybe check .env::{pool_object_id_key}?)"
            )
        if self.account_cap is None:
            self.logger().info(
                f"DeepbookConnector.__init__(..): account_cap is None; many functions require an `account_cap` so self.create_account() should be called first"
            )

    @property
    def active_address(self):
        if self.cfg is None:
            return None
        else:
            return self.cfg.active_address

    def create_account(self):
        """public fun create_account(ctx: &mut TxContext): AccountCap {"""
        # FUTURE: should we refuse to create a new account if self.account_cap is not None?
        self.logger().info(f"Package ID: {self.package_id}")

        txn = SyncTransaction(client=self.client)
        account_cap = txn.move_call(
            target=f"{self.package_id}::clob_v2::create_account",
            arguments=[],
        )
        txn.transfer_objects(
            transfers=[account_cap],
            recipient=self.active_address,
        )
        success, tx_result_json, tx_result = libsui.execute_and_handle_result(txn)
        self.logger().debug(tx_result_json)

        account_cap = tx_result_json.get("effects").get("created")[0]["reference"]["objectId"]
        self.account_cap = account_cap
        self.logger().info(f"created account cap: {account_cap}")
        return account_cap

    def get_account_cap(self, create_if_needed=False):
        account_cap_dicts = libsui.find_objects(self.client, "AccountCap", address_owner=self.active_address)
        account_cap_dict = account_cap_dicts[-1] if account_cap_dicts else {}
        if (account_cap := account_cap_dict.get("objectId", None)) is None:
            if create_if_needed:
                account_cap = self.create_account()
            else:
                raise RuntimeError("No AccountCap object could be found?! (net={self._network}, active_address={self.active_address})")
        return account_cap

    def deposit_base(self):  # noqa: mock
        # TODO: add case for sponsoredTransaction
        txn = SyncTransaction(client=self.client)

        # deposit 30 SUI
        amount = amount_to_deposit

        txn.move_call(
            target=f"{self.package_id}::clob_v2::deposit_base",
            arguments=[
                ObjectID(self.pool_object_id),
                txn.split_coin(coin=txn.gas, amounts=[amount]),
                ObjectID(self.account_cap),
            ],
            type_arguments=[
                "0x2::sui::SUI",
                f"{self.package_id}::realusdc::REALUSDC",
            ],
        )

        tx_result = handle_result(txn.execute(gas_budget="10000000"))
        self.logger().info(tx_result.to_json(indent=4))

    def place_limit_order(
        self,
        price=price,
        quantity=quantity,
        is_bid=is_bid,
    ):  # noqa: mock
        # TODO: add case for sponsoredTransaction
        txn = SyncTransaction(client=self.client)

        # defining range for mock order id
        # Define the lower and upper bounds for the random u64 integers (inclusive)
        low = 0
        high = np.iinfo(np.uint64).max  # Maximum value for uint64

        # sett ask price to
        print(f"Placing {'bid' if is_bid else 'ask'} order with price {price} and quantity {quantity}")

        txn.move_call(
            target=f"{self.package_id}::clob_v2::place_limit_order",
            arguments=[
                ObjectID(self.pool_object_id),
                SuiU64(order_id),
                SuiU64(price),
                SuiU64(quantity),
                SuiU8(0),
                SuiBoolean(is_bid),
                SuiU64(round(int(datetime.datetime.utcnow().timestamp()) * 1000 + 24 * 60 * 60 * 100000000000000)),
                SuiU8(1),
                ObjectID("0x6"),
                ObjectID(self.account_cap),
            ],
            type_arguments=[
                "0x2::sui::SUI",
                f"{self.package_id}::realusdc::REALUSDC",
            ],
        )
        tx_result = handle_result(txn.execute(gas_budget="10000000"))
        self.logger().info(tx_result.to_json(indent=4))

    def get_level2_book_status_bid_side(self, *args, **kwargs):
        return self.get_level2_book_status("bid", *args, **kwargs)

    def get_level2_book_status_ask_side(self, *args, **kwargs):
        return self.get_level2_book_status("ask", *args, **kwargs)

    def get_level2_book_status(self, side):
        txn = SyncTransaction(client=self.client)
        return_value = txn.move_call(
            target=f"{self.package_id}::clob_v2::get_level2_book_status_{side}_side",
            arguments=[
                ObjectID(self.pool_object_id),
                SuiU64(0),
                SuiU64(10**12),
                ObjectID("0x6"),
            ],
            type_arguments=[
                "0x2::sui::SUI",
                f"{self.package_id}::realusdc::REALUSDC",
            ],
        )
        # print(return_value)
        temp = txn.inspect_all()
        # pprint(temp)
        results = temp.results
        # result = handle_result(temp)
        # print(results)

        # Extract raw values (lists containing 0)
        price_vec = results[0]["returnValues"][0][0]
        depth_vec = results[0]["returnValues"][1][0]
        self.logger().debug(f"price_vec: {price_vec}")
        self.logger().debug(f"depth_vec: {depth_vec}")

        return results

    def get_order_status(self, order_id, account_cap=None):
        txn = SyncTransaction(client=self.client)
        return_value = txn.move_call(
            target=f"{self.package_id}::clob_v2::get_order_status",
            arguments=[
                ObjectID(self.pool_object_id),
                SuiU64(order_id),
                ObjectID(self.account_cap),
            ],
            type_arguments=[
                "0x2::sui::SUI",
                f"{self.package_id}::realusdc::REALUSDC",
            ],
        )

        print("=== GET ORDER STATUS ===")
        pprint(txn.inspect_all())

        result = handle_result(txn.inspect_all())
        print(return_value)
        print(result)


def current():
    global _DEEPBOOK
    if _DEEPBOOK is None:
        libsui.init()
        _DEEPBOOK = DeepbookConnector()
    return _DEEPBOOK


if __name__ == "__main__":
    connector = DeepbookConnector(client, cfg)
    # connector.create_account()#
    # print(connector.package_id)
    # print(connector.pool_object_id)
    # connector.deposit_base()
    connector.place_limit_order()
    # connector.place_limit_order()
    # connector.place_limit_order()
    connector.get_level2_book_status_bid_side()
    connector.get_level2_book_status_ask_side()
    connector.get_order_status(order_id, ACCOUNT_CAP)
