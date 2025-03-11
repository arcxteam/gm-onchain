import os
import time
import random
import asyncio
import json
from web3 import Web3
from dotenv import load_dotenv
from colorama import Fore, Style, init
from web3.middleware import geth_poa_middleware
from eth_account import Account
from datetime import datetime, timedelta

init(autoreset=True)

# ======================= CONFIG SECTION =======================
# CONFIG TIME (in seconds)
UNSTAKE_DELAY_MIN = 1000  # 16mins
UNSTAKE_DELAY_MAX = 2000  # 33mins
WALLET_INTERVAL_MIN = 200  # 3-4mins
WALLET_INTERVAL_MAX = 330  # 5-mins
RETRY_DELAY = 33
MAX_RETRIES = 3

# CONFIG STAKING
MIN_STAKE_AMOUNT = 0.101
MAX_STAKE_AMOUNT = 0.122

# CONFIG GLOBAL
CONTINUOUS_RUNNING = True
MAX_CYCLES = 9999

# CONFIG GAS
GAS_LIMIT_STAKE = 88888
GAS_LIMIT_UNSTAKE = 98888
GAS_PRICE_MIN_GWEI = 50
GAS_PRICE_MAX_GWEI = 52
USE_EIP1559 = True  # True/False EIP-1559 or legacy

# CONFIG RPC & CONTRACT
RPC_URLS = [
    "https://testnet-rpc.monad.xyz", 
    "https://monad-testnet.drpc.org"
]
EXPLORER_URL = "https://testnet.monadexplorer.com/tx/"
CONTRACT_ADDRESS = "0x2c9C959516e9AAEdB2C748224a41249202ca8BE7"

# FUNCTION SIGN
STAKE_SELECTOR = "0xd5575982"
UNSTAKE_SELECTOR = "0x6fed1ea7"

# Variables
RPC_CACHE = None
STAKE_TIMESTAMPS = {}

