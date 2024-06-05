"""Implementing the pysui connection to the Deep Book"""

import datetime
import json
import logging
import numpy as np
import os
import random

from decimal import Decimal as D
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

REFERENCE_TAKER_FEE_RATE = 2_500_000
REFERENCE_MAKER_REBATE_RATE = 1_500_000
FEE_AMOUNT_FOR_CREATE_POOL = (
    1 * libsui.ONE_SUI
)  # 1 SUI; clob_v2.move comment is "// 100 SUI" but actually does 1 * 1_000_000_000 == 1 * 10^9 == 1 * ONE_SUI

### DEPRECATED -- use `self.account_cap` on your DeepbookConnector instance instead
### ACCOUNT_CAP = "0x9d4c904c0e51d9e09cbba1f24626060e9eee6460d4430b3539d43a2578c9ff07"  # noqa: mock


EIncorrectPoolOwner = 1
EInvalidFeeRateRebateRate = 2
EInvalidOrderId = 3
EUnauthorizedCancel = 4
EInvalidPrice = 5
EInvalidQuantity = 6
EInsufficientBaseCoin = 7  # Insufficient amount of base coin.
EInsufficientQuoteCoin = 8  # Insufficient amount of quote coin.
EOrderCannotBeFullyFilled = 9
EOrderCannotBeFullyPassive = 10
EInvalidTickPrice = 11
EInvalidUser = 12
ENotEqual = 13
EInvalidRestriction = 14
EInvalidPair = 16
EInvalidFee = 18
EInvalidExpireTimestamp = 19
EInvalidTickSizeMinSize = 20
EInvalidSelfMatchingPreventionArg = 21


_DEEPBOOK = None


# FUTURE(martin): hoist to trade_ids.py or something
def _client_trade_code(msg=None, codelen=8):
    msg = str(datetime.datetime.now().microsecond) if msg is None else msg
    SAFE_ALPHABET_STRING = "234679CDFGHJKMNPRTWXYZ"
    return "".join([random.choice(SAFE_ALPHABET_STRING) for _ in range(codelen)])


