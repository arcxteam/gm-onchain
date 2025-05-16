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
load_dotenv()

# ======================== Configuration ========================
CONFIG = {
    "RPC_URLS": os.getenv("RPC_URLS","https://evmrpc-testnet.0g.ai,https://0g-testnet-rpc.astrostake.xyz,https://rpc.ankr.com/0g_newton",).split(","),
    "CONTRACT_ADDRESS": os.getenv("CONTRACT_ADDRESS", "0xf767ac1513742c9c46AC835E66944522c6708237"),
    "PRIVATE_KEY_FILE": os.path.join(os.path.dirname(__file__), "private_keys.txt"),
    "ENV_FILE": ".env",
    "MAX_RETRIES": 5,
    "GAS_MULTIPLIER": 0.155,
    "MAX_PRIORITY_GWEI": 1.05,
    "GAS_LIMIT": 180000,
    "GAS_MIN_GWEI": 1.05,
    "GAS_MAX_GWEI": 2.05,
    "GAS_RESET_GWEI": 3.05,
    "COOLDOWN": {"SUCCESS": (10, 30), "ERROR": (30, 60)},
    "WALLET_SWITCH_DELAY": (60, 150),  # Short delay wallet seconsd
    "CYCLE_COMPLETE_DELAY": (200, 300), # Long delay all wallets use seconsd
    "RPC_TIMEOUT": 15,  # detik
    "RPC_RETRY_DELAY": 8,  # detik
}

# ======================== Chain Symbol ========================
CHAIN_SYMBOLS = {16601: "0G"}

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
    datefmt="%H:%M:%S",)
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
        print(f"9️⃣ {Fore.GREEN}Mode airplane..Rotating sleep in {seconds} seconds...{Style.RESET_ALL}")
    time.sleep(seconds)
    
def validate_rpc_urls(urls):
    """Validate RPC URLs to ensure they are formatted correctly."""
    valid_urls = []
    for url in urls:
        url = url.strip()
        if url and url.startswith("http"):
            valid_urls.append(url)
        else:
            log_warning(f"Invalid RPC URL ignored: {url}")
    
    if not valid_urls:
        log_error("No valid RPC URL found. Using default.")
        return ["https://evmrpc-testnet.0g.ai"]
    
    return valid_urls

