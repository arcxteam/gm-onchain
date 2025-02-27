import web3
from web3 import Web3
import json
import os
import time
import datetime
import logging
from pathlib import Path
from colorama import Fore, Style, init

# Init colorama
init(autoreset=True)

# ======================== Configuration Module ========================
CONFIG = {
    "RPC_URL": "https://rpc-gel.inkonchain.com",
    "CONTRACT_ADDRESS": "0x974fBb3C286fF89d62c507204406109a686080cD",  # Updated contract address
    "PRIVATE_KEY_FILE": os.path.join(os.path.dirname(__file__), 'private_keys.txt'),
    "ENV_FILE": ".env",
    "MAX_RETRIES": 3,
    # Flexible Gas Fee Settings
    "GAS_MULTIPLIER": 1.05,   # Buffer 5% of base fee
    "MAX_PRIORITY_GWEI": 0.001,  # Max priority fee user-defined (0.001 Gwei default)
    "GAS_LIMIT": 28006,  # More accurate estimate (standard GM transaction)
    "COOLDOWN": {
        "SUCCESS": 10,
        "ERROR": 30
    },
    "WAIT_TIME": 300  # Every 5 minutes, as per the new requirement
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

# ======================== ABI Definition ========================
ABI = [
    {
        "inputs": [],
        "name": "gm",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "recipient", "type": "address"}, {"internalType": "string", "name": "message", "type": "string"}],
        "name": "gmTo",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "lastGM",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getTotalGMs",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ======================== Logging System ========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('gMfootprint')

# ======================== Utility Functions ========================
def short_address(address):
    return f"{address[:6]}...{address[-4:]}" if address else "Unknown address"

# Banner
print(f"{Fore.GREEN}============================ WELCOME TO GM ONCHAIN ============================{Fore.RESET}")
def print_welcome_message():
    welcome_banner = f"""
{Fore.YELLOW}
 ██████╗██╗   ██╗ █████╗ ███╗   ██╗███╗   ██╗ ██████╗ ██████╗ ███████╗
██╔════╝██║   ██║██╔══██╗████╗  ██║████╗  ██║██╔═══██╗██╔══██╗██╔════╝
██║     ██║   ██║███████║██╔██╗ ██║██╔██╗ ██║██║   ██║██║  ██║█████╗  
██║     ██║   ██║██╔══██║██║╚██╗██║██║╚██╗██║██║   ██║██║  ██║██╔══╝  
╚██████╗╚██████╔╝██║  ██║██║ ╚████║██║ ╚████║╚██████╔╝██████╔╝███████╗
 ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝
{Fore.RESET}
{Fore.GREEN}========================================================================={Fore.RESET}
{Fore.CYAN}         Welcome to GM-Onchain Testnet & Mainnet Auto Interactive{Fore.RESET}
{Fore.YELLOW}            - CUANNODE By Greyscope&Co, Credit By Arcxteam -{Fore.RESET}
{Fore.GREEN}========================================================================={Fore.RESET}
"""
    print(welcome_banner)
print_welcome_message()

# ===========================================================================================
def is_connected(web3):
    try:
        chain_id = web3.eth.chain_id
        print(f"1️⃣ Connected to network with chain ID: {Fore.GREEN}{chain_id}{Fore.RESET}")
        return chain_id
    except Exception as e:
        print(f"0️⃣ Failed to connect to the network: {e}")
        return None

# ======================== Core Functionality Class ========================
class GMScheduler:
    def __init__(self):
        self.accounts = []
        self.gas_price = None
        self.web3 = Web3(Web3.HTTPProvider(CONFIG["RPC_URL"]))
        self.contract = self.web3.eth.contract(address=CONFIG["CONTRACT_ADDRESS"], abi=ABI)
        
    def initialize(self):
        self.load_accounts()
        self.update_gas_price()
        
    def load_accounts(self):
        accounts = []
        
        # Try loading from .env file first if it exists
        if os.path.exists(CONFIG["ENV_FILE"]):
            try:
                from dotenv import load_dotenv
                load_dotenv(CONFIG["ENV_FILE"])
                private_key = os.getenv('PRIVATE_KEY')
                if private_key:
                    if not private_key.startswith('0x'):
                        private_key = '0x' + private_key
                    account = self.web3.eth.account.from_key(private_key)
                    accounts.append({
                        'key': private_key,
                        'address': account.address
                    })
                    print(f"3️⃣ Attempting to load wallet... {Fore.GREEN}Status: OK Gas!!!{Style.RESET_ALL}")
                    print(f"4️⃣ Wallet loaded successfully -> EVM Address: {account.address}")
            except Exception as e:
                print(f"Error loading from .env: {str(e)}")
        
        # If no accounts loaded from .env, try private_keys.txt
        if not accounts:
            try:
                if os.path.exists(CONFIG["PRIVATE_KEY_FILE"]):
                    with open(CONFIG["PRIVATE_KEY_FILE"], 'r') as file:
                        keys = [k.strip() for k in file.readlines()]
                        for k in keys:
                            if not k.startswith('0x'):
                                k = '0x' + k
                            if len(k) == 66 and k.startswith('0x'):  # 0x + 64 hex chars
                                try:
                                    account = self.web3.eth.account.from_key(k)
                                    accounts.append({
                                        'key': k,
                                        'address': account.address
                                    })
                                    print(f"3️⃣ Attempting to load wallet... {Fore.GREEN}Status: OK Gas!!!{Style.RESET_ALL}")
                                    print(f"4️⃣ Wallet loaded successfully -> EVM Address: {account.address}")
                                except Exception as e:
                                    print(f"3️⃣ Attempting to load wallet... {Fore.RED}Status: FAILED{Style.RESET_ALL}")
                                    print(f"Invalid key: {str(e)}")
                            else:
                                print(f"3️⃣ Attempting to load wallet... {Fore.RED}Status: FAILED{Style.RESET_ALL}")
                                print(f"Invalid key format: {k}")
            except Exception as e:
                print(f"Error loading private keys: {str(e)}")
                exit(1)
                
        if len(accounts) == 0:
            print("No valid private keys found in either .env or private_keys.txt")
            exit(1)
                
        self.accounts = accounts
        print(f"🔄 Successfully loaded {len(self.accounts)} accounts")
            
    def update_gas_price(self):
        try:    
            # Get base fee from blockchain (EIP-1559)
            fee_history = self.web3.eth.fee_history(1, 'latest')
            base_fee = fee_history['baseFeePerGas'][0]

            # Get max priority fee from CONFIG (can be set by user)
            max_priority = self.web3.to_wei(CONFIG["MAX_PRIORITY_GWEI"], 'gwei')

            # Use multiplier from CONFIG for max fee
            max_fee = int(base_fee * CONFIG["GAS_MULTIPLIER"]) + max_priority

            # Convert to Gwei for display
            base_fee_gwei = self.web3.from_wei(base_fee, 'gwei')
            max_fee_gwei = self.web3.from_wei(max_fee, 'gwei')
            max_priority_gwei = self.web3.from_wei(max_priority, 'gwei')

            # Calculate transaction cost in ETH
            total_cost_wei = CONFIG["GAS_LIMIT"] * max_fee
            total_cost_eth = self.web3.from_wei(total_cost_wei, 'ether')

            print(f"⚡ Gas Prices: Base Fee: {base_fee_gwei:.9f} Gwei | Max Fee: {max_fee_gwei:.9f} Gwei | Priority Fee: {max_priority_gwei:.9f} Gwei")
            print(f"🤑 Est. Transaction Cost: {Fore.YELLOW}{total_cost_eth:.9f} ETH{Fore.RESET}")

            # Store configured gas price into object variables
            self.gas_price = {'maxFeePerGas': max_fee, 'maxPriorityFeePerGas': max_priority}
            self.legacy_gas_price = int(base_fee * CONFIG["GAS_MULTIPLIER"])  # Buffer only 5%

        except Exception as e:
            # If unable to get EIP-1559 gas fee, use legacy gas price
            current = self.web3.eth.gas_price
            legacy_gas_price = int(current * CONFIG["GAS_MULTIPLIER"])
            self.gas_price = legacy_gas_price
            gas_gwei = self.web3.from_wei(legacy_gas_price, 'gwei')
            print(f"⛽ Gas price updated: {gas_gwei:.9f} Gwei (Legacy Mode) - Exception: {str(e)}")
    
    def get_wallet_balance(self, address):
        try:
            # Get chain ID to determine token symbol
            chain_id = self.web3.eth.chain_id
            token_symbol = CHAIN_SYMBOLS.get(chain_id, "ETH")  # Default to ETH if chain not found
            
            balance_wei = self.web3.eth.get_balance(address)
            balance_eth = self.web3.from_wei(balance_wei, 'ether')
            print(f"5️⃣ Checking Wallet Balance: {Fore.YELLOW}{balance_eth:.6f} {token_symbol}{Fore.RESET}")
            return balance_wei
        except Exception as e:
            print(f"Error getting balance: {str(e)}")
            return 0

    def estimate_gas(self, sender):
        try:
            # Try to estimate gas from GM function
            gas_estimate = self.contract.functions.gm().estimate_gas({'from': sender})

            # Buffer only 5% from initial estimate
            return int(gas_estimate * 1.05)  
        except Exception as e:
            print(f"⚠️ Gas estimation failed: {str(e)}. Using safe default.")
            return CONFIG["GAS_LIMIT"]  # Use standard limit as fallback
    
    def build_transaction(self, sender):
        try:
            nonce = self.web3.eth.get_transaction_count(sender, 'pending')

            # Use latest gas estimate
            gas_limit = self.estimate_gas(sender)
            print(f"🚀 Estimated gas usage: {gas_limit}")

            # If chain supports EIP-1559
            if isinstance(self.gas_price, dict):
                tx = {
                'from': sender,
                'to': CONFIG["CONTRACT_ADDRESS"],
                'gas': gas_limit,
                'maxFeePerGas': self.gas_price['maxFeePerGas'],
                'maxPriorityFeePerGas': self.gas_price['maxPriorityFeePerGas'],
                'nonce': nonce,
                'data': self.contract.encodeABI(fn_name='gm', args=[]),
                'chainId': self.web3.eth.chain_id
            }
            else:
                # Use legacy gas price if chain does not support EIP-1559
                tx = {
                'from': sender,
                'to': CONFIG["CONTRACT_ADDRESS"],
                'gas': gas_limit,
                'gasPrice': self.gas_price,
                'nonce': nonce,
                'data': self.contract.encodeABI(fn_name='gm', args=[]),
                'chainId': self.web3.eth.chain_id
            }

            print(f"🔵 Transaction OnChain Data Prepared to Say: {Fore.GREEN}hELLO...gM with nonce {nonce}{Style.RESET_ALL}")
            return tx

        except Exception as e:
            print(f"❌ Error building transaction: {str(e)}")
            return None
        
    def send_transaction(self, tx, private_key):
        global tx_counter
        retries = CONFIG["MAX_RETRIES"]
        
        while retries > 0:
            try:
                signed = self.web3.eth.account.sign_transaction(tx, private_key)
                receipt = self.web3.eth.send_raw_transaction(signed.rawTransaction)
                tx_counter += 1
                tx_hash = receipt.hex()
                print(f"6️⃣ Transaction Sent {Fore.GREEN}Successfully{Style.RESET_ALL} with Total TXiD {Fore.RED}{tx_counter}{Style.RESET_ALL} -> {Fore.GREEN}TxID Hash:{Style.RESET_ALL} {tx_hash}")
                
                # Wait for transaction receipt with timeout
                print(f"⌛ Waiting for transaction to onchain bang....")
                try:
                    tx_receipt = self.web3.eth.wait_for_transaction_receipt(receipt, timeout=120)
                    if tx_receipt.status == 1:
                        print(f"{Fore.GREEN}😎 Transaction successfully onchain!{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}🔞 Transaction failed on-chain! Check explorer for details.{Style.RESET_ALL}")
                    return tx_receipt
                except Exception as timeout_error:
                    print(f"⏱️ Timeout waiting for transaction receipt: {str(timeout_error)}")
                    print(f"🆙 Transaction may still be pending. Check hash: {tx_hash}")
                    return None
                
            except Exception as e:
                error_message = str(e)
                if "insufficient funds" in error_message.lower():
                    print(f"{Fore.RED}Error: 💰 Insufficient funds for gas * price + value{Style.RESET_ALL}")
                    return None
                elif "nonce too low" in error_message.lower():
                    # Try to get the correct nonce and update transaction
                    try:
                        new_nonce = self.web3.eth.get_transaction_count(tx['from'], 'pending')
                        tx['nonce'] = new_nonce
                        print(f"Updated nonce to {new_nonce}")
                    except Exception as nonce_error:
                        print(f"Error updating nonce: {str(nonce_error)}")
                # Check for fee-related errors that might require a slight increase
                elif "fee too low" in error_message.lower() or "underpriced" in error_message.lower():
                    # Increase fees more aggressively on this specific error
                    if isinstance(self.gas_price, dict):
                        self.gas_price['maxFeePerGas'] = int(self.gas_price['maxFeePerGas'] * 1.5)
                        self.gas_price['maxPriorityFeePerGas'] = int(self.gas_price['maxPriorityFeePerGas'] * 1.5)
                    else:
                        self.gas_price = int(self.gas_price * 1.5)
                    print(f" 🤯 Transaction fees too low. Increasing and retrying...")
                
                retries -= 1
                print(f"Error sending transaction. Retries left: {retries}. Error: {error_message}")
                if retries == 0:
                    print(f"{Fore.RED}All retry attempts failed.{Style.RESET_ALL}")
                    return None
                
                # Increase gas price on retry, but more conservatively
                if isinstance(self.gas_price, dict):
                    # Only increase by 10% on each retry unless fee-specific error
                    if "fee too low" not in error_message.lower() and "underpriced" not in error_message.lower():
                        self.gas_price['maxFeePerGas'] = int(self.gas_price['maxFeePerGas'] * 1.1)
                        self.gas_price['maxPriorityFeePerGas'] = int(self.gas_price['maxPriorityFeePerGas'] * 1.1)
                    new_max_fee_gwei = self.web3.from_wei(self.gas_price['maxFeePerGas'], 'gwei')
                    print(f"Increased gas price for retry: {new_max_fee_gwei:.6f} Gwei")
                else:
                    if "fee too low" not in error_message.lower() and "underpriced" not in error_message.lower():
                        self.gas_price = int(self.gas_price * 1.1)
                    new_gas_gwei = self.web3.from_wei(self.gas_price, 'gwei')
                    print(f"Increased gas price for retry: {new_gas_gwei:.6f} Gwei")
                
                # Update the transaction with new gas price
                if isinstance(self.gas_price, dict):
                    tx['maxFeePerGas'] = self.gas_price['maxFeePerGas']
                    tx['maxPriorityFeePerGas'] = self.gas_price['maxPriorityFeePerGas']
                else:
                    tx['gasPrice'] = self.gas_price
                
                time.sleep(CONFIG["COOLDOWN"]["ERROR"])
        
        return None

    def execute_gm(self, account):
        try:
            private_key = account['key']
            sender = account['address']
            
            # Get initial balance
            initial_balance = self.get_wallet_balance(sender)
            
            # Build and send transaction
            tx_data = self.build_transaction(sender)
            if tx_data:
                receipt = self.send_transaction(tx_data, private_key)
                if receipt and receipt.status == 1:
                    time.sleep(5)
                    
                    # Get updated balance
                    chain_id = self.web3.eth.chain_id
                    token_symbol = CHAIN_SYMBOLS.get(chain_id, "ETH")
                    new_balance = self.web3.eth.get_balance(sender)
                    new_balance_eth = self.web3.from_wei(new_balance, 'ether')
                    gas_used = initial_balance - new_balance
                    gas_cost_eth = self.web3.from_wei(gas_used, 'ether')
                    
                    print(f"7️⃣ Checking Last Balance: {Fore.YELLOW}{new_balance_eth:.8f} {token_symbol}{Fore.RESET}")
                    print(f"🤑 Transaction cost: {Fore.YELLOW}{gas_cost_eth:.8f} {token_symbol}{Fore.RESET}")
                    
                    return True
                else:
                    print(f"{Fore.RED}🤏Transaction failed or receipt not available.{Fore.RESET}")
            else:
                print("Failed to build transaction.")
        except Exception as e:
            print(f"Error executing GM: {str(e)}")
        
        return False

# ======================== Main Program ========================
def main():
    try:
        # Initialize Web3 and contract
        web3 = Web3(Web3.HTTPProvider(CONFIG["RPC_URL"]))
        contract = web3.eth.contract(address=CONFIG["CONTRACT_ADDRESS"], abi=ABI)

        # Ensure connection is successful
        chain_id = is_connected(web3)
        if not chain_id:
            print("Failed to connect to the network.")
            exit(1)
        else:
            chain_name = CHAIN_SYMBOLS.get(chain_id, "Unknown")
            print(f"2️⃣ Connected to the network: {Fore.YELLOW}{chain_name}{Fore.RESET}")

        # Initialize scheduler
        scheduler = GMScheduler()
        scheduler.initialize()

        # Execute GM every WAIT_TIME (e.g., every 5 minutes)
        while True:
            for account in scheduler.accounts:
                scheduler.execute_gm(account)  # Run GM transaction
                time.sleep(CONFIG["WAIT_TIME"])  # Wait for the configured time before next execution

        print(f"{Fore.YELLOW}☑️ All gM onchain completed. Waiting for next execution bang!!!...{Fore.RESET}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()