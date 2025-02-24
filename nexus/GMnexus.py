import time
from web3 import Web3
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Configuration for MONAD Contract and RPC
RPC_URL = 'https://rpc.nexus.xyz'
CONTRACT_ADDRESS = '0x06Ed963C84575F0f3508E1aC663628Fed5692B6b'  # NexusGM Contract Address
PRIVATE_KEY_FILE = 'private_keys.txt'
MAX_RETRIES = 5
GAS_MULTIPLIER = 1.2
COOLDOWN_ERROR = 30
COOLDOWN_SUCCESS = 10

# Initialize Web3 connection
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# ============================ WELCOME TO GM ONCHAIN ============================
def print_welcome_message():
    welcome_banner = """
 ██████╗██╗   ██╗ █████╗ ███╗   ██╗███╗   ██╗ ██████╗ ██████╗ ███████╗
██╔════╝██║   ██║██╔══██╗████╗  ██║████╗  ██║██╔═══██╗██╔══██╗██╔════╝
██║     ██║   ██║███████║██╔██╗ ██║██╔██╗ ██║██║   ██║██║  ██║█████╗  
██║     ██║   ██║██╔══██║██║╚██╗██║██║╚██╗██║██║   ██║██║  ██║██╔══╝  
╚██████╗╚██████╔╝██║  ██║██║ ╚████║██║ ╚████║╚██████╔╝██████╔╝███████╗
 ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝
=========================================================================
         Welcome to GM-Onchain Testnet & Mainnet Auto Interactive
            - CUANNODE By Greyscope&Co, Credit By Arcxteam -
=========================================================================
"""
    print(welcome_banner)

print_welcome_message()

# ===========================================================================================
# Custom function to check connection
def is_connected(web3):
    try:
        chain_id = web3.eth.chain_id
        print(f"Connected to network with chain ID: {chain_id}")
        return True
    except Exception as e:
        print(f"Failed to connect to the network: {e}")
        return False

# Check if connected to the network
if not is_connected(web3):
    print("Failed to connect to the network.")
    exit(1)
else:
    print("Connected to the network.")

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

# Debugging: Print contract functions
print("Contract functions:", contract.all_functions())

# Function to convert private key to address
def private_key_to_address(private_key):
    try:
        account = web3.eth.account.from_key(private_key)
        return account.address
    except Exception as e:
        print(f"Error converting private key to address: {e}")
        return None

# Function to read private keys from file
def load_accounts():
    accounts = []
    try:
        with open(PRIVATE_KEY_FILE, 'r') as file:
            keys = file.readlines()
            for key in keys:
                key = key.strip()
                print(f"Attempting to load key: {key}")
                if not key.startswith('0x'):
                    key = '0x' + key
                if len(key) == 66 and key.startswith('0x'):
                    address = private_key_to_address(key)
                    if address:
                        accounts.append({'private_key': key, 'address': address})
                        print(f"Valid key loaded: {key} -> Address: {address}")
                    else:
                        print(f"Invalid key skipped: {key}")
                else:
                    print(f"Invalid key skipped: {key}")
        if not accounts:
            raise ValueError("No valid private keys found.")
        return accounts
    except FileNotFoundError:
        print(f"Error: File '{PRIVATE_KEY_FILE}' not found.")
        exit(1)
    except Exception as e:
        print(f"Error loading private keys: {e}")
        exit(1)

# Function to get EIP-1559 gas prices
def get_gas_prices():
    try:
        fee_history = web3.eth.fee_history(1, 'latest')
        base_fee = fee_history['baseFeePerGas'][0]
        max_priority = web3.to_wei(2, 'gwei')  # Priority fees
        max_fee = base_fee + max_priority
        gas_prices = {'maxFeePerGas': max_fee, 'maxPriorityFeePerGas': max_priority}
        print(f"Fetched gas prices: {gas_prices}")
        return gas_prices
    except Exception as e:
        print(f"Error fetching gas prices: {e}")
        return None

# Function to send transaction with retry logic
def send_transaction(tx, private_key):
    retries = MAX_RETRIES
    while retries > 0:
        try:
            signed_tx = web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return tx_hash
        except Exception as e:
            retries -= 1
            print(f"Error sending transaction. Retries left: {retries}. Error: {e}")
            if retries == 0:
                raise Exception("Transaction failed after maximum retries.")
            time.sleep(COOLDOWN_ERROR)
    return None

# Function to build the transaction
def build_transaction(sender):
    try:
        # Check balances
        balance = web3.eth.get_balance(sender)
        
        # Get EIP-1559 gas prices
        gas_prices = get_gas_prices()
        if not gas_prices:
            return None
        
        # Estimate gas limit
        gas_estimate = contract.functions.gm().estimate_gas({'from': sender})
        
        # Calculate required balance
        required_balance = gas_estimate * (gas_prices['maxFeePerGas'] + gas_prices['maxPriorityFeePerGas'])
        if balance < required_balance:
            print(f"Saldo gak cukup. belilah bang: {web3.from_wei(required_balance, 'ether')} ETH")
            return None
        
        # Build transaction data
        tx_data = {
            'from': sender,
            'to': CONTRACT_ADDRESS,
            'gas': gas_estimate,
            'maxFeePerGas': gas_prices['maxFeePerGas'],
            'maxPriorityFeePerGas': gas_prices['maxPriorityFeePerGas'],
            'nonce': web3.eth.get_transaction_count(sender, 'pending'),
            'data': contract.encodeABI(fn_name='gm', args=[]),  # Ensure this is correct
            'chainId': web3.eth.chain_id
        }
        print(f"Transaction data: {tx_data}")
        return tx_data
    except Exception as e:
        print(f"Error building transaction: {e}")
        return None

# Function to execute the GM task
def execute_gm(account):
    try:
        private_key = account['private_key']
        sender = account['address']
        tx_data = build_transaction(sender)
        if tx_data:
            tx_hash = send_transaction(tx_data, private_key)
            if tx_hash:
                print(f"Transaction successful: {tx_hash.hex()}")
            else:
                print("Transaction failed.")
        else:
            print("Failed to build transaction.")
    except Exception as e:
        print(f"Error executing GM: {e}")

# Main function to execute the schedule
def main():
    accounts = load_accounts()
    while True:
        for account in accounts:
            execute_gm(account)
            time.sleep(COOLDOWN_SUCCESS)
        time.sleep(1 * 60)  # Looping 1m

if __name__ == "__main__":
    main()
