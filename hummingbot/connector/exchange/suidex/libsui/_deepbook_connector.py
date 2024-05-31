"""Implementing the pysui connection to the Deep Book"""

import datetime
import json
import numpy as np
import os
from pprint import pprint

from dotenv import load_dotenv

# from numpy.random import PCG64, Generator
from pysui import handle_result
from pysui.sui.sui_builders.get_builders import GetObjectsOwnedByAddress
from pysui.sui.sui_txn import SyncTransaction

# from pysui.sui.sui_types.address import SuiAddress
from pysui.sui.sui_types.scalars import ObjectID, SuiBoolean, SuiU8, SuiU64

from hummingbot.connector.exchange.suidex.libsui._interface import cfg, client

load_dotenv()

########################
# Paramaters to be set
network = "localnet"
# account cap / account cap (= key to account) of the user
account_cap = "0x9d4c904c0e51d9e09cbba1f24626060e9eee6460d4430b3539d43a2578c9ff07"  # noqa: mock

##
amount_to_deposit = 10**9 * 10  # 10 SUI
price = 10**9 * 1.5  # 1.5 SUI per REALUSDC
quantity = 1_000_000_000
is_bid = False

########################


class DeepbookConnector:
    def __init__(self, client, cfg):
        self.client = client
        self.cfg = cfg
        self.package_id = os.getenv("TESTNET_PACKAGE_ID") if network == "testnet" else os.getenv("LOCALNET_PACKAGE_ID")
        self.pool_object_id = (
            os.getenv("TESTNET_POOL_OBJECT_ID") if network == "testnet" else os.getenv("LOCALNET_POOL_OBJECT_ID")
        )

        # check that package_id and pool_object_id are set
        if self.package_id is None or self.pool_object_id is None:
            raise ValueError("Package ID or Pool Object ID not set")

    def create_account(self):
        print(f"Package ID: {self.package_id}")

        txn = SyncTransaction(client=client)
        account_cap = txn.move_call(
            target=f"{self.package_id}::clob_v2::create_account",
            arguments=[],
        )
        txn.transfer_objects(
            transfers=[account_cap],
            recipient=self.cfg.active_address,
        )
        tx_result = handle_result(txn.execute(gas_budget="10000000"))
        account_cap = json.loads(tx_result.to_json(indent=4)).get("effects").get("created")[0]["reference"]["objectId"]
        print("created accaount cap: ", account_cap)
        return account_cap

    def deposit_base(self, account_cap=account_cap):  # noqa: mock
        # TODO: add case for sponsoredTransaction
        txn = SyncTransaction(client=client)

        # deposit 30 SUI
        amount = amount_to_deposit

        txn.move_call(
            target=f"{self.package_id}::clob_v2::deposit_base",
            arguments=[
                ObjectID(self.pool_object_id),
                txn.split_coin(coin=txn.gas, amounts=[amount]),
                ObjectID(account_cap),
            ],
            type_arguments=[
                "0x2::sui::SUI",
                f"{self.package_id}::realusdc::REALUSDC",
            ],
        )

        tx_result = handle_result(txn.execute(gas_budget="10000000"))
        print(tx_result.to_json(indent=4))

    def place_limit_order(
        self,
        price=price,
        quantity=quantity,
        is_bid=is_bid,
        account_cap=account_cap,
    ):  # noqa: mock
        # TODO: add case for sponsoredTransaction
        txn = SyncTransaction(client=client)

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
                SuiU64(np.random.randint(low, high + 1, dtype=np.uint64)),
                SuiU64(price),
                SuiU64(quantity),
                SuiU8(0),
                SuiBoolean(is_bid),
                SuiU64(round(int(datetime.datetime.utcnow().timestamp()) * 1000 + 24 * 60 * 60 * 100000000000000)),
                SuiU8(1),
                ObjectID("0x6"),
                ObjectID(account_cap),
            ],
            type_arguments=[
                "0x2::sui::SUI",
                f"{self.package_id}::realusdc::REALUSDC",
            ],
        )
        tx_result = handle_result(txn.execute(gas_budget="10000000"))
        print(tx_result.to_json(indent=4))

    def get_level2_book_status_bid_side(self):
        txn = SyncTransaction(client=client)
        return_value = txn.move_call(
            target=f"{self.package_id}::clob_v2::get_level2_book_status_bid_side",
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
        print(f"price_vec: {price_vec}")
        print(f"depth_vec: {depth_vec}")

    def get_level2_book_status_ask_side(self):
        txn = SyncTransaction(client=client)
        return_value = txn.move_call(
            target=f"{self.package_id}::clob_v2::get_level2_book_status_ask_side",
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
        print(f"price_vec: {price_vec}")
        print(f"depth_vec: {depth_vec}")


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
