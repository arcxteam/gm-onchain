import os
import random
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
import colorama
from colorama import Fore, Style
import asyncio

# Banner bang!!
print(f"{Fore.GREEN}======================= WELCOME TO MONAD ONCHAIN ========================{Fore.RESET}")
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
{Fore.CYAN}         Welcome to MONAD Onchain Testnet & Mainnet Auto Interactive{Fore.RESET}
{Fore.YELLOW}            - CUANNODE By Greyscope&Co, Credit By Arcxteam -{Fore.RESET}
{Fore.GREEN}========================================================================={Fore.RESET}
"""
    print(welcome_banner)
print_welcome_message()

# Load own wallet .env
load_dotenv()
private_key = os.getenv('PRIVATE_KEY')

if not private_key:
    print(Fore.RED + 'Not found private keys .env')
    exit(1)

network = {
    "name": "Monad Testnet",
    "chainId": 10143,
    "rpc": "https://testnet-rpc.monad.xyz",
    "symbol": "MON",
    "explorer": "https://testnet.monadexplorer.com"
}

# connected to web3
w3 = Web3(Web3.HTTPProvider(network["rpc"]))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

if not w3.is_connected():
    print(Fore.RED + f"Disconnect to chain {network['name']}")
    exit(1)

def generate_new_wallet():
    account = Account.create()
    return {
        "address": account.address,
        "private_key": account.key.hex()
    }

def check_balance(address):
    balance = w3.eth.get_balance(address)
    return w3.from_wei(balance, 'ether')

async def transfer_tokens(wallet_address, private_key, index, wallets_data):
    new_wallet = generate_new_wallet()
    wallets_data.append({
        "index": index + 1,
        "address": new_wallet["address"],
        "private_key": new_wallet["private_key"]
    })
    
    random_amount = max(random.uniform(0.0001, 0.001), 0.0001)
    rounded_amount = round(random_amount, 6)
    
    # crated tx/id
    nonce = w3.eth.get_transaction_count(wallet_address)
    amount_in_wei = int(rounded_amount * 10**6)
    
    tx = {
        'nonce': nonce,
        'to': new_wallet["address"],
        'value': amount_in_wei,
        'gas': 21000,
        'gasPrice': w3.eth.gas_price,
        'chainId': network["chainId"]
    }
    
    # sign wallet
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    short_address = new_wallet["address"][-5:]
    print(Fore.YELLOW + f"🟣 ({index + 1}/2) [ALRAEDY] : {rounded_amount} {network['symbol']} sent to {short_address} : TXiD/Hash {tx_hash.hex()}")
    
    wallets_data[-1].update({
        "tx_hash": tx_hash.hex(),
        "amount": rounded_amount,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return tx_receipt

# save wallet to JSON
def save_wallets_to_json(wallets_data):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"monad_wallets_{timestamp}.json"
    with open(filename, 'w') as file:
        json.dump(wallets_data, file, indent=4)
    
    return filename

async def handle_token_transfers():
    account = Account.from_key(private_key)
    wallet_address = account.address
    
    print(Fore.BLUE + f"🔎 TRY AUTO GENERATE WALLET & SEND ANY $MONAD 💭💭💭")
    print(" ")
    
    wallets_data = []
    
    # Try to 11 address transfer with delay random 60s-420s
    for i in range(50):
        await transfer_tokens(wallet_address, private_key, i, wallets_data)
        delay = random.randint(60, 420)
        time.sleep(delay)
    
    filename = save_wallets_to_json(wallets_data)
    
    print(Fore.GREEN + "✅ \nAll transactions completed successfully!")
    print(Fore.YELLOW + f"📝 Wallet data saved to {filename}")
    
    print(Fore.GREEN + "\nChecking MONAD balances of all generated wallets...")
    for wallet in wallets_data:
        balance = check_balance(wallet["address"])
        print(Fore.RED + f"🤑 Wallet {wallet['address']} balance: {balance} {network['symbol']}")

# Eksekusi main
if __name__ == "__main__":
    try:
        asyncio.run(handle_token_transfers())
    except Exception as e:
        print(Fore.RED + f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
