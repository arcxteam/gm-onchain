import web3
from web3 import Web3
import json
import os
import time
import datetime
import pytz
import logging
import random
from pathlib import Path
from colorama import Fore, Style, init
from dotenv import load_dotenv

# Init colorama
init(autoreset=True)

# ======================== Configuration Module ========================
CONFIG = {
    "RPC_URL": "https://testnet-rpc.monad.xyz",
    "CONTRACT_ADDRESS": "0x0aaa9532B950392f86D2e3871068C23ef34D6774",
    "PRIVATE_KEY_FILE": os.path.join(os.path.dirname(__file__), 'private_keys.txt'),
    "ENV_FILE": ".env",
    "MAX_RETRIES": 3,
    
    # Gas settings
    "GAS_MULTIPLIER": 1.05,
    "MAX_PRIORITY_GWEI": 0.002,
    "GAS_LIMIT": 29000,
    "GAS_VARIATION_RANGE": (0.90, 1.05),  # Random gas multiplier
    
    # Cooldown for errors and success
    "COOLDOWN": {
        "SUCCESS": 10,
        "ERROR": 30
    },
    
    # Human-like delays
    "WALLET_SWITCH_DELAY_MEAN": 88,     # Mean in seconds (75 seconds)
    "WALLET_SWITCH_DELAY_STD": 38,      # Standard deviation (25 seconds)
    "WALLET_SWITCH_DELAY_MIN": 68,      # Minimum delay between wallets
    "WALLET_SWITCH_DELAY_MAX": 248,     # Maximum delay between wallets
    
    # Cycle complete delays
    "CYCLE_COMPLETE_DELAY_MEAN": 2000,  # Mean in seconds (35 minutes)
    "CYCLE_COMPLETE_DELAY_STD": 600,    # Standard deviation (10 minutes)
    "CYCLE_COMPLETE_DELAY_MIN": 1200,   # Minimum cycle delay (20 minutes)
    "CYCLE_COMPLETE_DELAY_MAX": 3600,   # Maximum cycle delay (60 minutes)
    
    # Nighttime delay factor (3AM - 8AM UTC)
    "NIGHT_TIME_START_HOUR": 3,
    "NIGHT_TIME_END_HOUR": 8,
    "NIGHT_TIME_DELAY_FACTOR": 2.0,
    
    # Wallet behavior
    "SKIP_WALLET_PROBABILITY": 0.04,    # 4% chance to skip a wallet in a cycle
    "FAST_TX_PROBABILITY": 0.08         # 8% chance of a "rushed" transaction
}

# ======================== Chain Symbol Mapping ========================
CHAIN_SYMBOLS = {
    1: "ETH",
    10: "ETH-Optimism",
    1135: "ETH-Lisk",
    480: "ETH-Worldchain",
    8453: "ETH-Base",
    130: "ETH-Unichain",
    10143: "MONAD",
    393: "NEXUS",
    1868: "ETH-Soneium",
    167000: "ETH-Taiko",
    57073: "ETH-Ink",
    5330: "ETH-Superseed",
    34443: "ETH-Mode",
    690: "ETH-Redstone",
}

# Transaction counter
tx_counter = 0

# ======================== ABI Contract ========================
ABI = [
    {
        "inputs": [],
        "name": "Vote",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "message", "type": "string"}],
        "name": "VoteWithMessage",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "recipient", "type": "address"}, {"internalType": "string", "name": "message", "type": "string"}],
        "name": "VoteForRecipient",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# ======================== Info Logging ========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('VoteFootprint')

# Custom log functions to maintain emoji format
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

def human_delay(mean, std_dev, min_val, max_val):
    """Generate a human-like delay based on normal distribution"""
    # Use normal distribution for more human-like randomness
    delay = int(random.gauss(mean, std_dev))
    delay = max(min_val, min(max_val, delay))
    return delay
    
def is_night_time():
    """Check if current time is within the defined night hours (UTC)"""
    utc_timezone = pytz.utc
    current_hour = datetime.datetime.now(utc_timezone).hour
    return CONFIG["NIGHT_TIME_START_HOUR"] <= current_hour < CONFIG["NIGHT_TIME_END_HOUR"]

def apply_night_time_factor(delay_seconds):
    """Apply night time factor to delay if applicable"""
    if is_night_time():
        night_factor = CONFIG["NIGHT_TIME_DELAY_FACTOR"]
        return int(delay_seconds * night_factor)
    return delay_seconds

