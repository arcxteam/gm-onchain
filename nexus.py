import time
from web3 import Web3
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Configuration for Nexus Contract and RPC
RPC_URL = 'https://rpc.nexus.xyz'
CONTRACT_ADDRESS = '0x0d95Bee83E3e8B7b585CfB1f2bdeE7A6fFfbc119'  # Nexus GM Contract Address
PRIVATE_KEY_FILE = 'private_keys.txt'  # File with private keys
MAX_RETRIES = 5  # Maximum retries for failed transactions
GAS_MULTIPLIER = 1.2  # Gas multiplier for faster transactions
COOLDOWN_ERROR = 30  # Cooldown time after an error (in seconds)
COOLDOWN_SUCCESS = 10  # Cooldown time after a successful transaction (in seconds)

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
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "lastGM",
        "outputs": [{"internalType": "uint256", "name": "lastGM", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Initialize Web3 connection
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Check if connected to the network
if not web3.is_connected():  # Perubahan: isConnected -> is_connected
    print("Failed to connect to the network.")
    exit(1)
else:
    print("Connected to the network.")

# Initialize contract
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# Debugging: Print contract functions
print("Contract functions:", contract.all_functions())

# Function to convert private key to address
def private_key_to_address(private_key):
    try:
        # Convert private key to account object
        account = web3.eth.account.from_key(private_key)
        # Return the public address
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
                key = key.strip()  # Remove extra spaces/newlines
                print(f"Attempting to load key: {key}")  # Debug: Show raw key
                # Tambahkan '0x' jika tidak ada awalan
                if not key.startswith('0x'):
                    key = '0x' + key
                # Validasi panjang private key
                if len(key) == 66 and key.startswith('0x'):
                    # Convert private key to address
                    address = private_key_to_address(key)
                    if address:
                        accounts.append({'private_key': key, 'address': address})
                        print(f"Valid key loaded: {key} -> Address: {address}")
                    else:
                        print(f"Invalid key skipped: {key}")
                else:
                    print(f"Invalid key skipped: {key}")  # Debug: Show invalid key
        if not accounts:
            raise ValueError("No valid private keys found.")
        return accounts
    except FileNotFoundError:
        print(f"Error: File '{PRIVATE_KEY_FILE}' not found.")
        exit(1)
    except Exception as e:
        print(f"Error loading private keys: {e}")
        exit(1)

# Function to handle gas price update
def get_gas_price():
    try:
        gas_price = web3.eth.gas_price
        return int(gas_price * GAS_MULTIPLIER)
    except Exception as e:
        print(f"Error fetching gas price: {e}")
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
            time.sleep(COOLDOWN_ERROR)  # Wait before retrying
    return None

# Function to build the transaction
def build_transaction(sender):
    try:
        # Get nonce for the sender account
        nonce = web3.eth.get_transaction_count(sender)
        print(f"Nonce for sender {sender}: {nonce}")

        # Build transaction data
        tx_data = {
            'from': sender,
            'to': CONTRACT_ADDRESS,
            'gas': 50000,  # Adjust gas limit if needed
            'gasPrice': get_gas_price(),
            'nonce': nonce,
            'data': contract.encodeABI(fn_name='gm'),  # Use 'gm' function
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
        sender = account['address']  # Use the public address as sender
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
    # Load accounts from private keys
    accounts = load_accounts()

    while True:
        for account in accounts:
            execute_gm(account)
            time.sleep(COOLDOWN_SUCCESS)  # Wait for a few seconds before next execution
        time.sleep(1 * 60)  # Execute the GM task every 1 minute

if __name__ == "__main__":
    main()
