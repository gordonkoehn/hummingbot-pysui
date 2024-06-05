"""

Usage example:

```
$ conda activate hummingbot

$ python -m hummingbot.connector.exchange.suidex.libsui
localnet
<pysui.sui.sui_config.SuiConfig object at 0x7ff1bcbf1390>
<pysui.sui.sui_clients.sync_client.SuiClient object at 0x7ff1bc8465f0>

```

"""
import hummingbot.connector.exchange.suidex.libsui as libsui

print("\n".join(map(str, libsui.init())))
