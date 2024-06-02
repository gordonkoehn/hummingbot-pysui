# Setting up suibase and pysui

_for manual testing purposes_

1. Install suibase
2. run hummingbot env in local
   ```bash
   conda activate hummingbot
   ```
4. Setup localnet and get wallet information
   ```bash
    localnet start; localnet status
   # localnet stop //when stopping the localnet 
   # localnet regen // if you have previously started localnet before
   # ps aux | grep "[s]uibase" | awk '{print $2}' | xargs kill //if you want to stop the daemon completely   
   ```
5. Get active wallet info
   ```bash
   lsui keytool export --key-identity sb-1-ed25519
   ```
   and paste this into your local .env file that is imported in `sui_client_config.py`; like:
   ```bash
   echo "LOCALNET_ADDR1_PRVKEY=$(lsui keytool export --key-identity sb-1-ed25519 --json | grep suipriv | cut '-d"' -f 4)" >> .env.localnet
   ```
6. Deploy Contract
   ```bash
   # in the dir of move.toml
    localnet publish --skip-dependency-verification
   ```
8. Add pysui to your project and make `devInspect` calls or `executeTransaction` calls



# Currencies background and terminology

Even amongst experienced FX traders and quantitative finance practitioners,
terminology confusion abounds.  We adopt a consistent terminology that is
understandable and in use by market practitioners including: 1) members of the
Bank of England Joint Standing Committee chief dealer's group, dealing in the
world's largest FX trading market (UK) [^symbology-ukfx]; 2) market data
providers like Bloomberg[^symbology-bbg] and Reuters[^symbology-reut]; and 3)
SUI Deepbook Central Limit Order Book (CLOB) implementation[^deepbook].


## tl;dr

| quoted price    | QuoteAsset | BaseAsset |
|-----------------|------------|-----------|
| $60,000 USD/BTC | USD        | BTC       |
| $60,000 BTC-USD | USD        | BTC       |
|                 |            |           |
| $5,000 USD/ETH  | USD        | ETH       |
| $5,000 ETH-USD  | USD        | ETH       |
|                 |            |           |
| ₿0.3 BTC/ETH    | BTC        | ETH       |
| ₿0.3 ETH-BTC    | BTC        | ETH       |
|                 |            |           |
| $1.2 USD/GBP    | USD        | GBP       |
| $1.2 GBPUSD     | USD        | GBP       |
| $1.2 GBP-USD    | USD        | GBP       |
|                 |            |           |


## Discussion

    For 'BTC-USD', 'BTC' is the 'coin' and 'USD' is the numeraire.

    MNEMONIC: "the COIN IS UNDER the sofa."; that is, "coin" is "under currency".

    To repeat:

        MNEMONIC: "the COIN IS UNDER the sofa."; that is, "coin" is "under currency".

    Because of how we quote prices and write fractions $3 \texttt{BTC} * \frac{60,000 \texttt{USD}}{1 \texttt{BTC}}} =
    180,000 \texttt{USD}$; that is, because:

    ```

     3  BTC  *    60,000 USD
                ------------   = 180,000 USD
                     1   BTC

    ```

    ...for a price of "60,000 USD/BTC", we call 'BTC' ('coin') the "under" currency and `USD` the "over" currency.


## Table

