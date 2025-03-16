import web3
from web3 import Web3
import json
import os
import time
import datetime
import logging
import random
from pathlib import Path
from colorama import Fore, Style, init
from dotenv import load_dotenv

init(autoreset=True)
# color & load env
load_dotenv()

# ======================== Configuration ========================
CONFIG = {
    "RPC_URLS": os.getenv(
        "RPC_URLS",
        "https://16600.rpc.thirdweb.com,https://rpc.ankr.com/0g_newton,https://evmrpc-testnet.0g.ai",
    ).split(","),
    "CONTRACT_ADDRESS": os.getenv(
        "CONTRACT_ADDRESS", "0x90723fb8FC109096c69BDb73E801989807E7C81F"
    ),
    "PRIVATE_KEY_FILE": os.path.join(os.path.dirname(__file__), "private_keys.txt"),
    "ENV_FILE": ".env",
    "MAX_RETRIES": 3,
    "GAS_MULTIPLIER": 1.5,
    "MAX_PRIORITY_GWEI": 1.8,
    "GAS_LIMIT": 310000,
    "COOLDOWN": {"SUCCESS": 15, "ERROR": 30},
    # Short delay in wallet secs
    "WALLET_SWITCH_DELAY": (120, 480),
    # Long delay after all wallets use secs
    "CYCLE_COMPLETE_DELAY": (3600, 7200),
}

# ======================== Chain Symbol ========================
CHAIN_SYMBOLS = {1: "ETH", 16600: "A0GI"}

# Tx counter
tx_counter = 0

# ======================== ABI Contract ========================
ABI = [
    {
        "inputs": [],
        "name": "Vote",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "string", "name": "message", "type": "string"}],
        "name": "VoteWithMessage",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "string", "name": "message", "type": "string"},
        ],
        "name": "VoteForRecipient",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

# ======================== Info Logging ========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("VoteDapps")

def log_info(message):
    logger.info(message)
    print(message)


def log_error(message):
    logger.error(message)
    print(message)


def log_warning(message):
    logger.warning(message)
    print(message)


# ======================== Utility Functions ========================
def short_address(address):
    return f"{address[:6]}...{address[-4:]}" if address else "Unknown address"


def sleep_seconds(seconds, message=None):
    if message:
        print(f"9️⃣ {Fore.GREEN}{message} in {seconds} seconds...{Style.RESET_ALL}")
    else:
        print(
            f"9️⃣ {Fore.GREEN}Mode airplane..Rotating sleep in {seconds} seconds...{Style.RESET_ALL}"
        )
    time.sleep(seconds)


# Print banner
def print_welcome_message():
    welcome_banner = f"""
{Fore.GREEN}============================ WELCOME TO VOTING DAPPs ============================{Fore.RESET}
{Fore.YELLOW}
 ██████╗██╗   ██╗ █████╗ ███╗   ██╗███╗   ██╗ ██████╗ ██████╗ ███████╗
██╔════╝██║   ██║██╔══██╗████╗  ██║████╗  ██║██╔═══██╗██╔══██╗██╔════╝
██║     ██║   ██║███████║██╔██╗ ██║██╔██╗ ██║██║   ██║██║  ██║█████╗  
██║     ██║   ██║██╔══██║██║╚██╗██║██║╚██╗██║██║   ██║██║  ██║██╔══╝  
╚██████╗╚██████╔╝██║  ██║██║ ╚████║██║ ╚████║╚██████╔╝██████╔╝███████╗
 ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝
{Fore.RESET}
{Fore.GREEN}========================================================================={Fore.RESET}
{Fore.MAGENTA}         Welcome to Voting Onchain Testnet & Mainnet Interactive   {Fore.RESET}
{Fore.YELLOW}           - CUANNODE By Greyscope&Co, Credit By Arcxteam -     {Fore.RESET}
{Fore.GREEN}========================================================================={Fore.RESET}
"""
    print(welcome_banner)


