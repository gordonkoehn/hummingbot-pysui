"""adapt SuidexDataSource to OrderBookDataSource interface"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from hummingbot.connector.exchange.suidex import suidex_constants as CONSTANTS
from hummingbot.connector.exchange.suidex.chain_data_source import SuidexDataSource
from hummingbot.core.data_type.order_book_message import OrderBookMessage
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.event.event_forwarder import EventForwarder
from hummingbot.core.event.events import OrderBookEvent
from hummingbot.core.web_assistant.ws_assistant import WSAssistant

if TYPE_CHECKING:
    from hummingbot.connector.exchange.suidex.suidex_exchange import SuidexExchange
else:
    SuidexExchange = type(None)


class SuidexOrderBookDataSource(OrderBookTrackerDataSource):
    def __init__(
        self,
        connector: SuidexExchange,
        trading_pairs: List[str],
        data_source: SuidexDataSource,
    ):
        super().__init__(trading_pairs=trading_pairs)
        self._ev_loop = asyncio.get_event_loop()
        self._connector = connector
        self._data_source = data_source
        self._forwarders = []
        self._configure_event_forwarders()

        # Initialize message queues that will be accessed by events from a different thread. The lazy initialization
        # would break in that case because an async Queue can't be created in a thread that is not running
        # the async loop
        self._message_queue[self._diff_messages_queue_key] = asyncio.Queue()
        self._message_queue[self._trade_messages_queue_key] = asyncio.Queue()

    async def get_last_traded_prices(self, trading_pairs: List[str]) -> Dict[str, float]:
        return await _data_source.get_last_traded_prices(trading_pairs=trading_pairs)

    async def listen_for_subscriptions(self):
        # The chain reconnection is managed by the data_source. This method should do nothing
        pass

    async def _parse_order_book_snapshot_message(self, raw_message: Dict[str, Any], message_queue: asyncio.Queue):
        # Polkadex only sends diff order book messages
        raise NotImplementedError

    async def _connected_websocket_assistant(self) -> WSAssistant:
        # Polkadex uses GrapQL websockets to consume stream events
        raise NotImplementedError

    async def _subscribe_channels(self, ws: WSAssistant):
        # Polkadex uses GrapQL websockets to consume stream events
        raise NotImplementedError

    def _channel_originating_message(self, event_message: Dict[str, Any]) -> str:
        # Polkadex uses GrapQL websockets to consume stream events
        return ""

    async def _order_book_snapshot(self, trading_pair: str) -> OrderBookMessage:
        symbol = await self._connector.exchange_symbol_associated_to_pair(trading_pair=trading_pair)
        snapshot = await self._data_source.order_book_snapshot(market_symbol=symbol, trading_pair=trading_pair)
        return snapshot

    async def _parse_trade_message(self, raw_message: OrderBookMessage, message_queue: asyncio.Queue):
        # In Polkadex 'raw_message' is not a raw message, but the OrderBookMessage with type Trade created
        # by the data source
        message_queue.put_nowait(raw_message)

    async def _parse_order_book_diff_message(self, raw_message: OrderBookMessage, message_queue: asyncio.Queue):
        # In Polkadex 'raw_message' is not a raw message, but the OrderBookMessage with type Trade created
        # by the data source
        message_queue.put_nowait(raw_message)

    def _configure_event_forwarders(self):
        event_forwarder = EventForwarder(to_function=self._process_order_book_event)
        self._forwarders.append(event_forwarder)
        self._data_source.add_listener(
            event_tag=OrderBookEvent.OrderBookDataSourceUpdateEvent, listener=event_forwarder
        )

        event_forwarder = EventForwarder(to_function=self._process_public_trade_event)
        self._forwarders.append(event_forwarder)
        self._data_source.add_listener(event_tag=OrderBookEvent.TradeEvent, listener=event_forwarder)

    def _process_order_book_event(self, order_book_diff: OrderBookMessage):
        self._message_queue[self._diff_messages_queue_key].put_nowait(order_book_diff)

    def _process_public_trade_event(self, trade_update: OrderBookMessage):
        self._message_queue[self._trade_messages_queue_key].put_nowait(trade_update)