| quoted price    | symbol  | source    | QuoteAsset | BaseAsset | coin | numeraire | over | under | "local" | "base" |
|-----------------|---------|-----------|------------|-----------|------|-----------|------|-------|---------|--------|
| $60,000 USD/BTC | USD/BTC | Reuters   | USD        | BTC       | BTC  | USD       | USD  | BTC   | BTC     | USD    |
| $60,000 BTC-USD | BTC-USD | Bloomberg | USD        | BTC       | BTC  | USD       | USD  | BTC   | BTC     | USD    |
|                 |         |           |            |           |      |           |      |       |         |        |
| $5,000 USD/ETH  | USD/ETH | Reuters   | USD        | ETH       | ETH  | USD       | USD  | ETH   | ETH     | USD    |
| $5,000 ETH-USD  | ETH-USD | Bloomberg | USD        | ETH       | ETH  | USD       | USD  | ETH   | ETH     | USD    |
|                 |         |           |            |           |      |           |      |       |         |        |
| ₿0.3 BTC/ETH    | BTC/ETH | Reuters   | BTC        | ETH       | ETH  | BTC       | BTC  | ETH   | ETH     | BTC    |
| ₿0.3 ETH-BTC    | ETH-BTC | Bloomberg | BTC        | ETH       | ETH  | BTC       | BTC  | ETH   | ETH     | BTC    |


    Commonly:

    | example                              | currency | roles                 |
    | :------                              | :-----:  | :-----:               |
    | "Bitcoin is at $60,000"              | BTC      | coin, under, local    |
    |                                      | USD      | numeraire, over, base |
    | "Ether is at $5,000"                 | ETH      | coin, under, local    |
    |                                      | USD      | numeraire, over, base |
    |                                      |          |                       |
    | "'The cross' is at ₿0.03"            | ETH      | coin, under, local    |
    |                                      | BTC      | numeraire, over       |
    |                                      |          |                       |
    | "My 10 BTC position is worth a ton!" | BTC      | coin, under, local    |
    |                                      | USD      | numeraire, over, base |
    |                                      |          |                       |


    Synonyms:

    * "coin" is the same as "under [currency]"
    * "coin" is the same as "local [currency]"

    Less commonly, one will come across these terms to describe trades/orders:

    * "numeraire" is the same as "trade [currency]" is the same as "receive [currency]", because when one "buys bitcoin [with USD]", one "pays USD" and "receives BTC".


## Examples of market-standard terminology for trades and prices

Note that "Pay" and "Receive" terms refer to the flow of assets from "You"r
perspective, whereas all the OTHER terms, like "coin" and "QuoteAsset", refer
to attributes of the *quoted price*, which is independent of the parties.

| Example                                 | currency | Terms & their roles                                       |
|:---------------------------------------:|:--------:|:---------------------------------------------------------:|
| "You BUY 8 BTC at $60,000 for $480,000" | BTC      | BaseAsset, receive, coin, under, local                    |
|                                         | USD      | QuoteAsset, pay, numeraire, over, base, trade, settle     |
|                                         |          |                                                           |
| "You SEL 1 BTC at $60,000 for $60,000"  | BTC      | BaseAsset, pay, coin, under, local                        |
|                                         | USD      | QuoteAsset, receive, numeraire, over, base, trade, settle |
|                                         |          |                                                           |
| "You BUY 8 ETH at $60,000 for $480,000" | ETH      | receive, coin, under, local                               |
|                                         | USD      | pay, numeraire, over, base, trade, settle                 |
|                                         |          |                                                           |
| "You SEL 1 ETH at $60,000 for $60,000"  | ETH      | pay, coin, under, local                                   |
|                                         | USD      | receive, numeraire, over, base, trade, settle             |
|                                         |          |                                                           |
| "You BUY 8 ETH at ₿0.04 for ₿0.24"      | ETH      | receive, coin, under, local                               |
|                                         | BTC      | pay, numeraire, over, trade, settle                       |
|                                         |          |                                                           |
| "You BUY 8 ETH at ₿0.04 for ₿0.24...    | ETH      | receive, coin, under, local                               |
| ...settling in USD"                     | BTC      | over, trade                                               |
|                                         | USD      | pay, numeraire, base, settle                              |
|                                         |          |                                                           |
| "You SEL 8 ETH at ₿0.04 for ₿0.24...    | ETH      | pay, coin, under, local                                   |
| ...settling in USD"                     | BTC      | over, trade                                               |
|                                         | USD      | receive, numeraire, base, settle                          |



