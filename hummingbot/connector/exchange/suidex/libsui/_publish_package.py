"""Publish the deepook contracts to the local net and automatically save their important info."""

# WORK IN PROGRESS - DONS'T WORK YET

from pysui import SuiConfig, SyncClient
from pysui.sui.sui_txn import SyncTransaction
from pysui.sui.sui_txresults.complex_tx import TxResponse

from hummingbot.connector.exchange.suidex.libsui._interface import cfg, client


def publish_and_result(txb: SyncTransaction, print_json=True) -> tuple[str, str]:
    """Example of running the publish commands in a SuiTransaction and retrieving important info."""
    # Set the sender if not already sent.
    # Not shown is optionally setting a sponsor as well
    if not txb.signer_block.sender:
        txb.signer_block.sender = txb.client.config.active_address

    # Execute the transaction
    tx_result = txb.execute(gas_budget="100000")
    package_id: str = None
    upgrade_cap_id: str = None

    if tx_result.is_ok():
        if hasattr(tx_result.result_data, "to_json"):
            # Get the result data and iterate through object changes
            tx_response: TxResponse = tx_result.result_data
            for object_change in tx_response.object_changes:
                match object_change["type"]:
                    # Found our newly published package_id
                    case "published":
                        package_id = object_change["packageId"]
                    case "created":
                        # Found our newly created UpgradeCap
                        if object_change["objectType"].endswith("UpgradeCap"):
                            upgrade_cap_id = object_change["objectId"]
                    case "mutated":
                        # On upgrades, UpgradeCap is mutated
                        if object_change["objectType"].endswith("UpgradeCap"):
                            upgrade_cap_id = object_change["objectId"]
                    case _:
                        pass
            if print_json:
                print(tx_response.to_json(indent=2))
        else:
            print(f"Non-standard result found {tx_result.result_data}")
    else:
        print(f"Error encoundered {tx_result.result_string}")
    return (package_id, upgrade_cap_id)


def publish_package(client: SyncClient = None):
    """Sample straight up publish of move contract returning UpgradeCap to current address."""
    client = client if client else SyncClient(cfg.default_config())

    # Initiate a new transaction
    txer = SyncTransaction(client=client)

    # Create a publish command
    # TODO: Not sure what the project path is
    upgrade_cap = txer.publish(
        project_path="~/Documents/Projects/consensus_EasyA_Hackathon/repos/hummingbot-pysui/hummingbot/connector/exchange/suidex/libsui/contracts/deepbook/"
    )

    # Transfer the upgrade cap to my address
    txer.transfer_objects(transfers=[upgrade_cap], recipient=client.config.active_address)

    # Convenience method to sign and execute transaction and fetch useful information
    package_id, cap_id = publish_and_result(txer, False)
    print(f"Package ID: {package_id}")
    print(f"UpgradeCap ID: {cap_id}")


if __name__ == "__main__":
    publish_package()
