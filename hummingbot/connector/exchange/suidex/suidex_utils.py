from decimal import Decimal

from pydantic import Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap, ClientFieldData
from hummingbot.connector.exchange.suidex import suidex_constants as CONSTANTS
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

CENTRALIZED = True
EXAMPLE_PAIR = "PDEX-1"

DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0"),
    taker_percent_fee_decimal=Decimal("0"),
)


def normalized_asset_name(asset_id: str, asset_name: str) -> str:
    name = asset_name if asset_id.isdigit() else asset_id
    name = name.replace("CHAINBRIDGE-", "C")
    name = name.replace("TEST DEX", "TDEX")
    name = name.replace("TEST BRIDGE", "TBRI")
    return name


class SuidexConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="suidex", const=True, client_data=None)
    suidex_seed_phrase: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Suidex seed phrase",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        ),
    )

    class Config:
        title = "suidex"


KEYS = SuidexConfigMap.construct()

# Disabling testnet because it breaks. We should enable it back when the issues in the server are solved
OTHER_DOMAINS = [f"suidex_{net}" for net in CONSTANTS.NETS]
OTHER_DOMAINS_PARAMETER = {f"suidex_{net}": net for net in CONSTANTS.NETS}
OTHER_DOMAINS_EXAMPLE_PAIR = {f"suidex_{net}": EXAMPLE_PAIR for net in CONSTANTS.NETS}
OTHER_DOMAINS_DEFAULT_FEES = {f"suidex_{net}": DEFAULT_FEES for net in CONSTANTS.NETS}


def _configmap(net):
    class SuidexBaseConfigMap(BaseConnectorConfigMap):
        connector: str = Field(default=f"suidex_{net}", const=True, client_data=None)
        suidex_seed_phrase: SecretStr = Field(
            default=...,
            client_data=ClientFieldData(
                prompt=lambda cm: f"Enter your Suidex {net} seed phrase",
                is_secure=True,
                is_connect_key=True,
                prompt_on_new=True,
            ),
        )

        class Config:
            title = f"suidex_{net}"

    return SuidexBaseConfigMap


OTHER_DOMAINS_KEYS = {f"suidex_{net}": _configmap(net).construct() for net in CONSTANTS.NETS}
