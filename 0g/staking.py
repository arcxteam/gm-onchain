import os
import time
import random
import asyncio
import json
from web3 import Web3
from dotenv import load_dotenv
from colorama import Fore, Style, init
from eth_account import Account
from datetime import datetime, timedelta

init(autoreset=True)

# ======================= CONFIG SECTION =======================
# CONFIG TIME (in seconds)
UNSTAKE_DELAY_MIN = 1000  # 16 mins
UNSTAKE_DELAY_MAX = 2000  # 33 mins
WALLET_INTERVAL_MIN = 200  # 3-4 mins
WALLET_INTERVAL_MAX = 330  # 5 mins
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
    "https://rpc-galileo.0g.ai",  # Ganti dengan RPC URL 0G Galileo Testnet
]
EXPLORER_URL = "https://chainscan-galileo.0g.ai/tx/"
WETH_ADDRESS = "0x1265ace75c199a531b7b1cd2a9666f434325d1e8"
WBTC_ADDRESS = "0x15b1121c947d1806e32c4c00e41c60bdf1b35e26"
ETH_TOKEN_ADDRESS = "0x...";  # Ganti dengan alamat token ERC20 ETH
BTC_TOKEN_ADDRESS = "0x...";  # Ganti dengan alamat token ERC20 BTC

# ABI (dari abi_weth.sol.txt)
ABI = [...]  # Tempelkan ABI dari abi_weth.sol.txt di sini

# Variables
RPC_CACHE = None
STAKE_TIMESTAMPS = {}

# ======================= BANNER =======================
print(f"{Fore.GREEN}======================= WELCOME TO 0G GALILEO TESTNET ========================{Fore.RESET}")
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
{Fore.CYAN}        Welcome to 0G Galileo Testnet Staking Interface {Fore.RESET}
{Fore.YELLOW}           - Adapted from MAGMA by Greyscope&Co -    {Fore.RESET}
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

def get_wallet_balance(web3, address, token_contract):
    """Get wallet balance of a token"""
    balance_wei = token_contract.functions.balanceOf(address).call()
    balance = web3.from_wei(balance_wei, 'ether')
    return balance

def get_reasonable_gas_price(web3):
    """Get a reasonable gas price"""
    try:
        target_gwei = random.uniform(GAS_PRICE_MIN_GWEI, GAS_PRICE_MAX_GWEI)
        final_gas_price = web3.to_wei(target_gwei, 'gwei')
        print(f"🔋 Using random gas price: {Fore.GREEN}{target_gwei:.2f} gwei{Fore.RESET}")
        return int(final_gas_price)
    except Exception as e:
        print(f"Error getting gas price: {e}. Using {Fore.GREEN}default.{Style.RESET_ALL}")
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
async def deposit_token(web3, wallet, wallet_idx, token_contract, token_address, amount, contract):
    """Deposit token to wrap into WETH/WBTC"""
    try:
        amount_wei = web3.to_wei(amount, 'ether')
        print(f"🔄 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} depositing {amount:.6f} tokens to wrap...")

        # Approve token contract to spend tokens
        approve_tx = token_contract.functions.approve(contract.address, amount_wei).build_transaction({
            'from': wallet.address,
            'nonce': web3.eth.get_transaction_count(wallet.address),
            'gas': 100000,
            'gasPrice': get_reasonable_gas_price(web3)
        })
        signed_approve_tx = wallet.sign_transaction(approve_tx)
        approve_tx_hash = await safe_send_transaction(web3, signed_approve_tx, wallet_idx)
        if not approve_tx_hash:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} failed to approve token")
            return False
        await web3.eth.wait_for_transaction_receipt(approve_tx_hash)

        # Deposit token
        deposit_tx = contract.functions.deposit(token_address, amount_wei).build_transaction({
            'from': wallet.address,
            'nonce': web3.eth.get_transaction_count(wallet.address),
            'gas': 200000,
            'gasPrice': get_reasonable_gas_price(web3)
        })
        signed_deposit_tx = wallet.sign_transaction(deposit_tx)
        deposit_tx_hash = await safe_send_transaction(web3, signed_deposit_tx, wallet_idx)
        if not deposit_tx_hash:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} failed to deposit token")
            return False

        receipt = await web3.eth.wait_for_transaction_receipt(deposit_tx_hash)
        if receipt.status != 1:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} deposit transaction failed")
            return False

        print(f"✅ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} successfully deposited {amount:.6f} tokens")
        return True
    except Exception as e:
        print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} deposit failed: {str(e)}")
        return False

