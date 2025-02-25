import time
from web3 import Web3
from dotenv import load_dotenv
import os
from colorama import Fore, Style, init

# Init colorama
init(autoreset=True)

# Load environment variables from .env file
load_dotenv()

# Configuration for GMink Contract and RPC
RPC_URL = 'https://rpc-gel.inkonchain.com'
CONTRACT_ADDRESS = '0x2a5e9b3b961aF9AE375673Ab25d2270E18dB579f'  # GMink Contract Address
PRIVATE_KEY_FILE = 'private_keys.txt'  # File with private keys
ENV_FILE = '.env'  # .env file
MAX_RETRIES = 5
GAS_MULTIPLIER = 1.2
COOLDOWN_ERROR = 30
COOLDOWN_SUCCESS = 10
LOOP_WAIT_TIME = 300  # every 5m to gM txhash, you can edit this in seconds

# Initialize Web3 connection
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Transaction counter
tx_counter = 0

# Chain ID to symbol mapping
CHAIN_SYMBOLS = {
    1: "ETH",     # Ethereum Mainnet
    10: "ETH",    # Optimism
    56: "BNB",    # BNB Chain
    137: "MATIC", # Polygon
    42161: "ETH", # Arbitrum
    43114: "AVAX", # Avalanche
    10143: "MONAD", # Monad
    393: "NEXUS", # NEXUS
    1868: "ETH-SONEIUM", # Soneium Mainnet
    167000: "ETH-TAIKO", # Taiko Mainnet
    57073: "ETH-Ink", # Ink Mainnet
    # Add more chains as needed
}

# Benner benner bang
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
# Custom function to check connection
def is_connected(web3):
    try:
        chain_id = web3.eth.chain_id
        print(f"1 Connected to network with chain ID: {Fore.GREEN}{chain_id}{Fore.RESET}")
        return chain_id
    except Exception as e:
        print(f"Failed to connect to the network: {e}")
        return None

# Check if connected to the network
chain_id = is_connected(web3)
if not chain_id:
    print("Failed to connect to the network")
    exit(1)
else:
    chain_name = CHAIN_SYMBOLS.get(chain_id, "Unknown")
    print(f"2 Connected to the network: {Fore.YELLOW}{chain_name}{Fore.RESET}")

# Determine token symbol based on chain ID
token_symbol = CHAIN_SYMBOLS.get(chain_id, "ETH")  # Default to ETH if chain not found

# Load contract ABI
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

# Initialize contract
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# Function to convert private key to address
def private_key_to_address(private_key):
    try:
        account = web3.eth.account.from_key(private_key)
        return account.address
    except Exception as e:
        print(f"Error converting private key to address: {e}")
        return None

# Function to read private keys from file or env
def load_accounts():
    accounts = []
    
    # Try loading from .env file first
    try:
        if os.path.exists(ENV_FILE):
            load_dotenv(ENV_FILE)
            private_key = os.getenv('PRIVATE_KEY')
            if private_key:
                if not private_key.startswith('0x'):
                    private_key = '0x' + private_key
                address = private_key_to_address(private_key)
                if address:
                    accounts.append({'private_key': private_key, 'address': address})
                    print(f"3 Attempting to load wallet... {Fore.GREEN}Status: OK Gas!!!{Style.RESET_ALL}")
                    print(f"4 Wallet loaded successfully -> EVM Address: {address}")
    except Exception as e:
        print(f"Error loading from .env: {e}")
    
    # If no accounts loaded from .env, try private_keys.txt
    if not accounts:
        try:
            if os.path.exists(PRIVATE_KEY_FILE):
                with open(PRIVATE_KEY_FILE, 'r') as file:
                    keys = file.readlines()
                    for key in keys:
                        key = key.strip()
                        if not key.startswith('0x'):
                            key = '0x' + key
                        if len(key) == 66 and key.startswith('0x'):
                            address = private_key_to_address(key)
                            if address:
                                accounts.append({'private_key': key, 'address': address})
                                print(f"3 Attempting to load wallet... {Fore.GREEN}Status: OK Gas!!!{Style.RESET_ALL}")
                                print(f"4 Wallet loaded successfully -> EVM Address: {address}")
                            else:
                                print(f"3 Attempting to load wallet... {Fore.RED}Status: FAILED{Style.RESET_ALL}")
                        else:
                            print(f"3 Attempting to load wallet... {Fore.RED}Status: FAILED{Style.RESET_ALL}")
                            print(f"Invalid key format: {key}")
        except FileNotFoundError:
            print(f"Error: Neither .env nor {PRIVATE_KEY_FILE} found.")
            exit(1)
        except Exception as e:
            print(f"Error loading private keys: {e}")
            exit(1)
    
    if not accounts:
        print("No valid private keys found in either .env or private_keys.txt")
        exit(1)
        
    return accounts

# Function to get wallet balance
def get_wallet_balance(address):
    try:
        balance_wei = web3.eth.get_balance(address)
        balance_eth = web3.from_wei(balance_wei, 'ether')
        print(f"5 Wallet Balance: {Fore.YELLOW}{balance_eth:.4f} {token_symbol}{Fore.RESET}")
        return balance_wei
    except Exception as e:
        print(f"Error getting balance: {e}")
        return 0

