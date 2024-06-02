""""Provide a python interface to the Sui Deepbook"""

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
    "ONE_SUI",
]