async def stake_token(web3, wallet, wallet_idx, contract, token_symbol):
    """Stake WETH/WBTC with random amount"""
    try:
        # Get token balance
        balance = get_wallet_balance(web3, wallet.address, contract)
        print(f"💰 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} {token_symbol} balance: {Fore.YELLOW}{balance:.6f}{Style.RESET_ALL}")
        
        # Generate random amount to stake
        amount_float = get_random_amount()
        amount_wei = web3.to_wei(amount_float, 'ether')
        
        # Check if enough balance
        if balance < amount_float:
            print(f"{Fore.RED}❌ Wallet {wallet_idx} insufficient {token_symbol} balance for staking{Style.RESET_ALL}")
            return None
        
        print(f"🔄 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} staking {Fore.MAGENTA}{amount_float:.6f} {token_symbol}{Style.RESET_ALL}")
        
        # Approve contract to spend tokens
        approve_tx = contract.functions.approve(contract.address, amount_wei).build_transaction({
            'from': wallet.address,
            'nonce': web3.eth.get_transaction_count(wallet.address),
            'gas': 100000,
            'gasPrice': get_reasonable_gas_price(web3)
        })
        signed_approve_tx = wallet.sign_transaction(approve_tx)
        approve_tx_hash = await safe_send_transaction(web3, signed_approve_tx, wallet_idx)
        if not approve_tx_hash:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} failed to approve {token_symbol}")
            return None
        await web3.eth.wait_for_transaction_receipt(approve_tx_hash)

        # Prepare staking transaction
        tx = contract.functions.stake(amount_wei).build_transaction({
            'from': wallet.address,
            'nonce': web3.eth.get_transaction_count(wallet.address),
            'gas': GAS_LIMIT_STAKE,
            'gasPrice': get_reasonable_gas_price(web3)
        })
        
        # Sign and send transaction
        print(f"✅ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} sending stake transaction...")
        signed_tx = wallet.sign_transaction(tx)
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
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} stake transaction {Fore.RED}failed{Style.RESET_ALL}")
            return None
        
        # Get new balance
        new_balance = get_wallet_balance(web3, wallet.address, contract)
        print(f"✅ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} {Fore.GREEN}STAKING was successful!{Style.RESET_ALL}")
        print(f"💰 Updated {token_symbol} balance: {Fore.YELLOW}{new_balance:.6f}{Style.RESET_ALL}")
        
        # Record stake timestamp and amount
        current_time = datetime.now()
        STAKE_TIMESTAMPS[wallet.address] = {
            'time': current_time,
            'amount': amount_wei
        }
        print(f"📝 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} stake timestamp recorded: {Fore.MAGENTA}{current_time.strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        
        return {'receipt': receipt, 'stake_amount': amount_wei}
    
    except Exception as e:
        print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} {Fore.RED}STAKING failed: {str(e)}{Style.RESET_ALL}")
        return None