def _client_trade_id(msg=None, epoch=10**17):
    """
    >>> 2**64
    18446744073709551616
    >>> dtm.datetime.now().timestamp() * 10**6
        1717283606001368.0
    >>> 10**16
       10000000000000000
    >>> 10**17
      100000000000000000
    """
    return epoch + int(datetime.datetime.now().timestamp())


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
        if self.pool_object_id is None:
            self.pool_object_id = self.get_pool(create_if_needed=True)

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

    def account_balance(self, asset_base=None, asset_quote=None, pool=None, account_cap=None):
        """public fun account_balance<BaseAsset, QuoteAsset>(
        pool: &Pool<BaseAsset, QuoteAsset>,
        account_cap: &AccountCap)
        """
        self.logger().debug(f"account_balance(..): calling...")

        asset_quote = libsui.ASSET_ACCOUNTING if asset_quote is None else asset_quote
        asset_base = libsui.ASSET_SUI if asset_base is None else asset_base
        pool_object_id = self.pool_object_id if pool is None else pool
        account_cap = self.account_cap if account_cap is None else account_cap

        type_base = libsui.TYPE_SUI
        type_quote = f"{self.package_id}::{asset_quote}"

        txn = SyncTransaction(client=self.client)
        result = txn.move_call(
            target=f"{self.package_id}::clob_v2::account_balance",
            arguments=[
                ObjectID(pool_object_id),
                ObjectID(account_cap),
            ],
            type_arguments=[type_base, type_quote],
        )

        success, tx_result_json, tx_result = libsui.execute_and_handle_result(txn)
        self.logger().debug(tx_result_json)

        if success:
            ((base_avail, _), (base_locked, _), (quote_avail, _), (quote_locked, _)) = [a.value for a in result]
            self.logger().info(
                f"account_balance(..): got ({base_avail=}, {base_locked=}, {quote_avail=}, {quote_locked=})"
            )
            return base_avail, base_locked, quote_avail, quote_locked
        else:
            self.logger().error(f"account_balance<..>(..) call failed:\n{tx_result_json}")
            raise RuntimeError(tx_result_json)

    def asks(self, *args, **kwargs):
        """public fun asks<BaseAsset, QuoteAsset>(pool: &Pool<BaseAsset, QuoteAsset>): &CritbitTree<TickLevel> {"""
        raise NotImplementedError()

    def batch_cancel_order(self, *args, **kwargs):
        """public fun batch_cancel_order<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def bids(self, *args, **kwargs):
        """public fun bids<BaseAsset, QuoteAsset>(pool: &Pool<BaseAsset, QuoteAsset>): &CritbitTree<TickLevel> {"""
        raise NotImplementedError()

    def borrow_custodian(self, *args, **kwargs):
        """public fun borrow_custodian<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def borrow_mut_custodian(self, *args, **kwargs):
        """public fun borrow_mut_custodian<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def borrow_mut_pool(self, *args, **kwargs):
        """public fun borrow_mut_pool<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def cancel_all_orders(self, *args, **kwargs):
        """public fun cancel_all_orders<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def cancel_order(self, *args, **kwargs):
        """public fun cancel_order<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def check_balance_invariants_for_account(self, *args, **kwargs):
        """public fun check_balance_invariants_for_account<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def check_empty_tick_level(self, *args, **kwargs):
        """public fun check_empty_tick_level("""
        raise NotImplementedError()

    def check_tick_level(self, *args, **kwargs):
        """public fun check_tick_level("""
        raise NotImplementedError()

    def check_usr_open_orders(self, *args, **kwargs):
        """public fun check_usr_open_orders("""
        raise NotImplementedError()

    def clean_up_expired_orders(self, *args, **kwargs):
        """public fun clean_up_expired_orders<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

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
                raise RuntimeError(
                    "No AccountCap object could be found?! (net={self._network}, active_address={self.active_address})"
                )
        return account_cap

    def create_customized_pool(self, *args, **kwargs):
        """public fun create_customized_pool<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def create_customized_pool_v(self, *args, **kwargs):
        """public fun create_customized_pool_v2<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def create_customized_pool_with_return(self, *args, **kwargs):
        """public fun create_customized_pool_with_return<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def create_pool(
        self,
        asset_base=None,
        asset_quote=None,
        taker_fee_rate=None,
        maker_rebate_rate=None,
        tick_size=None,
        min_size=None,
        creation_fee=None,
    ):
        """public fun create_pool<BaseAsset, QuoteAsset>("""
        asset_quote = libsui.ASSET_ACCOUNTING if asset_quote is None else asset_quote
        asset_base = libsui.ASSET_SUI if asset_base is None else asset_base
        ONE_BASIS_POINT = 10**4
        TICK_SIZE = libsui.ONE_SUI // ONE_BASIS_POINT
        tick_size = TICK_SIZE if tick_size is None else tick_size
        min_size = TICK_SIZE if min_size is None else min_size

        type_base = libsui.TYPE_SUI if asset_base == libsui.ASSET_SUI else f"{self.package_id}::{asset_base}"
        type_quote = f"{self.package_id}::{asset_quote}"

        txn = SyncTransaction(client=self.client)
        creation_fee = txn.split_coin(coin=txn.gas, amounts=[libsui.ONE_SUI])

        returned_pool = txn.move_call(
            target=f"{self.package_id}::clob_v2::create_pool",
            arguments=[
                SuiU64(str(tick_size)),
                SuiU64(str(min_size)),
                #                                                 SuiU64(str(REFERENCE_TAKER_FEE_RATE)),
                #                                                 SuiU64(str(REFERENCE_MAKER_REBATE_RATE)),
                creation_fee,
            ],
            type_arguments=[type_base, type_quote],
        )

        success, tx_result_json, tx_result = libsui.execute_and_handle_result(txn)
        self.logger().debug(tx_result_json)

        changed_objects = tx_result.to_dict()["objectChanges"]
        pool_object_ids = [c.get("objectId", "") for c in changed_objects if "::Pool<" in c.get("objectType", "")]

        if len(pool_object_ids) != 1:
            msg = f"created Pool<{asset_base}, {asset_quote}>: but got no ::Pool<..> in {len(changed_objects)} changed objects ({changed_objects=})"
            self.logger().warning(msg)
            raise RuntimeError(msg)

        pool_object_id = pool_object_ids[0]

        if not pool_object_id:
            msg = f"created Pool<{asset_base}, {asset_quote}>: but got strange ::Pool<..> {pool_object_id=} in {len(changed_objects)} changed objects ({changed_objects=})"
            self.logger().warning(msg)
            raise RuntimeError(msg)

        self.logger().info(f"created Pool<{asset_base}, {asset_quote}>: {pool_object_id}")
        return pool_object_id

    def get_pool(self, asset_base=None, asset_quote=None, create_if_needed=False):
        pool_object_dicts = libsui.find_objects(self.client, "::Pool<", address_owner=self.active_address)
        breakpoint()
        pool_object_id = None
        if pool_object_dicts:
            asset_quote_desired = libsui.ASSET_ACCOUNTING if asset_quote is None else asset_quote
            asset_base_desired = libsui.ASSET_SUI if asset_base is None else asset_base

            def is_desired_pool(o):
                return (asset_base_desired in o["type"]) and (asset_quote_desired in o["type"])

            pool_object_dicts_matching = [o for o in pool_object_dicts if is_desired_pool(o)]
            breakpoint()
            if pool_object_dicts_matching:
                pool_object_id = pool_object_dicts_matching[-1]["objectId"]
        if not pool_object_id:
            if create_if_needed:
                pool_object_id = self.create_pool(asset_base=asset_base, asset_quote=asset_quote)
            else:
                raise RuntimeError(
                    "No Pool object could be found?! (net={self._network}, active_address={self.active_address})"
                )
        return pool_object_id

    def create_pool_with_return(self, *args, **kwargs):
        """public fun create_pool_with_return<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def delete_pool_owner_cap(self, *args, **kwargs):
        """public fun delete_pool_owner_cap(pool_owner_cap: PoolOwnerCap) {"""
        raise NotImplementedError()

    def deposit_base(self, amount_base, asset_quote=None, asset_base=None):  # noqa: mock
        """public fun deposit_base<BaseAsset, QuoteAsset>("""
        return self._deposit("base", amount_base, asset_quote=asset_quote, asset_base=asset_base)

    def deposit_quote(self, amount_quote, asset_quote=None, asset_base=None):  # noqa: mock
        """public fun deposit_quote<BaseAsset, QuoteAsset>("""
        return self._deposit("quote", amount_base, asset_quote=asset_quote, asset_base=asset_base)

    def _deposit(self, base_or_quote, amount, asset_quote=None, asset_base=None):
        assert base_or_quote in [
            "base",
            "quote",
        ], f"base_or_quote argument must be 'base' or 'quote' (was: {base_or_quote=})"
        depositing_quote = base_or_quote == "quote"
        asset_quote = libsui.ASSET_ACCOUNTING if asset_quote is None else asset_quote
        asset_base = libsui.ASSET_SUI if asset_base is None else asset_base
        asset_coin = asset_quote if depositing_quote else asset_base

        pool_object_id = self.pool_object_id  # FUTURE: use asset_quote and ASSET_SUI to look up pool
        account_cap = self.account_cap

        type_base = libsui.TYPE_SUI
        type_quote = f"{self.package_id}::{asset_quote}"

        amount_sui = D(amount) / D(libsui.ONE_SUI)
        self.logger().info(f"deposit_{base_or_quote}(..): depositing {amount_sui} SUI ({amount=}) [{base_or_quote=}]")

        # TODO: add case for sponsoredTransaction
        txn = SyncTransaction(client=self.client)
        ret = txn.move_call(
            target=f"{self.package_id}::clob_v2::deposit_{base_or_quote}",
            arguments=[
                ObjectID(pool_object_id),
                txn.split_coin(coin=txn.gas, amounts=[amount]),
                ObjectID(account_cap),
            ],
            type_arguments=[type_base, type_quote],
        )
        breakpoint()
        success, tx_result_json, tx_result = libsui.execute_and_handle_result(txn)
        self.logger().debug(tx_result_json)
        return tx_result

    def deposit_quote(self, *args, **kwargs):
        """public fun deposit_quote<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def expire_timestamp(self, *args, **kwargs):
        """public fun expire_timestamp(order: &Order): u64 {"""
        raise NotImplementedError()

    def get_level(self, *args, **kwargs):
        """public fun get_level2_book_status_ask_side<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def get_level(self, *args, **kwargs):
        """public fun get_level2_book_status_bid_side<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

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

    def get_market_price(self, *args, **kwargs):
        """public fun get_market_price<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def get_order_status(self, pool_order_id, account_cap=None):
        """public fun get_order_status<BaseAsset, QuoteAsset>("""
        txn = SyncTransaction(client=self.client)
        return_value = txn.move_call(
            target=f"{self.package_id}::clob_v2::get_order_status",
            arguments=[
                ObjectID(self.pool_object_id),
                SuiU64(pool_order_id),
                ObjectID(self.account_cap),
            ],
            type_arguments=[
                "0x2::sui::SUI",
                f"{self.package_id}::realusdc::REALUSDC",
            ],
        )

        print("=== GET ORDER STATUS ===")
        pprint(txn.inspect_all())

        success, tx_result_json, tx_result = libsui.execute_and_handle_result(txn)
        self.logger().debug(tx_result_json)
        order_status = None
        breakpoint()
        return order_status

    def get_pool_stat(self, *args, **kwargs):
        """public fun get_pool_stat<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def get_usr_open_orders(self, *args, **kwargs):
        """public fun get_usr_open_orders<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def is_bid(self, *args, **kwargs):
        """public fun is_bid(order: &Order): bool {"""
        raise NotImplementedError()

    def list_open_orders(self, *args, **kwargs):
        """public fun list_open_orders<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def maker_rebate_rate(self, *args, **kwargs):
        """public fun maker_rebate_rate<BaseAsset, QuoteAsset>(pool: &Pool<BaseAsset, QuoteAsset>): u64 {"""
        raise NotImplementedError()

    def matched_order_metadata_info(self, *args, **kwargs):
        """public fun matched_order_metadata_info<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def mint_account_cap_transfer(self, *args, **kwargs):
        """public fun mint_account_cap_transfer("""
        raise NotImplementedError()

    def open_orders(self, *args, **kwargs):
        """public fun open_orders(tick_level: &TickLevel): &LinkedTable<u64, Order> {"""
        raise NotImplementedError()

    def order_id_for_test(self, *args, **kwargs):
        """public fun order_id_for_test("""
        raise NotImplementedError()

    def order_id(self, *args, **kwargs):
        """public fun order_id(order: &Order): u64 {"""
        raise NotImplementedError()

    def original_quantity(self, *args, **kwargs):
        """public fun original_quantity(order: &Order): u64 {"""
        raise NotImplementedError()

    def owner(self, *args, **kwargs):
        """public fun owner(order: &Order): address {"""
        raise NotImplementedError()

    def place_limit_order(self, price, quantity, is_bid=None, client_order_id=None):  # noqa: mock
        """public fun place_limit_order<BaseAsset, QuoteAsset>("""
        client_order_id = _client_trade_id() if client_order_id is None else client_order_id
        if quantity == 0:
            raise ValueError(f"quantity was 0; why are you placing an order?! ({quantity=}")
        if quantity < 0:
            if is_bid is not None and is_bid is True:
                raise ValueError(f"contradictory inputs: {is_bid=} but {quantity=} < 0")
            is_bid = False
            quantity = abs(quantity)
        else:
            if (quantity > 0) and (is_bid is not None) and (is_bid is False):
                raise ValueError(f"contradictory inputs: {is_bid=} but {quantity=} > 0")
            is_bid = True

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
                SuiU64(client_order_id),
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
        success, tx_result_json, tx_result = libsui.execute_and_handle_result(txn)
        breakpoint()
        pool_order_id = tx_result_json[4]
        return success, client_order_id, pool_order_id, tx_result

    def place_limit_order_with_metadata(self, *args, **kwargs):
        """public fun place_limit_order_with_metadata<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def place_market_order(self, *args, **kwargs):
        """public fun place_market_order<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def place_market_order_with_metadata(self, *args, **kwargs):
        """public fun place_market_order_with_metadata<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def pool_size(self, *args, **kwargs):
        """public fun pool_size<BaseAsset, QuoteAsset>(pool: &Pool<BaseAsset, QuoteAsset>): u64 {"""
        raise NotImplementedError()

    def quantity(self, *args, **kwargs):
        """public fun quantity(order: &Order): u64 {"""
        raise NotImplementedError()

    def quote_asset_trading_fees_value(self, *args, **kwargs):
        """public fun quote_asset_trading_fees_value<BaseAsset, QuoteAsset>(pool: &Pool<BaseAsset, QuoteAsset>): u64 {"""
        raise NotImplementedError()

    def setup_test(self, *args, **kwargs):
        """public fun setup_test("""
        raise NotImplementedError()

    def setup_test_with_tick_min(self, *args, **kwargs):
        """public fun setup_test_with_tick_min("""
        raise NotImplementedError()

    def setup_test_with_tick_min_and_wrapped_pool(self, *args, **kwargs):
        """public fun setup_test_with_tick_min_and_wrapped_pool("""
        raise NotImplementedError()

    def setup_test_wrapped_pool(self, *args, **kwargs):
        """public fun setup_test_wrapped_pool("""
        raise NotImplementedError()

    def swap_exact_base_for_quote(self, *args, **kwargs):
        """public fun swap_exact_base_for_quote<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def swap_exact_base_for_quote_with_metadata(self, *args, **kwargs):
        """public fun swap_exact_base_for_quote_with_metadata<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def swap_exact_quote_for_base(self, *args, **kwargs):
        """public fun swap_exact_quote_for_base<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def swap_exact_quote_for_base_with_metadata(self, *args, **kwargs):
        """public fun swap_exact_quote_for_base_with_metadata<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def taker_fee_rate(self, *args, **kwargs):
        """public fun taker_fee_rate<BaseAsset, QuoteAsset>(pool: &Pool<BaseAsset, QuoteAsset>): u64 {"""
        raise NotImplementedError()

    """
    public fun test_construct_order(sequence_id: u64, client_order_id: u64, price: u64, original_quantity: u64, quantity: u64, is_bid: bool, owner: address): Order {
    public fun test_construct_order_with_expiration(
    public fun test_inject_limit_order<BaseAsset, QuoteAsset>(
    public fun test_inject_limit_order_with_expiration<BaseAsset, QuoteAsset>(
    public fun test_match_ask<BaseAsset, QuoteAsset>(
    public fun test_match_bid<BaseAsset, QuoteAsset>(
    public fun test_match_bid_with_quote_quantity<BaseAsset, QuoteAsset>(
    public fun test_remove_order<BaseAsset, QuoteAsset>(
    """

    def tick_level(self, *args, **kwargs):
        """public fun tick_level(order: &Order): u64 {"""
        raise NotImplementedError()

    def tick_size(self, *args, **kwargs):
        """public fun tick_size<BaseAsset, QuoteAsset>(pool: &Pool<BaseAsset, QuoteAsset>): u64 {"""
        raise NotImplementedError()

    def usr_open_orders(self, *args, **kwargs):
        """public fun usr_open_orders<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def usr_open_orders_exist(self, *args, **kwargs):
        """public fun usr_open_orders_exist<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def usr_open_orders_for_address(self, *args, **kwargs):
        """public fun usr_open_orders_for_address<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def withdraw_base(self, *args, **kwargs):
        """public fun withdraw_base<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def withdraw_fees(self, *args, **kwargs):
        """public fun withdraw_fees<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()

    def withdraw_quote(self, *args, **kwargs):
        """public fun withdraw_quote<BaseAsset, QuoteAsset>("""
        raise NotImplementedError()


def current():
    global _DEEPBOOK
    if _DEEPBOOK is None:
        libsui.init()
        _DEEPBOOK = DeepbookConnector()
    return _DEEPBOOK


if __name__ == "__main__":
    print("running examples")

    amount_to_deposit = 10 * ONE_SUI
    price = 1 * (1.5 * ONE_SUI)  # 1.5 SUI per REALUSDC
    quantity = 1_000_000_000
    is_bid = False
    order_id = 136375

    connector = DeepbookConnector(client, cfg)
    # connector.create_account()#
    # print(connector.package_id)
    # print(connector.pool_object_id)
    connector.deposit_base(amount_to_deposit)
    connector.place_limit_order(price, quantity, is_bid)
    # connector.place_limit_order()
    # connector.place_limit_order()
    connector.get_level2_book_status_bid_side()
    connector.get_level2_book_status_ask_side()
    connector.get_order_status(order_id, ACCOUNT_CAP)
