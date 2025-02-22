# nexus.py
import time
from web3 import Web3
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Setup Web3 provider
web3 = Web3(Web3.HTTPProvider(os.getenv('PROVIDER_URL')))
contract_address = os.getenv('CONTRACT_ADDRESS')
private_key = os.getenv('PRIVATE_KEY')

# Contract ABI (paste ABI here)
abi = []

account = web3.eth.account.privateKeyToAccount(private_key)
contract = web3.eth.contract(address=contract_address, abi=abi)

def send_transaction():
    data = contract.functions.gm().encodeABI()

    tx = {
        'to': contract_address,
        'data': data,
        'gas': 2000000,
        'gasPrice': web3.eth.gas_price  # Get gas price dynamically
    }

    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    print(f"Transaction sent with hash: {tx_hash.hex()}")

# Run every 3 minutes
while True:
    send_transaction()
    time.sleep(3 * 60)  # 3 minutes