# Function to get EIP-1559 gas prices
def get_gas_prices():
    try:
        fee_history = web3.eth.fee_history(1, 'latest')
        base_fee = fee_history['baseFeePerGas'][0]
        max_priority = web3.to_wei(2, 'gwei')  # Priority fees
        max_fee = base_fee + max_priority
        
        # Convert to gwei for display
        max_fee_gwei = web3.from_wei(max_fee, 'gwei')
        max_priority_gwei = web3.from_wei(max_priority, 'gwei')
        
        # Estimate gas limit for a typical transaction
        gas_estimate = 22000  # Basic transaction
        total_cost_wei = gas_estimate * max_fee
        total_cost_eth = web3.from_wei(total_cost_wei, 'ether')
        
        print(f"6 Gas Prices: Max Fee Per Gas: {max_fee_gwei:.1f} Gwei | Priority Fee: {max_priority_gwei:.1f} Gwei (Est. cost: {Fore.YELLOW}{total_cost_eth:.6f} {token_symbol}{Fore.RESET})")

        return {'maxFeePerGas': max_fee, 'maxPriorityFeePerGas': max_priority}
    except Exception as e:
        print(f"Error fetching gas prices: {e}")
        return None

# Function to send transaction with retry logic
def send_transaction(tx, private_key):
    global tx_counter
    retries = MAX_RETRIES
    while retries > 0:
        try:
            signed_tx = web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_counter += 1
            print(f"8 Transaction Sent {Fore.GREEN}Successfully{Style.RESET_ALL} with Total TXiD {Fore.RED}{tx_counter}{Style.RESET_ALL} -> {Fore.GREEN}TxID Hash:{Style.RESET_ALL} {tx_hash.hex()}")
            return tx_hash
        except Exception as e:
            retries -= 1
            print(f"Error sending transaction. Retries left: {retries}. Error: {e}")
            if retries == 0:
                raise Exception("Transaction failed after maximum retries")
            time.sleep(COOLDOWN_ERROR)
    return None

# Function to build transaction for gm
def build_gm_transaction(sender):
    try:
        # Get EIP-1559 gas prices
        gas_prices = get_gas_prices()
        if not gas_prices:
            return None
        
        # Estimate gas limit
        gas_estimate = contract.functions.gm().estimate_gas({'from': sender})
        
        # Get nonce
        nonce = web3.eth.get_transaction_count(sender, 'pending')
        
        # Build transaction data
        tx_data = {
            'from': sender,
            'to': CONTRACT_ADDRESS,
            'gas': int(gas_estimate * GAS_MULTIPLIER),
            'maxFeePerGas': gas_prices['maxFeePerGas'],
            'maxPriorityFeePerGas': gas_prices['maxPriorityFeePerGas'],
            'nonce': nonce,
            'data': contract.encodeABI(fn_name='gm', args=[]),
            'chainId': web3.eth.chain_id
        }
        
        print(f"7 Transaction OnChain Data Prepared to Say: {Fore.GREEN}hELLO gM with nonce {nonce}{Style.RESET_ALL}")
        return tx_data
    except Exception as e:
        print(f"Error building transaction: {e}")
        return None

# Function to execute the GM task
def execute_gm(account):
    try:
        private_key = account['private_key']
        sender = account['address']
        
        # Get initial balance
        initial_balance = get_wallet_balance(sender)
        
        # Build and send transaction
        tx_data = build_gm_transaction(sender)
        if tx_data:
            tx_hash = send_transaction(tx_data, private_key)
            if tx_hash:
                # Wait for transaction confirmation
                time.sleep(5)
                
                # Get updated balance
                new_balance = web3.eth.get_balance(sender)
                new_balance_eth = web3.from_wei(new_balance, 'ether')
                print(f"9 Checking Last Balance: {Fore.YELLOW}{new_balance_eth:.4f} {token_symbol}{Fore.RESET}")
                
                return True
            else:
                print("Transaction failed.")
        else:
            print("Failed to build transaction.")
    except Exception as e:
        print(f"Error executing GM: {e}")
    
    return False

# Function to display countdown
def countdown_timer(seconds):
    print(f"{Fore.CYAN}Waiting to sleep next GM...bang!!! for {seconds//60} minutes{Style.RESET_ALL}")
    for i in range(seconds, 0, -1):
        mins, secs = divmod(i, 60)
        timer = f"{Fore.YELLOW}   Countdown: {mins:02d}:{secs:02d}{Style.RESET_ALL}"
        print(timer, end="\r")
        time.sleep(1)
    print(" " * 50, end="\r")  # Clear the countdown line

# Main function to execute the schedule
def main():
    accounts = load_accounts()
    while True:
        for account in accounts:
            execute_gm(account)
            time.sleep(COOLDOWN_SUCCESS)
        
        # Wait for the next cycle with countdown
        countdown_timer(LOOP_WAIT_TIME)

if __name__ == "__main__":
    main()