## Calculation Cheat Sheet

    # 1 BTC    *        BTC-USD          = ???   USD        -- 1 BTC  *  33,000                     =     33,000 USD
    # 1 BTC    *        USD/BTC          = ???   USD        -- 1 BTC  * (33,000 USD / 1 BTC)        =     33,000 USD
    # 1 under  *        over/under       = ???   over       -- 1 BTC  * (33,000 USD / 1 BTC)        =     33,000 USD
    # q under  *        over/under       = px    over       -- q BTC  * (33,000 USD / 1 BTC)        = q * 33,000 USD
    # 1 coin   *        numeraire/coin   = ???   numeraire  -- 1 coin *  33,000 numeraire-coin      =     33,000 numeraire
    # 1 coin   *        coin-numeraire   = ???   numeraire  -- 1 coin *  33,000 numeraire-coin      =     33,000 numeraire
    # q coin   BOUGHT @ PRICE numeraire  = PRICE numeraire  -- q coin *  33,000 PRICE of numeraire  = q * 33,000 numeraire
    # 1 BTC    BOUGHT @ 33,000 BTC-USD   = PRICE USD        -- 1 BTC  *  33,000 BTC-USD             =     33,000 USD
    # q BTC    BOUGHT @ 33,000 BTC-USD   = PRICE USD        -- q BTC  *  33,000 BTC-USD             = q * 33,000 USD


## Confusion Examples

| # | Example           | Source    | QuoteAsset | BaseAsset |
|---|:------------------|-----------|------------|-----------|
| 1 | $60,000 USD/BTC   | Reuters   | USD        | BTC       |
| 2 | $60,000 BTC-USD   | Bloomberg | USD        | BTC       |
| 3 | USD/EUR           | Reuters   | USD        | EUR       |
| 4 | EUR-USD           | Bloomberg | USD        | EUR       |
| 5 | USD/EUR           | ECB       | EUR        | USD       |
| 6 | GBP/USD           | Reuters   | USD        | GBP       |
| 7 | 1.2 GBP-USD       | Bloomberg | USD        | GBP       |
| 7 | 1.2 GBPUSD CURNCY | Bloomberg | USD        | GBP       |
| 8 | 1.2 GBP/USD       | BIS       | GBP        | USD       |
| 9 | 1.2 USD/GBP       | ECB       | GBP        | USD       |

Please note the confusion possible between #3 vs #5 and #6 and #8.  We are not
responsible for the ECB's symbology[^wikipedia-ecb] or the Wikipedia editors'
choice of sources.  They are not reflective of FX spot market practice as
evidenced by Reuters, Bloomberg, and BIS data[^bis-data].


## Inverted / flipped currencies

Humans prefer to talk about prices as integers larger that 1.  So it is
customary to talk about prices between GBP and USD in terms of how much USD is involved: "$1.2
GBPUSD", "cable is $1.2", "buy a yard of Betty for $1.2", rather than in terms
of how much GBP is involved "£0.83 USDGBP" would not be spoken about.
Consider, for example, the price of exchanging USD and JPY is quoted in terms
of how many yen are exchanged: ¥126 JPY/USD and not "$0.0066 USD per JPY".  For
more discussion, see "2.3 Sourcing"'s "Market conventions" section in the
[LSEG's FX Methodology guide](https://www.lseg.com/content/dam/ftse-russell/en_us/documents/methodology/wmr-methodology.pdf).


## References

[^symbology-ukfx]:

[^symbology-bbg]: Example: https://www.bloomberg.com/quote/GBPUSD:CUR (quote:
    USD, base: GBP) ; similar to https://www.bloomberg.com/quote/USDJPY:CUR
    (quote: JPY, base: USD) via https://www.bloomberg.com/markets/currencies
    Source: https://bsym.bloomberg.com/id/BBG0013HQ141

[^symbology-reut]: Example: https://finance.yahoo.com/quote/GBPUSD=X/  via https://www.reuters.com/markets/currencies/gbp/

[^deepbook]: https://docs.sui.io/standards/deepbook  and https://www.deepbook.tech/

[^wikipedia-ecb]: From
https://web.archive.org/web/20190903175803/https://fxaccumulator.com/interpreting-a-currency-pair/
via https://en.wikipedia.org/wiki/Currency_pair#cite_note-4 and
https://en.wikipedia.org/wiki/Currency_pair

[^bis-data]: For example see: https://data.bis.org/topics/XRU/BIS,WS_XRU,1.0/D.GB.GBP.A