# ============================ Connect Web3 Wallet ===================================
def is_connected(web3):
    try:
        chain_id = web3.eth.chain_id
        print(
            f"1️⃣ Connected to network with chain ID: {Fore.GREEN}{chain_id}{Fore.RESET}"
        )
        return chain_id
    except Exception as e:
        print(f"0️⃣ Failed to connect to the network: {e}")
        return None


# ============================ Function of Class ==================================
class VoteScheduler:
    def __init__(self):
        self.accounts = []
        self.gas_price = None
        self.web3 = None
        self.contract = None
        self.cycle_count = 1

    def initialize(self):
        self.connect_to_rpc()
        self.load_accounts()
        self.update_gas_price()

    def connect_to_rpc(self):
        """Connect to the first available RPC endpoint"""
        for rpc_url in CONFIG["RPC_URLS"]:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url.strip()))
                if w3.is_connected() and w3.eth.chain_id == int(
                    os.getenv("CHAIN_ID", "16600")
                ):
                    self.web3 = w3
                    self.contract = self.web3.eth.contract(
                        address=CONFIG["CONTRACT_ADDRESS"], abi=ABI
                    )
                    print(
                        f"🌐 Connected to RPC: {Fore.GREEN}{rpc_url}{Style.RESET_ALL}"
                    )
                    return True
            except Exception as e:
                print(f"⚠️ Failed to connect to RPC {rpc_url}: {e}")
                continue

        if not self.web3:
            raise ConnectionError(
                "Failed to connect to any RPC endpoint. Please check your RPC URLs."
            )

    def retry_with_new_rpc(self):
        """Try to connect to a different RPC endpoint"""
        current_url = None
        for provider in self.web3.provider._active_providers:
            if hasattr(provider, "endpoint_uri"):
                current_url = provider.endpoint_uri
                break

        remaining_urls = [
            url.strip() for url in CONFIG["RPC_URLS"] if url.strip() != current_url
        ]
        random.shuffle(remaining_urls)

        for rpc_url in remaining_urls:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                if w3.is_connected() and w3.eth.chain_id == int(
                    os.getenv("CHAIN_ID", "16600")
                ):
                    self.web3 = w3
                    self.contract = self.web3.eth.contract(
                        address=CONFIG["CONTRACT_ADDRESS"], abi=ABI
                    )
                    print(f"🔄 Switched to RPC: {Fore.GREEN}{rpc_url}{Style.RESET_ALL}")
                    return True
            except Exception as e:
                print(f"⚠️ Failed to switch to RPC {rpc_url}: {e}")
                continue

        print(f"{Fore.RED}Failed to switch to any alternative RPC{Style.RESET_ALL}")
        return False

    def is_valid_private_key(self, key):
        """Validate a private key format and return standardized key"""
        try:
            if not key or key.startswith("#"):
                return None

            # Standardize key format (add 0x if missing)
            if not key.startswith("0x"):
                key = "0x" + key

            if len(key) != 66:
                return None

            self.web3.eth.account.from_key(key)
            return key
        except Exception:
            return None

    def load_accounts(self):
        accounts = []

        # Try loading from .env
        if os.path.exists(CONFIG["ENV_FILE"]):
            try:
                load_dotenv(CONFIG["ENV_FILE"])
                private_key = os.getenv("PRIVATE_KEY")
                if private_key:
                    valid_key = self.is_valid_private_key(private_key)
                    if valid_key:
                        account = self.web3.eth.account.from_key(valid_key)
                        accounts.append({"key": valid_key, "address": account.address})
                        print(
                            f"3️⃣ Attempting to load wallet... {Fore.GREEN}Status: OK gas Bang!!!{Style.RESET_ALL}"
                        )
                        print(
                            f"4️⃣ Wallet loaded successfully -> EVM Address: {account.address}"
                        )
            except Exception as e:
                log_error(f"Error loading from .env: {str(e)}")

        # Then try loading from private_keys.txt
        if os.path.exists(CONFIG["PRIVATE_KEY_FILE"]):
            try:
                with open(CONFIG["PRIVATE_KEY_FILE"], "r") as file:
                    keys = [line.strip() for line in file.readlines()]
                    for key in keys:
                        valid_key = self.is_valid_private_key(key)
                        if valid_key:
                            account = self.web3.eth.account.from_key(valid_key)
                            if not any(
                                acc["address"] == account.address for acc in accounts
                            ):
                                accounts.append(
                                    {"key": valid_key, "address": account.address}
                                )
                                print(
                                    f"3️⃣ Attempting to load wallet... {Fore.GREEN}Status: OK Gas!!!{Style.RESET_ALL}"
                                )
                                print(
                                    f"4️⃣ Wallet loaded successfully -> EVM Address: {account.address}"
                                )
                        else:
                            print(
                                f"3️⃣ Attempting to load wallet... {Fore.RED}Status: FAILED{Style.RESET_ALL}"
                            )
                            print("Invalid key format or length")
            except Exception as e:
                log_error(f"Error loading private keys: {str(e)}")

        if not accounts:
            log_error("No valid private keys found in either .env or private_keys.txt")
            exit(1)

        self.accounts = accounts
        print(f"🔄 Successfully loaded {len(self.accounts)} accounts")

    def get_eip1559_gas_params(self):
        """Get EIP-1559 gas parameters"""
        try:
            # Get base fee from blockchain
            fee_history = self.web3.eth.fee_history(1, 'latest')
            if 'baseFeePerGas' not in fee_history or not fee_history['baseFeePerGas'] or len(fee_history['baseFeePerGas']) == 0:
                logger.warning("EIP-1559 fee history missing baseFeePerGas, falling back to legacy")
                return None
            
            base_fee = fee_history['baseFeePerGas'][0]
            if base_fee is None:
                logger.warning("EIP-1559 base fee is None, falling back to legacy")
                return None

            max_priority = self.web3.to_wei(CONFIG["MAX_PRIORITY_GWEI"], 'gwei')
            max_fee = int(base_fee * CONFIG["GAS_MULTIPLIER"]) + max_priority

            # Convert to Gwei for display
            base_fee_gwei = self.web3.from_wei(base_fee, 'gwei')
            max_fee_gwei = self.web3.from_wei(max_fee, 'gwei')
            max_priority_gwei = self.web3.from_wei(max_priority, 'gwei')

            # Calculate tx cost in balances
            total_cost_wei = CONFIG["GAS_LIMIT"] * max_fee
            total_cost_eth = self.web3.from_wei(total_cost_wei, 'ether')

            print(f"⛽ Gas Prices: Base Fee: {base_fee_gwei:.9f} Gwei | Max Fee: {max_fee_gwei:.9f} Gwei | Priority Fee: {max_priority_gwei:.9f} Gwei")
            print(f"💱 Est. Transaction Cost: {Fore.YELLOW}{total_cost_eth:.9f} {CHAIN_SYMBOLS.get(self.web3.eth.chain_id, 'A0GI')}{Fore.RESET}")

            return {'maxFeePerGas': max_fee, 'maxPriorityFeePerGas': max_priority}
        except Exception as e:
            log_error(f"EIP-1559 gas estimation failed: {str(e)}")
            return None

    def get_legacy_gas_price(self):
        """Get legacy gas price"""
        try:
            current = self.web3.eth.gas_price
            gas_price = int(current * CONFIG["GAS_MULTIPLIER"])
            gas_gwei = self.web3.from_wei(gas_price, "gwei")
            print(f"⚡ Gas price updated: {gas_gwei:.9f} Gwei (Legacy Mode)")
            return gas_price
        except Exception as e:
            log_error(f"Legacy gas estimation failed: {str(e)}")
            return self.web3.to_wei(50, "gwei")  # Safe fallback

    def update_gas_price(self):
        """Update gas price with EIP-1559 or legacy mode"""
        # Try EIP-1559 first
        eip1559_params = self.get_eip1559_gas_params()
        if eip1559_params:
            self.gas_price = eip1559_params
        else:
            # Fallback to legacy
            self.gas_price = self.get_legacy_gas_price()

    def get_wallet_balance(self, address):
        try:
            chain_id = self.web3.eth.chain_id
            token_symbol = CHAIN_SYMBOLS.get(chain_id, "A0GI")

            balance_wei = self.web3.eth.get_balance(address)
            balance_eth = self.web3.from_wei(balance_wei, "ether")
            print(
                f"5️⃣ Checking Wallet Balance: {Fore.YELLOW}{balance_eth:.6f} {token_symbol}{Fore.RESET}"
            )
            return balance_wei
        except Exception as e:
            log_error(f"Error getting balance: {str(e)}")
            return 0

    def estimate_gas(self, sender):
        try:
            gas_estimate = self.contract.functions.Vote().estimate_gas({"from": sender})
            return int(gas_estimate * 1.2)  # Add 20% buffer
        except Exception as e:
            print(f"⚠️ Gas estimation failed: {str(e)}. Using safe default.")
            return CONFIG["GAS_LIMIT"]

    def build_transaction(self, sender):
        try:
            nonce = self.web3.eth.get_transaction_count(sender, "pending")
            gas_limit = self.estimate_gas(sender)
            print(f"🚀 Estimated gas usage: {gas_limit}")

            # Vote 80% and VoteWithMessage 20% (0.8 & 0.2)
            vote_type = "Vote" if random.random() < 0.8 else "VoteWithMessage"

            tx = {
                "from": sender,
                "to": CONFIG["CONTRACT_ADDRESS"],
                "gas": gas_limit,
                "nonce": nonce,
                "chainId": self.web3.eth.chain_id,
            }

            if vote_type == "Vote":
                tx["data"] = self.contract.encodeABI(fn_name="Vote", args=[])
                print(f"🔵 Vote Transaction Prepared")
            else:
                messages = ["0G AI layer 1", "Vote 0G", "Vote NFT", "0Gmorning", "VoteDapps"]
                message = random.choice(messages)
                tx["data"] = self.contract.encodeABI(
                    fn_name="VoteWithMessage", args=[message]
                )
                print(f"🔵 VoteWithMessage Transaction Prepared: '{message}'")

            if isinstance(self.gas_price, dict):
                tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
            else:
                tx["gasPrice"] = self.gas_price

            print(
                f"🔵 Transaction onchain data with nonce -> {Fore.Yellow}[{nonce}]{Style.RESET_ALL}"
            )
            return tx

        except Exception as e:
            log_error(f"❌ Error building transaction: {str(e)}")
            return None

    def handle_tx_error(self, error, tx):
        """Handle transaction error and update tx if needed"""
        error_message = str(error)

        if "insufficient funds" in error_message.lower():
            print(
                f"{Fore.RED}Error: 💰 Insufficient funds for gas * price + value{Style.RESET_ALL}"
            )
            return None, False

        elif "nonce too low" in error_message.lower():
            try:
                new_nonce = self.web3.eth.get_transaction_count(tx["from"], "pending")
                tx["nonce"] = new_nonce
                print(f"Updated nonce to {new_nonce}")
                return tx, True
            except Exception as nonce_error:
                log_error(f"Error updating nonce: {str(nonce_error)}")
                return None, False

        elif any(
            msg in error_message.lower() for msg in ["fee too low", "underpriced"]
        ):
            if isinstance(self.gas_price, dict):
                self.gas_price["maxFeePerGas"] = int(
                    self.gas_price["maxFeePerGas"] * 1.5
                )
                self.gas_price["maxPriorityFeePerGas"] = int(
                    self.gas_price["maxPriorityFeePerGas"] * 1.5
                )

                tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]

                new_max_fee_gwei = self.web3.from_wei(
                    self.gas_price["maxFeePerGas"], "gwei"
                )
                print(
                    f" 🤯 Transaction fees too low. Increased to {new_max_fee_gwei:.6f} Gwei"
                )
            else:
                self.gas_price = int(self.gas_price * 1.5)
                tx["gasPrice"] = self.gas_price
                new_gas_gwei = self.web3.from_wei(self.gas_price, "gwei")
                print(
                    f" 🤯 Transaction fees too low. Increased to {new_gas_gwei:.6f} Gwei"
                )

            return tx, True

        # Mempool full error
        elif "mempool is full" in error_message.lower():
            print(
                f"{Fore.YELLOW}⚠️ Mempool is full. Trying to switch RPC...{Style.RESET_ALL}"
            )
            if self.retry_with_new_rpc():
                return tx, True
            else:
                # If can't switch RPC, wait longer and retry with higher gas
                time.sleep(CONFIG["COOLDOWN"]["ERROR"] * 2)
                if isinstance(self.gas_price, dict):
                    self.gas_price["maxFeePerGas"] = int(
                        self.gas_price["maxFeePerGas"] * 2
                    )
                    self.gas_price["maxPriorityFeePerGas"] = int(
                        self.gas_price["maxPriorityFeePerGas"] * 2
                    )
                    tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                    tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
                else:
                    self.gas_price = int(self.gas_price * 2)
                    tx["gasPrice"] = self.gas_price
                return tx, True

        else:
            if isinstance(self.gas_price, dict):
                self.gas_price["maxFeePerGas"] = int(
                    self.gas_price["maxFeePerGas"] * 1.2
                )
                self.gas_price["maxPriorityFeePerGas"] = int(
                    self.gas_price["maxPriorityFeePerGas"] * 1.2
                )

                tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]

                new_max_fee_gwei = self.web3.from_wei(
                    self.gas_price["maxFeePerGas"], "gwei"
                )
                print(f"Increased gas price for retry: {new_max_fee_gwei:.6f} Gwei")
            else:
                self.gas_price = int(self.gas_price * 1.2)
                tx["gasPrice"] = self.gas_price
                new_gas_gwei = self.web3.from_wei(self.gas_price, "gwei")
                print(f"Increased gas price for retry: {new_gas_gwei:.6f} Gwei")

            return tx, True

    def send_transaction(self, tx, private_key):
        global tx_counter
        retries = CONFIG["MAX_RETRIES"]

        while retries > 0:
            try:
                signed = self.web3.eth.account.sign_transaction(tx, private_key)
                receipt = self.web3.eth.send_raw_transaction(signed.rawTransaction)
                tx_counter += 1
                tx_hash = receipt.hex()
                print(
                    f"6️⃣ Transaction Sent {Fore.GREEN}Successfully{Style.RESET_ALL} with Total TXiD {Fore.RED}{tx_counter}{Style.RESET_ALL} -> {Fore.GREEN}TxID Hash:{Style.RESET_ALL} {tx_hash}"
                )

                print(f"⌛ Waiting for transaction to onchain...")
                try:
                    tx_receipt = self.web3.eth.wait_for_transaction_receipt(
                        receipt, timeout=130
                    )
                    if tx_receipt.status == 1:
                        print(
                            f"{Fore.GREEN}😎 Transaction successfully onchain!{Style.RESET_ALL}"
                        )
                    else:
                        print(
                            f"{Fore.RED}🔞 Transaction failed on-chain! Check explorer for details.{Style.RESET_ALL}"
                        )
                    return tx_receipt
                except Exception as timeout_error:
                    print(
                        f"⏱️ Timeout waiting for transaction receipt: {str(timeout_error)}"
                    )
                    print(f"🆙 Transaction may still be pending. Check hash: {tx_hash}")
                    return None

            except Exception as e:
                updated_tx, should_retry = self.handle_tx_error(e, tx)

                if not should_retry:
                    return None

                tx = updated_tx
                retries -= 1
                print(
                    f"Error sending transaction. Retries left: {retries}. Error: {str(e)}"
                )

                if retries == 0:
                    print(f"{Fore.RED}All retry attempts failed.{Style.RESET_ALL}")
                    return None

                time.sleep(CONFIG["COOLDOWN"]["ERROR"])

        return None

    def execute_vote(self, account, is_last_wallet=False):
        try:
            private_key = account["key"]
            sender = account["address"]

            initial_balance = self.get_wallet_balance(sender)

            tx_data = self.build_transaction(sender)
            if not tx_data:
                return False

            receipt = self.send_transaction(tx_data, private_key)
            if not receipt:
                print(
                    f"{Fore.RED}🤏 Transaction failed or receipt not available.{Fore.RESET}"
                )
                return False

            if receipt.status != 1:
                print(f"{Fore.RED}🤏 Transaction reverted on-chain.{Fore.RESET}")
                return False

            time.sleep(5)

            # Get updated balance
            chain_id = self.web3.eth.chain_id
            token_symbol = CHAIN_SYMBOLS.get(chain_id, "A0GI")
            new_balance = self.web3.eth.get_balance(sender)
            new_balance_eth = self.web3.from_wei(new_balance, "ether")
            gas_used = initial_balance - new_balance
            gas_cost_eth = self.web3.from_wei(gas_used, "ether")

            print(
                f"7️⃣ Checking Last Balance: {Fore.YELLOW}{new_balance_eth:.8f} {token_symbol}{Fore.RESET}"
            )
            print(
                f"🤑 Final Transaction Cost: {Fore.YELLOW}{gas_cost_eth:.8f} {token_symbol}{Fore.RESET}"
            )

            if is_last_wallet:
                # Long delay after all wallets have been used
                delay_seconds = random.randint(
                    CONFIG["CYCLE_COMPLETE_DELAY"][0], CONFIG["CYCLE_COMPLETE_DELAY"][1]
                )
                print(
                    f"{Fore.GREEN}8️⃣ All wallets used! Cycle {self.cycle_count} completed. Long delay for {delay_seconds} seconds before next cycle...{Style.RESET_ALL}"
                )
                sleep_seconds(delay_seconds, "Waiting for next cycle")
                self.cycle_count += 1
            else:
                # Short delay between wallets
                delay_seconds = random.randint(
                    CONFIG["WALLET_SWITCH_DELAY"][0], CONFIG["WALLET_SWITCH_DELAY"][1]
                )
                print(
                    f"{Fore.GREEN}8️⃣ Switching to next wallet in {delay_seconds} seconds...{Style.RESET_ALL}"
                )
                sleep_seconds(delay_seconds, "Switching to next wallet")

            return True
        except Exception as e:
            log_error(f"Error executing vote: {str(e)}")
            return False

    def execute_cycle(self):
        """Execute one Vote transaction for each wallet in a cycle"""
        print(
            f"{Fore.CYAN}🔄 Starting Vote transaction cycle #{self.cycle_count} with {len(self.accounts)} wallets{Fore.RESET}"
        )

        self.update_gas_price()

        for idx, account in enumerate(self.accounts):
            wallet_num = idx + 1
            is_last_wallet = idx == len(self.accounts) - 1

            address_short = short_address(account["address"])
            print(
                f"{Fore.YELLOW}🏦 Using wallet {wallet_num}/{len(self.accounts)}: {address_short}{Fore.RESET}"
            )

            success = self.execute_vote(account, is_last_wallet)
            if not success:
                print(
                    f"{Fore.RED}Failed to execute Vote for wallet {wallet_num}. Continuing to next wallet.{Fore.RESET}"
                )

        print(
            f"{Fore.YELLOW}☑️ Vote cycle #{self.cycle_count} completed for all wallets.{Fore.RESET}"
        )
        return True


# ======================== Main Program ========================
def main():
    try:
        print_welcome_message()

        scheduler = VoteScheduler()
        scheduler.initialize()

        chain_id = is_connected(scheduler.web3)
        if chain_id:
            chain_name = CHAIN_SYMBOLS.get(chain_id, "Unknown")
            print(f"2️⃣ Connected to the network: {Fore.YELLOW}{chain_name}{Fore.RESET}")

        try:
            while True:
                scheduler.execute_cycle()
        except KeyboardInterrupt:
            print(
                f"\n{Fore.YELLOW}Script interrupted by user. Exiting gracefully.{Fore.RESET}"
            )
            return

    except Exception as e:
        log_error(f"An error occurred: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