async def unstake_token(web3, wallet, wallet_idx, contract, token_symbol):
    """Unstake WETH/WBTC tokens"""
    try:
        # Check if we have a record of the stake
        if wallet.address not in STAKE_TIMESTAMPS:
            print(f"⚠️  Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} no stake timestamp found. Using default amount")
            amount_to_unstake = web3.to_wei(MIN_STAKE_AMOUNT, 'ether')
        else:
            amount_to_unstake = STAKE_TIMESTAMPS[wallet.address]['amount']
        
        amount_eth = web3.from_wei(amount_to_unstake, 'ether')
        print(f"🔄 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} unstaking: {Fore.YELLOW}{amount_eth:.6f} {token_symbol}{Style.RESET_ALL}")
        
        # Prepare unstaking transaction
        tx = contract.functions.unstake(amount_to_unstake).build_transaction({
            'from': wallet.address,
            'nonce': web3.eth.get_transaction_count(wallet.address),
            'gas': GAS_LIMIT_UNSTAKE,
            'gasPrice': get_reasonable_gas_price(web3)
        })
        
        # Sign and send transaction
        print(f"✅ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} sending unstake transaction...")
        signed_tx = wallet.sign_transaction(tx)
        tx_hash = await safe_send_transaction(web3, signed_tx, wallet_idx)
        
        if not tx_hash:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} failed to send unstake transaction...")
            return False
        
        tx_hash_hex = web3.to_hex(tx_hash)
        print(f" $ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} transaction HashID: {Fore.MAGENTA}{tx_hash_hex}{Style.RESET_ALL}")
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
        new_balance = get_wallet_balance(web3, wallet.address, contract)
        print(f"💰 Updated {token_symbol} balance after unstake: {Fore.YELLOW}{new_balance:.6f}{Style.RESET_ALL}")
        
        return True
    
    except Exception as e:
        print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} {Fore.RED}UNSTAKE failed: {str(e)}{Style.RESET_ALL}")
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
        
        # Initialize contracts
        weth_contract = web3.eth.contract(address=WETH_ADDRESS, abi=ABI)
        wbtc_contract = web3.eth.contract(address=WBTC_ADDRESS, abi=ABI)
        eth_contract = web3.eth.contract(address=ETH_TOKEN_ADDRESS, abi=ABI)
        btc_contract = web3.eth.contract(address=BTC_TOKEN_ADDRESS, abi=ABI)

        # Step 1: Wrap ETH to WETH
        eth_balance = get_wallet_balance(web3, wallet.address, eth_contract)
        print(f"💰 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} ETH balance: {Fore.YELLOW}{eth_balance:.6f}{Style.RESET_ALL}")
        if eth_balance >= 10:
            await deposit_token(web3, wallet, wallet_idx, eth_contract, ETH_TOKEN_ADDRESS, 10, weth_contract)

        # Step 2: Wrap BTC to WBTC
        btc_balance = get_wallet_balance(web3, wallet.address, btc_contract)
        print(f"💰 Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} BTC balance: {Fore.YELLOW}{btc_balance:.6f}{Style.RESET_ALL}")
        if btc_balance >= 0.2:
            await deposit_token(web3, wallet, wallet_idx, btc_contract, BTC_TOKEN_ADDRESS, 0.2, wbtc_contract)

        # Step 3: Stake WETH
        result_weth = await stake_token(web3, wallet, wallet_idx, weth_contract, "WETH")
        if not result_weth:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} WETH staking failed, skipping this cycle")
            return False

        # Step 4: Stake WBTC
        result_wbtc = await stake_token(web3, wallet, wallet_idx, wbtc_contract, "WBTC")
        if not result_wbtc:
            print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} WBTC staking failed, skipping this cycle")
            return False

        # Wait before unstaking with random time
        unstake_delay = get_random_delay(UNSTAKE_DELAY_MIN, UNSTAKE_DELAY_MAX)
        print(f"⏳ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} waiting {unstake_delay} seconds before unstaking...")
        await sleep_seconds(unstake_delay, wallet_idx)
        
        # Step 5: Unstake WETH
        unstake_weth_success = await unstake_token(web3, wallet, wallet_idx, weth_contract, "WETH")
        if not unstake_weth_success:
            print(f"⚠️ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} WETH unstake failed")
            return False

        # Step 6: Unstake WBTC
        unstake_wbtc_success = await unstake_token(web3, wallet, wallet_idx, wbtc_contract, "WBTC")
        if not unstake_wbtc_success:
            print(f"⚠️ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} WBTC unstake failed")
            return False

        print(f"\n ✅ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} cycle {Fore.YELLOW}[{cycle}]{Fore.RESET} {Fore.GREEN}completed successfully!{Style.RESET_ALL}\n")
        return True
        
    except Exception as e:
        print(f"❌ Wallet {Fore.YELLOW}[{wallet_idx}]{Fore.RESET} cycle {Fore.YELLOW}[{cycle}]{Fore.RESET} failed: {str(e)}{Style.RESET_ALL}")
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
        
        print(f"🚀 Starting 0G Galileo Testnet Staking Automation...")
        print(f"ℹ️ Using {'EIP-1559' if USE_EIP1559 else 'Legacy'} transaction type{Style.RESET_ALL}")
        
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
        print(f"\n{Fore.MAGENTA}Thank you for using 0G Galileo Staking Automation{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Script interrupted by user. Exiting...{Style.RESET_ALL}")