# ======================= BANNER BANG =======================

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
{Fore.CYAN}        Welcome to MONAD Onchain Testnet & Mainnet Interactive {Fore.RESET}
{Fore.YELLOW}           - CUANNODE By Greyscope&Co, Credit By 0xgr3y -    {Fore.RESET}
{Fore.GREEN}========================================================================={Fore.RESET}
"""
    print(welcome_banner)
print_welcome_message()

# ======================= UTILITY FUNCTIONS =======================

def get_random_delay(min_delay, max_delay):
    """Generate random delay between min and max"""
    return random.randint(min_delay, max_delay)

def connect_to_rpc():
    """Connect to one of the RPC URLs"""
    global RPC_CACHE
    if RPC_CACHE:
        try:
            RPC_CACHE.eth.chain_id
            print(f"🔄 Already Connected to RPC URL: {Fore.GREEN}{RPC_CACHE.provider.endpoint_uri}{Style.RESET_ALL}")
            return RPC_CACHE
        except:
            RPC_CACHE = None
            print(f"{Fore.RED}RPC connection lost, reconnecting...{Style.RESET_ALL}")

    random.shuffle(RPC_URLS)
    
    for url in RPC_URLS:
        try:
            web3 = Web3(Web3.HTTPProvider(url))
            # Add middleware for PoA chains if needed
            web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            if web3.is_connected():
                print(f"📶 Connected to RPC URL: {Fore.GREEN}{url}{Style.RESET_ALL}")
                RPC_CACHE = web3
                return web3
        except Exception as e:
            print(f"{Fore.RED}Failed to connect to {url}: {e}{Style.RESET_ALL}")

    raise Exception("Unable to connect to any RPC URL.")

def load_private_keys():
    """Load private keys from environment variable and file"""
    private_keys = []

    # Load from environment variable
    env_private_key = os.getenv("PRIVATE_KEY")
    if env_private_key:
        private_keys.append(env_private_key.strip())

    # Try to load from private_keys.txt
    try:
        with open("private_keys.txt", "r") as file:
            keys = [line.strip() for line in file.readlines()]
            private_keys.extend(keys)
    except Exception as e:
        print(f"{Fore.YELLOW}Note: private_keys.txt not found or couldn't be read: {e}{Style.RESET_ALL}")

    if not private_keys:
        raise Exception("No private keys found in .env or private_keys.txt")

    private_keys = [k if k.startswith("0x") else "0x" + k for k in private_keys]
    
    print(f"📸 Loaded {len(private_keys)} wallet(s) {Fore.GREEN}successfully{Style.RESET_ALL}")
    
    # Return unique keys
    return list(set(private_keys))

def get_wallet_balance(web3, address):
    """Get wallet balance in MON"""
    balance_wei = web3.eth.get_balance(address)
    balance_eth = web3.from_wei(balance_wei, 'ether')
    return balance_eth

def get_reasonable_gas_price(web3):
    """Get a reasonable gas price"""
    try:
        # Generate random gas price
        target_gwei = random.uniform(GAS_PRICE_MIN_GWEI, GAS_PRICE_MAX_GWEI)
        final_gas_price = web3.to_wei(target_gwei, 'gwei')
        
        print(f"🔋 Using random gas price: {Fore.GREEN}{target_gwei:.2f} gwei{Fore.RESET}")
        return int(final_gas_price)
    except Exception as e:
        print(f" Error getting gas price: {e}. Using {Fore.GREEN}default.{Style.RESET_ALL}")
        # Fallback to default gas price if there's an error
        default_gwei = 51
        return int(web3.to_wei(default_gwei, 'gwei'))

def get_random_amount():
    """Generate random amount between MIN_STAKE_AMOUNT and MAX_STAKE_AMOUNT"""
    random_amount = random.uniform(MIN_STAKE_AMOUNT, MAX_STAKE_AMOUNT)
    return random_amount

async def sleep_seconds(seconds, wallet_idx=None):
    """Sleep with a nice message"""
    wallet_str = f"Wallet {wallet_idx} " if wallet_idx is not None else ""
    print(f"🛏️  {Fore.GREEN} {wallet_str}sleeping in {seconds} seconds...{Style.RESET_ALL}")
    await asyncio.sleep(seconds)

# ======================= TRANSACTION FUNCTIONS =======================

async def stake_mon(web3, wallet, wallet_idx):
    """Stake MON with random amount"""
    try:
        # Get account balance
        balance = get_wallet_balance(web3, wallet.address)
        print(f"💰 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} checking balance: {Fore.YELLOW}{balance:.6f} MON{Style.RESET_ALL}")
        
        # Generate random amount to stake
        amount_float = get_random_amount()
        amount_wei = web3.to_wei(amount_float, 'ether')
        
        # Check if enough balance
        if balance < amount_float + 0.01:
            print(f"{Fore.RED}❌ Wallet {wallet_idx} insufficient balance for staking{Style.RESET_ALL}")
            return None
        
        print(f"🔄 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} be ready staking: {Fore.MAGENTA}{amount_float:.6f} MON{Style.RESET_ALL}")
        
        # Get gas price
        gas_price = get_reasonable_gas_price(web3)
        
        # Prepare transaction
        contract_address = Web3.to_checksum_address(CONTRACT_ADDRESS)
        
        if USE_EIP1559:
            # Use EIP-1559 transaction
            base_fee = web3.eth.get_block('latest')['baseFeePerGas']
            max_priority_fee = web3.to_wei(2, 'gwei')
            max_fee = base_fee * 2 + max_priority_fee
            
            tx = {
                'from': wallet.address,
                'to': contract_address,
                'value': amount_wei,
                'gas': GAS_LIMIT_STAKE,
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': max_priority_fee,
                'nonce': web3.eth.get_transaction_count(wallet.address),
                'chainId': web3.eth.chain_id,
                'type': '0x2',  # EIP-1559
                'data': STAKE_SELECTOR
            }
        else:
            # Use legacy
            tx = {
                'from': wallet.address,
                'to': contract_address,
                'value': amount_wei,
                'gas': GAS_LIMIT_STAKE,
                'gasPrice': gas_price,
                'nonce': web3.eth.get_transaction_count(wallet.address),
                'chainId': web3.eth.chain_id,
                'data': STAKE_SELECTOR
            }
        
        # Sign and send transaction
        print(f"✅ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} sending stake transaction...")
        signed_tx = wallet.sign_transaction(tx)
        
        # Send with retries
        tx_hash = await safe_send_transaction(web3, signed_tx, wallet_idx)
        
        if not tx_hash:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} failed to send stake transaction")
            return None
        
        tx_hash_hex = web3.to_hex(tx_hash)
        print(f" $ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} transaction HashID: {Fore.MAGENTA}{tx_hash_hex}{Style.RESET_ALL}")
        print(f" $ {EXPLORER_URL}{tx_hash_hex}")
        
        # Wait for confirmation
        print(f"⏳ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} waiting for confirmation...")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET}stake transaction {Fore.RED}failed{Style.RESET_ALL}")
            return None
        
        # Get new balance
        new_balance = get_wallet_balance(web3, wallet.address)
        print(f"✅ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} {Fore.GREEN}STAKING was successful!{Style.RESET_ALL}")
        print(f"💰 Update new balance: {Fore.YELLOW}{new_balance:.6f} MON{Style.RESET_ALL}")
        
        # Record stake timestamp and amount
        current_time = datetime.now()
        STAKE_TIMESTAMPS[wallet.address] = {
            'time': current_time,
            'amount': amount_wei
        }
        print(f"📝 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} stake timestamp recorded: {Fore.MAGENTA}{current_time.strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        
        return {'receipt': receipt, 'stake_amount': amount_wei}
    
    except Exception as e:
        print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} {Fore.RED}STAKING was failed! {str(e)}{Style.RESET_ALL}")
        return None

async def unstake_gmon(web3, wallet, wallet_idx):
    """Unstake gMON tokens"""
    try:
        # Check if we have a record of the stake
        if wallet.address not in STAKE_TIMESTAMPS:
            print(f"⚠️  Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} no stake timestamp found. Using default amount")
            amount_to_unstake = web3.to_wei(MIN_STAKE_AMOUNT, 'ether')
        else:
            amount_to_unstake = STAKE_TIMESTAMPS[wallet.address]['amount']
        
        amount_eth = web3.from_wei(amount_to_unstake, 'ether')
        print(f"🔄 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} unstaking: {Fore.YELLOW}{amount_eth:.6f} gMON{Style.RESET_ALL}")
        
        # Prepare data field - function
        amount_hex = hex(amount_to_unstake)[2:].zfill(64)
        data = UNSTAKE_SELECTOR + amount_hex
        
        # Get gas price
        gas_price = get_reasonable_gas_price(web3)
        
        # Prepare transaction
        contract_address = Web3.to_checksum_address(CONTRACT_ADDRESS)
        
        if USE_EIP1559:
            # Use EIP-1559 transaction
            base_fee = web3.eth.get_block('latest')['baseFeePerGas']
            max_priority_fee = web3.to_wei(2, 'gwei')
            max_fee = base_fee * 2 + max_priority_fee
            
            tx = {
                'from': wallet.address,
                'to': contract_address,
                'value': 0,
                'gas': GAS_LIMIT_UNSTAKE,
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': max_priority_fee,
                'nonce': web3.eth.get_transaction_count(wallet.address),
                'chainId': web3.eth.chain_id,
                'type': '0x2',  # EIP-1559
                'data': data
            }
        else:
            # Use legacy transaction type
            tx = {
                'from': wallet.address,
                'to': contract_address,
                'value': 0,
                'gas': GAS_LIMIT_UNSTAKE,
                'gasPrice': gas_price,
                'nonce': web3.eth.get_transaction_count(wallet.address),
                'chainId': web3.eth.chain_id,
                'data': data
            }
        
        # Sign and send transaction
        print(f"✅ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} sending unstake transaction...")
        signed_tx = wallet.sign_transaction(tx)
        
        # Send with retries
        tx_hash = await safe_send_transaction(web3, signed_tx, wallet_idx)
        
        if not tx_hash:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} failed to send unstake transaction...")
            return False
        
        tx_hash_hex = web3.to_hex(tx_hash)
        print(f" $ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} transaction hashID: {Fore.MAGENTA}{tx_hash_hex}{Style.RESET_ALL}")
        print(f" $ {EXPLORER_URL}{tx_hash_hex}")
        
        # Wait for confirmation
        print(f"⏳ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} waiting for confirmation...")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} unstake transaction failed...")
            return False
        
        # Clear the stake timestamp record
        if wallet.address in STAKE_TIMESTAMPS:
            del STAKE_TIMESTAMPS[wallet.address]
        
        print(f"✅ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} {Fore.GREEN}UNSTAKE was successful!{Style.RESET_ALL}")
        
        # Get new balance after unstaking
        new_balance = get_wallet_balance(web3, wallet.address)
        print(f"💰 Update new balance after unstake: {Fore.YELLOW}{new_balance:.6f} MON{Style.RESET_ALL}")
        
        return True
    
    except Exception as e:
        print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} {Fore.RED}UNSTAKE was failed! {str(e)}{Style.RESET_ALL}")
        return False

async def safe_send_transaction(web3, signed_tx, wallet_idx, retries=3):
    """Send transaction with retries"""
    for i in range(retries):
        try:
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return tx_hash
        except Exception as e:
            error_str = str(e)
            print(f"Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} transaction failed (attempt {i+1}/{retries}): {error_str}")
            
            # Check for specific error conditions
            if "nonce too low" in error_str.lower():
                print(f"Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} nonce error detected - {Fore.MAGENTA}possibly transaction processed{Style.RESET_ALL}")
                return None
            elif "insufficient funds" in error_str.lower():
                print(f"Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} insufficient funds error - stopping retries")
                return None
                
            if i < retries - 1:
                wait_time = 3 * (i + 1)
                print(f"Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} waiting {wait_time} seconds before {Fore.MAGENTA}RETRY...{Style.RESET_ALL}")
                await asyncio.sleep(wait_time)
    
    print(f"{Fore.RED}🥵 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} transaction ultimately failed after {retries} retries.{Style.RESET_ALL}")
    return None

# ======================= CYCLE FUNCTIONS =======================

async def process_wallet(wallet, wallet_idx, cycle):
    """Process the full cycle for a wallet"""
    try:
        print(f"\n ======== {Fore.YELLOW} WALLET [{wallet_idx}]{Fore.RESET} {Fore.MAGENTA}{wallet.address[:8]}...{wallet.address[-6:]}{Fore.RESET} {Fore.YELLOW}CYCLE [{cycle}] {Style.RESET_ALL} ========\n")
        
        web3 = connect_to_rpc()
        
        # Step 1: Stake MON
        result = await stake_mon(web3, wallet, wallet_idx)
        if not result:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} staking failed, skipping this cycle")
            return False
        
        # Wait before unstaking with random time
        unstake_delay = get_random_delay(UNSTAKE_DELAY_MIN, UNSTAKE_DELAY_MAX)
        print(f"⏳ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} waiting {unstake_delay} seconds before unstaking...")
        await sleep_seconds(unstake_delay, wallet_idx)
        
        # Step 2: Unstake gMON
        unstake_success = await unstake_gmon(web3, wallet, wallet_idx)
        
        if unstake_success:
            print(f"\n ✅ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} cycle {Fore.YELLOW}[{cycle}]{Fore.RESET} WTF are {Fore.GREEN}complete.................!!!{Style.RESET_ALL}\n")
            return True
        else:
            print(f"\n ⚠️ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} cycle {Fore.YELLOW}[{cycle}]{Fore.RESET} unstake are partially\n")
            return False
        
    except Exception as e:
        print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} cycle {Fore.YELLOW}[{cycle}]{Fore.RESET} WTF are {Fore.RED}failed................!!!{str(e)}{Style.RESET_ALL}")
        return False
    
async def run_wallet_continuously(wallet, wallet_idx):
    """Run wallet process continuously"""
    cycle = 1
    
    while True:
        try:
            success = await process_wallet(wallet, wallet_idx, cycle)
            cycle += 1
            
            # Add a random delay between cycles for the same wallet
            inter_cycle_delay = random.randint(21, 61)  # 21-61 seconds
            print(f"⏳ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} waiting {inter_cycle_delay} seconds before next cycle...")
            await sleep_seconds(inter_cycle_delay, wallet_idx)
            
        except Exception as e:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} encountered critical error: {str(e)}{Style.RESET_ALL}")
            print(f"⚠️ Waiting {RETRY_DELAY} seconds before retry...{Style.RESET_ALL}")
            await sleep_seconds(RETRY_DELAY, wallet_idx)

# ======================= MAIN FUNCTIONS =======================

async def main():
    """Main entry point - runs all wallets in parallel"""
    try:
        private_keys = load_private_keys()
        
        print(f"🚀  Starting {Fore.MAGENTA}MAGMA{Fore.RESET} Liquid Staking Unstaking Automation bang...")
        print(f"ℹ️  Using {'EIP-1559' if USE_EIP1559 else 'Legacy'} transaction type{Style.RESET_ALL}")
        
        tasks = []
        
        # Start process for each wallet with a small delay
        for idx, private_key in enumerate(private_keys):
            wallet = Account.from_key(private_key)
            print(f"🔑 Preparing wallet {Fore.YELLOW}[{idx+1}/{len(private_keys)}]{Fore.RESET}: {Fore.MAGENTA}{wallet.address}{Style.RESET_ALL}")
            
            task = asyncio.create_task(run_wallet_continuously(wallet, idx+1))
            tasks.append(task)
            
            # Random delay before starting next wallet process
            if idx < len(private_keys) - 1:
                wallet_interval = get_random_delay(WALLET_INTERVAL_MIN, WALLET_INTERVAL_MAX)
                print(f"⏳ Waiting {Fore.MAGENTA}{wallet_interval} seconds{Fore.RESET} before starting next wallet...")
                await sleep_seconds(wallet_interval)
        
        await asyncio.gather(*tasks)
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Script interrupted by user. Exiting...{Style.RESET_ALL}")
    
    except Exception as e:
        print(f"\n{Fore.RED}❌ Operation failed: {str(e)}{Style.RESET_ALL}")
    
    finally:
        print(f"\n{Fore.MAGENTA}Thank you for using MAGMA Staking utomation{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Script interrupted by user. Exiting...{Style.RESET_ALL}")