def sleep_seconds(seconds, message=None):
    """Sleep with a message, showing a human-friendly countdown"""
    if message:
        print(f"9️⃣ {Fore.GREEN}{message} in {seconds} seconds...{Style.RESET_ALL}")
    else:
        print(f"9️⃣ {Fore.GREEN}Mode airplane..Rotating sleep in {seconds} seconds...{Style.RESET_ALL}")
        
    # For long delays, show progress
    if seconds > 500:  # 9 minutes
        start_time = time.time()
        while time.time() - start_time < seconds:
            elapsed = time.time() - start_time
            remaining = seconds - elapsed
            if remaining <= 0:
                break
                
            minutes_remaining = int(remaining // 60)
            if minutes_remaining > 0 and minutes_remaining % 15 == 0:  # Update every 15 minutes
                print(f"⏳ {Fore.YELLOW}Waiting... Approximately {minutes_remaining} minutes remaining{Style.RESET_ALL}")
            
            time.sleep(min(30, remaining))
    else:
        # For shorter delays, just sleep
        time.sleep(seconds)

# Print bang banner
def print_welcome_message():
    welcome_banner = f"""
{Fore.GREEN}========================= WELCOME TO VOTING DAPPs ======================={Fore.RESET}
{Fore.YELLOW}
 ██████╗██╗   ██╗ █████╗ ███╗   ██╗███╗   ██╗ ██████╗ ██████╗ ███████╗
██╔════╝██║   ██║██╔══██╗████╗  ██║████╗  ██║██╔═══██╗██╔══██╗██╔════╝
██║     ██║   ██║███████║██╔██╗ ██║██╔██╗ ██║██║   ██║██║  ██║█████╗  
██║     ██║   ██║██╔══██║██║╚██╗██║██║╚██╗██║██║   ██║██║  ██║██╔══╝  
╚██████╗╚██████╔╝██║  ██║██║ ╚████║██║ ╚████║╚██████╔╝██████╔╝███████╗
 ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝
{Fore.RESET}
{Fore.GREEN}========================================================================={Fore.RESET}
{Fore.MAGENTA}        Welcome to Voting Onchain Testnet & Mainnet Interactive {Fore.RESET}
{Fore.YELLOW}          - CUANNODE By Greyscope&Co, Credit By Arcxteam -    {Fore.RESET}
{Fore.GREEN}========================================================================={Fore.RESET}
"""
    print(welcome_banner)

# ============================ Connection Web3 Wallet ===================================
def is_connected(web3):
    try:
        chain_id = web3.eth.chain_id
        print(f"1️⃣ Connected to network with chain ID: {Fore.MAGENTA}{chain_id}{Fore.RESET}")
        return chain_id
    except Exception as e:
        print(f"0️⃣ Failed to connect to the network: {e}")
        return None
        
# ============================ Functionality Class ==================================
class VoteScheduler:
    def __init__(self):
        self.accounts = []
        self.gas_price = None
        self.web3 = Web3(Web3.HTTPProvider(CONFIG["RPC_URL"]))
        self.contract = self.web3.eth.contract(address=CONFIG["CONTRACT_ADDRESS"], abi=ABI)
        self.cycle_count = 1
        
    def build_transaction(self, sender):
        try:
            # Add small random delay to simulate human thinking
            time.sleep(random.uniform(0.8, 6.5))
            
            nonce = self.web3.eth.get_transaction_count(sender, 'pending')
            gas_limit = self.estimate_gas(sender)
            print(f"🚀 Estimated gas usage: {Fore.MAGENTA}{gas_limit}{Fore.RESET}")

            # Base transaction params
            tx = {
                'from': sender,
                'to': CONFIG["CONTRACT_ADDRESS"],
                'gas': gas_limit,
                'nonce': nonce,
                'data': self.contract.encodeABI(fn_name='Vote', args=[]),
                'chainId': self.web3.eth.chain_id
            }

            # Add either EIP-1559 or legacy gas params
            if isinstance(self.gas_price, dict):
                tx['maxFeePerGas'] = self.gas_price['maxFeePerGas']
                tx['maxPriorityFeePerGas'] = self.gas_price['maxPriorityFeePerGas']
            else:
                tx['gasPrice'] = self.gas_price

            print(f"🔵 Transaction OnChain prepared: {Fore.GREEN}Already...Voting-Dapps with nonce ->{Fore.RESET} {Fore.MAGENTA}{nonce}{Style.RESET_ALL}")
            return tx

        except Exception as e:
            log_error(f"❌ Error building transaction: {str(e)}")
            return None
    
    def initialize(self):
        self.load_accounts()
        self.update_gas_price()
    
    def is_valid_private_key(self, key):
        """Validate a private key format and return standardized key"""
        try:
            # Skip empty lines and comments
            if not key or key.startswith('#'):
                return None
                
            # Standardize key format (add 0x if missing)
            if not key.startswith('0x'):
                key = '0x' + key
                
            # Validate key length (private key is 32 bytes = 64 chars + '0x' prefix = 66 chars)
            if len(key) != 66:
                return None
                
            # Final validation - try to derive an account
            self.web3.eth.account.from_key(key)
            return key
        except Exception:
            return None
            
    def load_accounts(self):
        accounts = []
        
        # Try loading from .env first
        if os.path.exists(CONFIG["ENV_FILE"]):
            try:
                load_dotenv(CONFIG["ENV_FILE"])
                private_key = os.getenv('PRIVATE_KEY')
                if private_key:
                    valid_key = self.is_valid_private_key(private_key)
                    if valid_key:
                        account = self.web3.eth.account.from_key(valid_key)
                        accounts.append({
                            'key': valid_key,
                            'address': account.address
                        })
                        print(f"3️⃣ Attempting to load wallet... {Fore.GREEN}Status: OK Gas!!!{Style.RESET_ALL}")
                        print(f"4️⃣ Wallet loaded successfully -> EVM Address: {Fore.MAGENTA}{account.address}{Fore.YELLOW}")
            except Exception as e:
                log_error(f"Error loading from .env: {str(e)}")
        
        # Then try loading from private_keys.txt
        if os.path.exists(CONFIG["PRIVATE_KEY_FILE"]):
            try:
                with open(CONFIG["PRIVATE_KEY_FILE"], 'r') as file:
                    keys = [line.strip() for line in file.readlines()]
                    for key in keys:
                        valid_key = self.is_valid_private_key(key)
                        if valid_key:
                            account = self.web3.eth.account.from_key(valid_key)
                            # Check if account already exists (avoid duplicates)
                            if not any(acc['address'] == account.address for acc in accounts):
                                accounts.append({
                                    'key': valid_key,
                                    'address': account.address
                                })
                                print(f"3️⃣ Attempting to load wallet... {Fore.GREEN}Status: OK Gas!!!{Style.RESET_ALL}")
                                print(f"4️⃣ Wallet loaded successfully -> EVM Address: {Fore.MAGENTA}{account.address}{Fore.YELLOW}")
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
    
    def get_eip1559_gas_params(self, is_rushed=False):
        """Get EIP-1559 gas parameters"""
        try:
            # Get base fee from blockchain
            fee_history = self.web3.eth.fee_history(1, 'latest')
            base_fee = fee_history['baseFeePerGas'][0]

            # Get max priority fee from CONFIG
            max_priority = self.web3.to_wei(CONFIG["MAX_PRIORITY_GWEI"], 'gwei')

            # Apply random variation to gas multiplier for more human-like behavior
            gas_multiplier = CONFIG["GAS_MULTIPLIER"]
            if is_rushed:
                # "Rushed" transaction - use higher gas (up to 30% higher)
                gas_multiplier *= random.uniform(1.15, 1.2)
                print(f"🚀 {Fore.YELLOW}In a hurry! Using higher gas price for this transaction{Style.RESET_ALL}")
            else:
                # Normal variation
                gas_multiplier *= random.uniform(CONFIG["GAS_VARIATION_RANGE"][0], CONFIG["GAS_VARIATION_RANGE"][1])

            # Use multiplier for max fee
            max_fee = int(base_fee * gas_multiplier) + max_priority

            # Convert to Gwei for display
            base_fee_gwei = self.web3.from_wei(base_fee, 'gwei')
            max_fee_gwei = self.web3.from_wei(max_fee, 'gwei')
            max_priority_gwei = self.web3.from_wei(max_priority, 'gwei')

            # Calculate transaction cost in ETH
            total_cost_wei = CONFIG["GAS_LIMIT"] * max_fee
            total_cost_eth = self.web3.from_wei(total_cost_wei, 'ether')

            print(f"⛽ Gas Prices: Base Fee: {base_fee_gwei:.9f} Gwei | Max Fee: {max_fee_gwei:.9f} Gwei | Priority Fee: {max_priority_gwei:.9f} Gwei")
            print(f"💱 Est. Transaction Cost: {Fore.MAGENTA}{total_cost_eth:.9f} MON{Fore.RESET}")

            return {'maxFeePerGas': max_fee, 'maxPriorityFeePerGas': max_priority}
        except Exception as e:
            log_error(f"EIP-1559 gas estimation failed: {str(e)}")
            return None
            
    def get_legacy_gas_price(self, is_rushed=False):
        """Get legacy gas price"""
        try:
            current = self.web3.eth.gas_price
            gas_multiplier = CONFIG["GAS_MULTIPLIER"]
            
            if is_rushed:
                # "Rushed" transaction - use higher gas (up to 30% higher)
                gas_multiplier *= random.uniform(1.15, 1.2)
                print(f"🚀 {Fore.YELLOW}Dont worry! Using higher gas price for this transaction{Style.RESET_ALL}")
            else:
                # Normal variation
                gas_multiplier *= random.uniform(CONFIG["GAS_VARIATION_RANGE"][0], CONFIG["GAS_VARIATION_RANGE"][1])
                
            gas_price = int(current * gas_multiplier)
            gas_gwei = self.web3.from_wei(gas_price, 'gwei')
            print(f"⚡ Gas price updated: {gas_gwei:.9f} Gwei (Legacy Mode)")
            return gas_price
        except Exception as e:
            log_error(f"Legacy gas estimation failed: {str(e)}")
            return self.web3.to_wei(50, 'gwei')
    
    def update_gas_price(self, is_rushed=False):
        """Update gas price with EIP-1559 or legacy mode"""
        # Try EIP-1559 first
        eip1559_params = self.get_eip1559_gas_params(is_rushed)
        if eip1559_params:
            self.gas_price = eip1559_params
        else:
            # Fallback to legacy
            self.gas_price = self.get_legacy_gas_price(is_rushed)
    
    def get_wallet_balance(self, address):
        try:
            # Get chain ID to determine token symbol
            chain_id = self.web3.eth.chain_id
            token_symbol = CHAIN_SYMBOLS.get(chain_id, "ETH")
            
            balance_wei = self.web3.eth.get_balance(address)
            balance_eth = self.web3.from_wei(balance_wei, 'ether')
            print(f"5️⃣  Checking Wallet Balance: {Fore.YELLOW}{balance_eth:.6f} {token_symbol}{Fore.RESET}")
            return balance_wei
        except Exception as e:
            log_error(f"Error getting balance: {str(e)}")
            return 0

    def estimate_gas(self, sender):
        try:
            gas_estimate = self.contract.functions.Vote().estimate_gas({'from': sender})
            # Apply slight random variation to gas limit (±5%)
            variation = random.uniform(0.90, 1.05)
            return int(gas_estimate * variation)
        except Exception as e:
            print(f"⚠️ Gas estimation failed: {str(e)}. Using safe default.")
            # Apply slight random variation to default gas limit (±5%)
            variation = random.uniform(0.90, 1.05)
            return int(CONFIG["GAS_LIMIT"] * variation)
            
    def handle_tx_error(self, error, tx):
        """Handle transaction error and update tx if needed"""
        error_message = str(error)
        
        # Insufficient funds error
        if "insufficient funds" in error_message.lower():
            print(f"{Fore.RED}Error: 💰 Insufficient funds for gas * price + value{Style.RESET_ALL}")
            return None, False
            
        # Nonce too low error
        elif "nonce too low" in error_message.lower():
            try:
                new_nonce = self.web3.eth.get_transaction_count(tx['from'], 'pending')
                tx['nonce'] = new_nonce
                print(f"Updated nonce to {new_nonce}")
                return tx, True
            except Exception as nonce_error:
                log_error(f"Error updating nonce: {str(nonce_error)}")
                return None, False
                
        # Fee too low error
        elif any(msg in error_message.lower() for msg in ["fee too low", "underpriced"]):
            if isinstance(self.gas_price, dict):
                self.gas_price['maxFeePerGas'] = int(self.gas_price['maxFeePerGas'] * 1.5)
                self.gas_price['maxPriorityFeePerGas'] = int(self.gas_price['maxPriorityFeePerGas'] * 1.5)
                
                tx['maxFeePerGas'] = self.gas_price['maxFeePerGas']
                tx['maxPriorityFeePerGas'] = self.gas_price['maxPriorityFeePerGas']
                
                new_max_fee_gwei = self.web3.from_wei(self.gas_price['maxFeePerGas'], 'gwei')
                print(f" 🤯 Transaction fees too low. Increased to {new_max_fee_gwei:.6f} Gwei")
            else:
                self.gas_price = int(self.gas_price * 1.5)
                tx['gasPrice'] = self.gas_price
                new_gas_gwei = self.web3.from_wei(self.gas_price, 'gwei')
                print(f" 🤯 Transaction fees too low. Increased to {new_gas_gwei:.6f} Gwei")
                
            return tx, True
            
        # General case: increase gas slightly and retry
        else:
            if isinstance(self.gas_price, dict):
                self.gas_price['maxFeePerGas'] = int(self.gas_price['maxFeePerGas'] * 1.1)
                self.gas_price['maxPriorityFeePerGas'] = int(self.gas_price['maxPriorityFeePerGas'] * 1.1)
                
                tx['maxFeePerGas'] = self.gas_price['maxFeePerGas']
                tx['maxPriorityFeePerGas'] = self.gas_price['maxPriorityFeePerGas']
                
                new_max_fee_gwei = self.web3.from_wei(self.gas_price['maxFeePerGas'], 'gwei')
                print(f"Increased gas price for retry: {new_max_fee_gwei:.6f} Gwei")
            else:
                self.gas_price = int(self.gas_price * 1.1)
                tx['gasPrice'] = self.gas_price
                new_gas_gwei = self.web3.from_wei(self.gas_price, 'gwei')
                print(f"Increased gas price for retry: {new_gas_gwei:.6f} Gwei")
                
            return tx, True
        
    def send_transaction(self, tx, private_key):
        global tx_counter
        retries = CONFIG["MAX_RETRIES"]
        
        while retries > 0:
            try:
                # Short random delay before signing (simulates human review)
                time.sleep(random.uniform(1.0, 3.0))
                
                signed = self.web3.eth.account.sign_transaction(tx, private_key)
                receipt = self.web3.eth.send_raw_transaction(signed.rawTransaction)
                tx_counter += 1
                tx_hash = receipt.hex()
                print(f"6️⃣ Transaction sent {Fore.GREEN}Successfully{Style.RESET_ALL} with total TXiD {Fore.YELLOW}[{tx_counter}]{Style.RESET_ALL} -> {Fore.MAGENTA}TxID Hash:{Style.RESET_ALL} {tx_hash}")
                
                print(f"⌛ Waiting for transaction to onchain bang....")
                try:
                    tx_receipt = self.web3.eth.wait_for_transaction_receipt(receipt, timeout=120)
                    if tx_receipt.status == 1:
                        print(f"{Fore.GREEN}😎 Transaction successfully onchain!{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}🔞 Transaction failed onchain! Check explorer for details.{Style.RESET_ALL}")
                    return tx_receipt
                except Exception as timeout_error:
                    print(f"⏱️ Timeout waiting for transaction receipt: {str(timeout_error)}")
                    print(f"🆙 Transaction may still be pending. Check hash: {tx_hash}")
                    return None
                
            except Exception as e:
                updated_tx, should_retry = self.handle_tx_error(e, tx)
                
                if not should_retry:
                    return None
                    
                tx = updated_tx  # Update transaction with new parameters
                retries -= 1
                print(f"Error sending transaction. Retries left: {retries}. Error: {str(e)}")
                
                if retries == 0:
                    print(f"{Fore.RED}All retry attempts failed.{Style.RESET_ALL}")
                    return None
                
                # Randomize error cooldown slightly
                error_cooldown = CONFIG["COOLDOWN"]["ERROR"] * random.uniform(0.8, 1.2)
                time.sleep(error_cooldown)
        
        return None
        
    def execute_vote(self, account, is_last_wallet=False):
        try:
            private_key = account['key']
            sender = account['address']
            
            # Decide if this transaction will be "rushed" (higher gas)
            is_rushed = random.random() < CONFIG["FAST_TX_PROBABILITY"]
            
            # Update gas price for this specific transaction
            self.update_gas_price(is_rushed)
            
            # Get initial balance
            initial_balance = self.get_wallet_balance(sender)
            
            tx_data = self.build_transaction(sender)
            if not tx_data:
                return False
                
            receipt = self.send_transaction(tx_data, private_key)
            if not receipt or receipt.status != 1:
                print(f"{Fore.RED}🤏 Transaction failed..is the canceled on purpose a variable patterns.{Fore.RESET}")
                return False
                
            # Add a short random delay after transaction (simulating checking tx status)
            time.sleep(random.uniform(3.0, 8.0))
            
            # Get updated balance
            chain_id = self.web3.eth.chain_id
            token_symbol = CHAIN_SYMBOLS.get(chain_id, "ETH")
            new_balance = self.web3.eth.get_balance(sender)
            new_balance_eth = self.web3.from_wei(new_balance, 'ether')
            gas_used = initial_balance - new_balance
            gas_cost_eth = self.web3.from_wei(gas_used, 'ether')
            
            print(f"7️⃣ Checking Last Balance: {Fore.YELLOW}{new_balance_eth:.8f} {token_symbol}{Fore.RESET}")
            print(f"🤑 Final Transaction Cost: {Fore.MAGENTA}{gas_cost_eth:.8f} {token_symbol}{Fore.RESET}")
            
            # If this is the last wallet in the cycle, apply long delay
            # Otherwise apply short delay between wallets
            if is_last_wallet:
                # Calculate human-like delay between cycles with night time factor
                delay_seconds = human_delay(
                    CONFIG["CYCLE_COMPLETE_DELAY_MEAN"],
                    CONFIG["CYCLE_COMPLETE_DELAY_STD"],
                    CONFIG["CYCLE_COMPLETE_DELAY_MIN"],
                    CONFIG["CYCLE_COMPLETE_DELAY_MAX"]
                )
                
                # Check if it's night time and apply factor if needed
                delay_seconds = apply_night_time_factor(delay_seconds)
                
                # Convert to minutes for display
                delay_minutes = delay_seconds // 60
                
                if is_night_time():
                    print(f"{Fore.MAGENTA}🌙 Night time detected (UTC). Applying longer delay.{Style.RESET_ALL}")
                
                print(f"8️⃣ All wallets used! {Fore.MAGENTA}cycle #{self.cycle_count}{Fore.RESET} completed. Taking a break for {Fore.MAGENTA}[{delay_minutes} minutes]{Fore.RESET} before next cycle...{Style.RESET_ALL}")
                sleep_seconds(delay_seconds, f"Waiting for {Fore.MAGENTA}cycle #{self.cycle_count + 1}{Fore.RESET}")
                self.cycle_count += 1
            else:
                # Calculate human-like delay between wallets
                delay_seconds = human_delay(
                    CONFIG["WALLET_SWITCH_DELAY_MEAN"],
                    CONFIG["WALLET_SWITCH_DELAY_STD"],
                    CONFIG["WALLET_SWITCH_DELAY_MIN"],
                    CONFIG["WALLET_SWITCH_DELAY_MAX"]
                )
                
                # Check if it's night time and apply factor if needed
                delay_seconds = apply_night_time_factor(delay_seconds)
                
                print(f"{Fore.GREEN}8️⃣ Taking a short break before next wallet ({delay_seconds} seconds)...{Style.RESET_ALL}")
                sleep_seconds(delay_seconds, "Preparing next wallet")
            
            return True
        except Exception as e:
            log_error(f"Error executing Voting: {str(e)}")
            return False

    def execute_cycle(self):
        """Execute one Voting transaction for each wallet in a cycle"""
        print(f"🔄 Starting voting transaction {Fore.MAGENTA}cycle #{self.cycle_count}{Fore.RESET} with {Fore.YELLOW}{len(self.accounts)} wallets{Fore.RESET}")
        
        # Check if it's night time
        if is_night_time():
            print(f"{Fore.MAGENTA}🌙 Operating during night hours (UTC {CONFIG['NIGHT_TIME_START_HOUR']}:00-{CONFIG['NIGHT_TIME_END_HOUR']}:00). "
                  f"Delays will be {CONFIG['NIGHT_TIME_DELAY_FACTOR']}x longer{Style.RESET_ALL}")
        
        # Update gas price at the start of each cycle
        self.update_gas_price()
        
        # Shuffle the accounts for more natural behavior
        shuffled_accounts = self.accounts.copy()
        random.shuffle(shuffled_accounts)
        
        # Process each account
        processed_count = 0
        for idx, account in enumerate(shuffled_accounts):
            # Randomly decide whether to skip this wallet
            if random.random() < CONFIG["SKIP_WALLET_PROBABILITY"]:
                address_short = short_address(account['address'])
                print(f"⏭️ {Fore.MAGENTA}Randomly skipping wallet {Fore.YELLOW}{address_short}{Fore.RESET} this cycle (USE Variable HUMAN-LIKE for NATURAL TRANSACTIONS){Style.RESET_ALL}")
                continue
                
            processed_count += 1
            wallet_num = idx + 1
            # Last wallet check considers actually executed wallets, not just position in list
            is_last_wallet = (processed_count == len(shuffled_accounts) - sum(1 for _ in shuffled_accounts if random.random() < CONFIG["SKIP_WALLET_PROBABILITY"]))
            
            address_short = short_address(account['address'])
            print(f"🏦 Now the ATM using wallet {Fore.MAGENTA}[{wallet_num}/{len(shuffled_accounts)}]{Fore.RESET} -> {Fore.YELLOW}{address_short}{Fore.RESET}")
            
            # Add a small random delay before processing (simulates human decision time)
            time.sleep(random.uniform(2.0, 5.0))
            
            success = self.execute_vote(account, is_last_wallet)
            if not success:
                print(f"{Fore.RED}❌ Failed to execute Voting for{Fore.RESET} {Fore.YELLOW}wallet {wallet_num}.{Fore.RESET} Continuing to next wallet.")
        
        print(f"{Fore.YELLOW}☑️ Vote cycle {Fore.MAGENTA}[#{self.cycle_count}]{Fore.RESET} completed with {processed_count} wallet(s).{Fore.RESET}")
        return True
        
# ======================== Main Program ========================
def main():
    try:
        print_welcome_message()
        
        # Initialize Web3 and contract
        web3 = Web3(Web3.HTTPProvider(CONFIG["RPC_URL"]))
        contract = web3.eth.contract(address=CONFIG["CONTRACT_ADDRESS"], abi=ABI)
        
        chain_id = is_connected(web3)
        if not chain_id:
            log_error("Failed to connect to the network.")
            exit(1)
        else:
            chain_name = CHAIN_SYMBOLS.get(chain_id, "Unknown")
            print(f"2️⃣ Connected to the network: {Fore.YELLOW}{chain_name}{Fore.RESET}")

        # Initialize scheduler rotating
        scheduler = VoteScheduler()
        scheduler.initialize()

        # Display natural behavior notification
        print(f"\n{Fore.YELLOW}🧠 Running with natural human-like a variable behavior patterns:{Fore.RESET}")
        print(f"  • Random wallet selection and ordering")
        print(f"  • Varied gas prices ({CONFIG['GAS_VARIATION_RANGE'][0]:.2f}x-{CONFIG['GAS_VARIATION_RANGE'][1]:.2f}x normal)")
        print(f"  • Boosting rushed transactions ({int(CONFIG['FAST_TX_PROBABILITY']*100)}% chance)")
        print(f"  • Random wallet skipping ({int(CONFIG['SKIP_WALLET_PROBABILITY']*100)}% chance)")
        print(f"  • Add Night-time hours (UTC {CONFIG['NIGHT_TIME_START_HOUR']}:00-{CONFIG['NIGHT_TIME_END_HOUR']}:00) will have {CONFIG['NIGHT_TIME_DELAY_FACTOR']}x longer delays")
        print(f"  • Variable human-like delays between actions\n")

        # Execute Vote in rotating wallet mode with efficient cycles
        try:
            print(f"{Fore.GREEN}⚡ Vote Onchain is now running.{Fore.RESET} {Fore.YELLOW}Press Ctrl+C to cancel.{Fore.RESET}")
            while True:
                scheduler.execute_cycle()
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Script interrupted by user. Exiting what the fuck.{Fore.RESET}")
            return
        
    except Exception as e:
        log_error(f"An error occurred: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