# ================ Print banner =================
def print_welcome_message():
    welcome_banner = f"""
{Fore.GREEN}================== WELCOME TO VOTING DAPPs ======================={Fore.RESET}
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
        print(f"1️⃣  Connected to network with chain ID: {Fore.MAGENTA}{chain_id}{Fore.RESET}")
        return chain_id
    except Exception as e:
        print(f"0️⃣  Failed to connect to the network: {e}")
        return None


# ============================ Function of Class ==================================
class VoteScheduler:
    def __init__(self):
        self.accounts = []
        self.gas_price = None
        self.web3 = None
        self.contract = None
        self.cycle_count = 1
        self.current_rpc_index = 0
        self.rpc_last_error_time = {}

    def initialize(self):
        CONFIG["RPC_URLS"] = validate_rpc_urls(CONFIG["RPC_URLS"])
        self.connect_to_rpc()
        self.load_accounts()
        self.update_gas_price()

    def connect_to_rpc(self):
        """Connect to RPC endpoint, with rotation on failure"""
        for i, rpc_url in enumerate(CONFIG["RPC_URLS"]):
            try:
                self.current_rpc_index = i
                w3 = Web3(Web3.HTTPProvider(rpc_url.strip(), request_kwargs={'timeout': CONFIG["RPC_TIMEOUT"]}))
                if w3.is_connected():
                    chain_id = w3.eth.chain_id
                    print(f"🌐 Connected to the RPC: {rpc_url}")
                    print(f"📡 Chain ID: {chain_id} - {CHAIN_SYMBOLS.get(chain_id, 'Unknown')}")
                    self.web3 = w3
                    self.contract = self.web3.eth.contract(address=CONFIG["CONTRACT_ADDRESS"], abi=ABI)
                    self.rpc_last_error_time[rpc_url] = 0
                    return True
            except Exception as e:
                print(f"⚠️ Failed to connect to RPC {rpc_url}: {str(e)}")
                self.rpc_last_error_time[rpc_url] = time.time()
        
        if not self.web3:
            print("❌ Failed to connect to all RPC endpoints.")
            raise ConnectionError("Unable to connect to 0G network. Check RPC URLs.")

    def switch_rpc(self):
        """Switch to another RPC if a problem occurs, prioritizing those that have not yet crashed"""
        old_index = self.current_rpc_index
        old_rpc = CONFIG["RPC_URLS"][old_index]
        
        now = time.time()
        available_rpcs = [
            (i, url) for i, url in enumerate(CONFIG["RPC_URLS"]) 
            if i != old_index and (url not in self.rpc_last_error_time or now - self.rpc_last_error_time[url] > 60)
        ]
        
        # gunakan semua RPC selain yang saat ini
        if not available_rpcs:
            available_rpcs = [(i, url) for i, url in enumerate(CONFIG["RPC_URLS"]) if i != old_index]
        
        if not available_rpcs:
            sleep_seconds(CONFIG["RPC_RETRY_DELAY"], "Menunggu sebelum mencoba ulang RPC yg sama bang")
            return False
        
        # random RPC
        self.current_rpc_index, new_rpc = random.choice(available_rpcs)
        
        print(f"🔄 Switch to old RPC {Fore.RED} {old_rpc} {Fore.RESET} --> {Fore.GREEN} {new_rpc} {Style.RESET_ALL}")
        
        try:
            self.web3 = Web3(Web3.HTTPProvider(new_rpc.strip(), request_kwargs={'timeout': CONFIG["RPC_TIMEOUT"]}))
            if self.web3.is_connected():
                self.contract = self.web3.eth.contract(address=CONFIG["CONTRACT_ADDRESS"], abi=ABI)
                print(f"✅ Successfully switched to RPC: {new_rpc}")
                self.rpc_last_error_time[new_rpc] = 0
                return True
        except Exception as e:
            print(f"❌ Failed to switch to RPC {new_rpc}: {str(e)}")
            self.rpc_last_error_time[new_rpc] = time.time()
            self.current_rpc_index = old_index
            return self.switch_rpc()

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
                        print(f"3️⃣ Attempting to load wallet... {Fore.GREEN}Status: OK gas Bang!!!{Style.RESET_ALL}")
                        print(f"4️⃣ Wallet loaded successfully -> EVM Address: {account.address}")
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
                            if not any(acc["address"] == account.address for acc in accounts):
                                accounts.append({"key": valid_key, "address": account.address})
                                print(f"3️⃣ Attempting to load wallet... {Fore.GREEN}Status: OK gas Bang!!!{Style.RESET_ALL}")
                                print(f"4️⃣ Wallet loaded successfully -> EVM Address: {account.address}")
                        else:
                            print(f"3️⃣ Attempting to load wallet... {Fore.RED}Status: FAILED{Style.RESET_ALL}")
                            print("Invalid key format or length")
            except Exception as e:
                log_error(f"Error loading private keys: {str(e)}")

        if not accounts:
            log_error("No valid private keys found in either .env or private_keys.txt")
            exit(1)

        self.accounts = accounts
        print(f"🔄 Successfully loaded {Fore.GREEN}{len(self.accounts)} accounts{Fore.RESET}")

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
                logger.warning("EIP-1559 is None or not yet support, falling back to legacy gas")
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
            print(f"💱 Est. Transaction Cost: {Fore.YELLOW}{total_cost_eth:.9f} {CHAIN_SYMBOLS.get(self.web3.eth.chain_id, '0G')}{Fore.RESET}")

            return {'maxFeePerGas': max_fee, 'maxPriorityFeePerGas': max_priority}
        except Exception as e:
            log_error(f"EIP-1559 gas estimation failed: {str(e)}")
            return None

    def get_legacy_gas_price(self):
        """Get legacy gas price with fallback to default value if it fails"""
        try:
            current = self.web3.eth.gas_price

            min_gas = self.web3.to_wei(CONFIG["GAS_MIN_GWEI"], "gwei")
            max_gas = self.web3.to_wei(CONFIG["GAS_MAX_GWEI"], "gwei")
                
            gas_price = int(current * CONFIG["GAS_MULTIPLIER"])
                
            if gas_price < min_gas:
                gas_price = min_gas
            elif gas_price > max_gas:
                gas_price = max_gas
            
            gas_gwei = self.web3.from_wei(gas_price, "gwei")
            print(f"⛽ Gas price: {gas_gwei:.2f} Gwei (Legacy Mode)")
            return gas_price
        
        except Exception as e:
            print(f"❌ Legacy gas estimates fail: {str(e)}")
            default_gas = self.web3.to_wei(CONFIG["GAS_MIN_GWEI"], "gwei")
            print(f"⚠️ Used price default: {CONFIG['GAS_MIN_GWEI']} Gwei")
            return default_gas

    def reset_gas_price(self):
        """Reset gas price to reasonable initial value after too many retries"""
        if isinstance(self.gas_price, dict):
            self.gas_price["maxFeePerGas"] = self.web3.to_wei(CONFIG["GAS_RESET_GWEI"], "gwei")
            self.gas_price["maxPriorityFeePerGas"] = self.web3.to_wei(1, "gwei")
            print(f"⚠️ Gas price was reset to value (EIP-1559)")
        else:
            self.gas_price = self.web3.to_wei(CONFIG["GAS_RESET_GWEI"], "gwei")
            print(f"⚠️ Gas price was reset to value (Legacy)")
        return self.gas_price
    
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
            token_symbol = CHAIN_SYMBOLS.get(chain_id, "0G")

            balance_wei = self.web3.eth.get_balance(address)
            balance_eth = self.web3.from_wei(balance_wei, "ether")
            print(f"5️⃣ Checking wallet balance: {Fore.YELLOW}{balance_eth:.6f} {token_symbol}{Fore.RESET}")
            return balance_wei
        except Exception as e:
            # Check for RPC specific errors
            if "429" in str(e) or "too many requests" in str(e).lower():
                print(f"⚠️ RPC error while checking balance. Switching RPC...")
                if self.switch_rpc():
                    return self.get_wallet_balance(address)

            log_error(f"Error getting balance: {str(e)}")
            return 0

    def estimate_gas(self, sender):
        try:
            estimate_gas = self.contract.functions.Vote().estimate_gas({"from": sender})
            final_gas = int(estimate_gas * 0.95) # add boosting
            return max(final_gas, CONFIG["GAS_LIMIT"])
        except Exception as e:
            print(f"⚠️ Gas estimation failed: {str(e)}. Using safe default.")
            return CONFIG["GAS_LIMIT"]
            
    def build_transaction(self, sender):
        try:
            nonce = self.web3.eth.get_transaction_count(sender, "pending")
            gas_limit = self.estimate_gas(sender)
            print(f"🚀 Estimated gas usage: {Fore.MAGENTA}{gas_limit}{Fore.RESET}")

            # Vote 60% and VoteWithMessage 40%
            vote_type = "Vote" if random.random() < 0.6 else "VoteWithMessage"

            tx = {
                "from": sender,
                "to": CONFIG["CONTRACT_ADDRESS"],
                "gas": gas_limit,
                "nonce": nonce,
                "chainId": self.web3.eth.chain_id,
            }

            if vote_type == "Vote":
                tx["data"] = self.contract.encodeABI(fn_name="Vote", args=[])
                print(f"🔵 Vote dApps transaction prepared")
            else:
                messages = ["ORO AI", "Zer0 Dex", "Ora", "Bagel", "Eliza OS", "Mintair", "Socrates AI", "Pond",  "Fraction-AI", "AI Arena", "Gaimin", "Alliance DAO", "DAO-AI", "Conft"]
                message = random.choice(messages)
                tx["data"] = self.contract.encodeABI(
                    fn_name="VoteWithMessage", args=[message])
                print(f"🔵 Vote With random Message (string code) transaction prepared: '{message}'")

            if isinstance(self.gas_price, dict):
                tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
            else:
                tx["gasPrice"] = self.gas_price

            print(f"🔵 Transaction onchain data with nonce -> {Fore.YELLOW}[{nonce}]{Style.RESET_ALL}")
            return tx

        except Exception as e:
            log_error(f"❌ Error building transaction: {str(e)}")
            return None

    def handle_tx_error(self, error, tx):
        """Handle transaction error and update tx if needed"""
        error_message = str(error)

        # Handle RPC throttling/limiting
        if "429" in error_message or "too many requests" in error_message.lower():
            print(f"{Fore.YELLOW}⚠️ RPC limiting requests (429). Switching RPC...{Style.RESET_ALL}")
            if self.switch_rpc():
                return tx, True
            else:
                time.sleep(CONFIG["COOLDOWN"]["ERROR"][0])
                return tx, True

        if "insufficient funds" in error_message.lower():
            print(f"{Fore.RED}Error: 💰 Insufficient funds for gas * price + value{Style.RESET_ALL}")
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

        
        elif any(msg in error_message.lower() for msg in ["fee too low", "underpriced"]):
            return self.increase_gas_price(tx, 0.5, "Transaction fees too low")
        
        # Mempool full error
        elif "mempool is full" in error_message.lower():
            print(f"{Fore.RED}⚠️ Mempool is full. Trying to switch RPC...{Style.RESET_ALL}")
            if self.switch_rpc():
                return tx, True
            else:
                # If can't switch RPC, wait longer and retry with higher gas
                time.sleep(CONFIG["COOLDOWN"]["ERROR"][0])
                if isinstance(self.gas_price, dict):
                    self.gas_price["maxFeePerGas"] = int(self.gas_price["maxFeePerGas"] * 0.5)
                    self.gas_price["maxPriorityFeePerGas"] = int(self.gas_price["maxPriorityFeePerGas"] * 0.5)
                    tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                    tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
                else:
                    self.gas_price = int(self.gas_price * 0.5)
                    tx["gasPrice"] = self.gas_price
                return self.increase_gas_price(tx, 0.5, "Mempool full")
                return tx, True

        else:
            if isinstance(self.gas_price, dict):
                self.gas_price["maxFeePerGas"] = int(self.gas_price["maxFeePerGas"] * 0.5)
                self.gas_price["maxPriorityFeePerGas"] = int(self.gas_price["maxPriorityFeePerGas"] * 0.5)

                tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]

                new_max_fee_gwei = self.web3.from_wei(self.gas_price["maxFeePerGas"], "gwei")
                print(f"🥶 Increased gas price for retry: {new_max_fee_gwei:.6f} Gwei")
            else:
                self.gas_price = int(self.gas_price * 0.5)
                tx["gasPrice"] = self.gas_price
                new_gas_gwei = self.web3.from_wei(self.gas_price, "gwei")
                print(f"🥶 Increased gas price for retry: {new_gas_gwei:.6f} Gwei")

            return tx, True

    def increase_gas_price(self, tx, factor, reason):
        max_allowed = self.web3.to_wei(CONFIG["GAS_MAX_GWEI"], "gwei")
    
        if isinstance(self.gas_price, dict):
            new_max_fee = int(self.gas_price["maxFeePerGas"] * factor)
            if new_max_fee > max_allowed:
                new_max_fee = max_allowed
            
            self.gas_price["maxFeePerGas"] = new_max_fee
            self.gas_price["maxPriorityFeePerGas"] = min(
                int(self.gas_price["maxPriorityFeePerGas"] * factor),
                self.web3.to_wei(CONFIG["MAX_PRIORITY_GWEI"], "gwei"))
        
            tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
            tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
        
            new_max_fee_gwei = self.web3.from_wei(self.gas_price["maxFeePerGas"], "gwei")
            print(f"⚠️ {reason}. Boosting to {new_max_fee_gwei:.2f} Gwei")
        else:
            new_gas_price = int(self.gas_price * factor)
            if new_gas_price > max_allowed:
                new_gas_price = max_allowed
            
            self.gas_price = new_gas_price
            tx["gasPrice"] = self.gas_price
        
            new_gas_gwei = self.web3.from_wei(self.gas_price, "gwei")
            print(f"⚠️ {reason}. Boosting to {new_gas_gwei:.2f} Gwei")
        
        return tx, True
    
    def send_transaction(self, tx, private_key):
        global tx_counter
        retries = CONFIG["MAX_RETRIES"]
        consecutive_failures = 0

        while retries > 0:
            try:
                signed = self.web3.eth.account.sign_transaction(tx, private_key)
                receipt = self.web3.eth.send_raw_transaction(signed.rawTransaction)
                tx_counter += 1
                tx_hash = receipt.hex()
                print(f"6️⃣ Transaction sent {Fore.GREEN}Successfully{Style.RESET_ALL} with total TXiD {Fore.YELLOW}[{tx_counter}]{Style.RESET_ALL} -> {Fore.GREEN}TxID Hash:{Style.RESET_ALL} {tx_hash}")

                print(f"⌛ Waiting for transaction to onchain...")
                try:
                    tx_receipt = self.web3.eth.wait_for_transaction_receipt(
                        receipt, timeout=150)
                    if tx_receipt.status == 1:
                        print(f"{Fore.GREEN}😎 Transaction successfully onchain!{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}🔞 Transaction failed on-chain! Check explorer for details.{Style.RESET_ALL}")
                    return tx_receipt
                except Exception as timeout_error:
                    print(f"⏱️ Timeout waiting for transaction receipt: {str(timeout_error)}")
                    print(f"🆙 Transaction may still be pending. {Fore.GREEN}Check HashID{Fore.RESET}: {tx_hash}")
                    return None

            except Exception as e:
                consecutive_failures += 1
            
                # Jika gagal 3x berturut-turut, reset gas price
                if consecutive_failures >= 3:
                    self.reset_gas_price()
                    consecutive_failures = 0
                
                    # Update tx dengan gas price yang di-reset
                    if "gasPrice" in tx:
                        tx["gasPrice"] = self.gas_price
                    elif "maxFeePerGas" in tx:
                        tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                        tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
                
                updated_tx, should_retry = self.handle_tx_error(e, tx)
                if not should_retry or updated_tx is None:
                    print(f"❌ Error sending transaction: {str(e)}")
                    return None

                tx = updated_tx
                retries -= 1
                print(f"⚠️ Error sending transaction. Retries left: {retries}.")

                if retries > 0:
                    delay = random.randint(CONFIG["COOLDOWN"]["ERROR"][0], CONFIG["COOLDOWN"]["ERROR"][1])
                    sleep_seconds(delay, "Waiting before retry")
        
        return None

    def execute_vote(self, account, is_last_wallet=False):
        try:
            private_key = account["key"]
            sender = account["address"]

            # Check RPC status first and switch if needed
            if not self.web3.is_connected():
                print(f"🔄 RPC connection lost, attempting to switch...")
                self.switch_rpc()

            # Get balance - handle RPC error
            try:
                initial_balance = self.get_wallet_balance(sender)
            except Exception as e:
                if "429" in str(e) or "too many requests" in str(e).lower():
                    print(f"⚠️ RPC limiting requests, switching RPC...")
                    if self.switch_rpc():
                        # Try again after switch
                        initial_balance = self.get_wallet_balance(sender)
                    else:
                        return False
                else:
                    raise  # Re-raise if it's a different error

            # Build transaction - handle RPC error
            try:
                tx_data = self.build_transaction(sender)
            except Exception as e:
                if "429" in str(e) or "too many requests" in str(e).lower():
                    print(f"⚠️ RPC limiting requests, switching RPC...")
                    if self.switch_rpc():
                        # Try again after switch
                        tx_data = self.build_transaction(sender)
                    else:
                        return False
                else:
                    raise  # Re-raise if it's a different error

            if not tx_data:
                return False

            receipt = self.send_transaction(tx_data, private_key)
            if not receipt:
                print(f"{Fore.RED}🤏 Transaction failed or receipt not available.{Fore.RESET}")
                return False

            if receipt.status != 1:
                print(f"{Fore.RED}🤏 Transaction reverted on-chain.{Fore.RESET}")
                return False

            time.sleep(5)

            # Get updated balance
            chain_id = self.web3.eth.chain_id
            token_symbol = CHAIN_SYMBOLS.get(chain_id, "0G")
            new_balance = self.web3.eth.get_balance(sender)
            new_balance_eth = self.web3.from_wei(new_balance, "ether")
            gas_used = initial_balance - new_balance
            gas_cost_eth = self.web3.from_wei(gas_used, "ether")

            print(f"7️⃣  Checking last balance: {Fore.YELLOW}{new_balance_eth:.8f} {token_symbol}{Fore.RESET}")
            print(f"🤑 Final transaction cost: {Fore.YELLOW}{gas_cost_eth:.8f} {token_symbol}{Fore.RESET}")

            if is_last_wallet:
                # Long delay after all wallets have been used
                delay_seconds = random.randint(
                    CONFIG["CYCLE_COMPLETE_DELAY"][0], CONFIG["CYCLE_COMPLETE_DELAY"][1])
                print(f"{Fore.MAGENTA}8️⃣  All wallets used! cycle {self.cycle_count} was completed. Rotate long delay in {delay_seconds} seconds for next cycle{Style.RESET_ALL}")
                sleep_seconds(delay_seconds, "Waiting for next cycle")
                self.cycle_count += 1
            else:
                # Short delay between wallets
                delay_seconds = random.randint(
                    CONFIG["WALLET_SWITCH_DELAY"][0], CONFIG["WALLET_SWITCH_DELAY"][1])
                print(f"{Fore.GREEN}8️⃣ Switching to next wallet in {delay_seconds} seconds...{Style.RESET_ALL}")
                sleep_seconds(delay_seconds, "Switching to next wallet")

            return True
        except Exception as e:
            log_error(f"Error executing vote: {str(e)}")
            return False

    def execute_cycle(self):
        """Execute one Vote transaction for each wallet in a cycle"""
        print(f"🔄 Starting vote transaction {Fore.YELLOW}CYCLE #{self.cycle_count}{Fore.RESET} with {Fore.GREEN}{len(self.accounts)} wallets{Fore.RESET}")

        # Ensure RPC is connected or switch
        if not self.web3.is_connected():
            print(f"🔄 RPC connection lost before cycle, attempting to switch...")
            if not self.switch_rpc():
                print(f"❌ Failed to find working RPC. Waiting before retry...")
                time.sleep(60)  # Wait a minute before trying the cycle again
                if not self.switch_rpc():
                    print(f"❌ Still no working RPC. Exiting cycle.")
                    return False
        
        self.update_gas_price()

        for idx, account in enumerate(self.accounts):
            wallet_num = idx + 1
            is_last_wallet = idx == len(self.accounts) - 1

            address_short = short_address(account["address"])
            print(f"🏦 Using wallet {Fore.YELLOW}[{wallet_num}/{len(self.accounts)}]{Fore.RESET} -> {Fore.GREEN}{address_short}{Fore.RESET}")

            success = self.execute_vote(account, is_last_wallet)
            if not success:
                print(f"🥵 Failed to execute vote for wallet {Fore.YELLOW}[{wallet_num}]{Fore.RESET} Continuing to next wallet.")

        print(f"☑️ Vote cycle {Fore.YELLOW}#{self.cycle_count}{Fore.RESET} completed for all wallets.")
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
            print(f"2️⃣ Connected to the network: {Fore.MAGENTA}{chain_name}{Fore.RESET}")

        try:
            while True:
                scheduler.execute_cycle()
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Script interrupted by user. Exiting gracefully.{Fore.RESET}")
            return

    except Exception as e:
        log_error(f"An error occurred: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
