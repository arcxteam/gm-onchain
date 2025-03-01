import os
import random
import time
from web3 import Web3
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)

# Load environment variables from .env file
load_dotenv()

RPC_URLS = [
    "https://testnet-rpc.monad.xyz",
    "https://monad-testnet.drpc.org",
    "https://monad-testnet.blockvision.org/v1/2td1EBS890QoVDhdSdd0Q1OlEGw"
]
CHAIN_ID = 10143
UNISWAP_V2_ROUTER_ADDRESS = Web3.to_checksum_address("0xCa810D095e90Daae6e867c19DF6D9A8C56db2c89")
WMON_ADDRESS = Web3.to_checksum_address("0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701")

TOKEN_ADDRESSES = {
    "DAK": Web3.to_checksum_address("0x0f0bdebf0f83cd1ee3974779bcb7315f9808c714"),
    "USDT": Web3.to_checksum_address("0x88b8e2161dedc77ef4ab7585569d2415a1c1055d"),
    "ETH": Web3.to_checksum_address("0x836047a99e11f376522b447bffb6e3495dd0637c"),
    "WETH": Web3.to_checksum_address("0xB5a30b0FDc5EA94A52fDc42e3E9760Cb8449Fb37"),
    "YAKI": Web3.to_checksum_address("0xfe140e1dCe99Be9F4F15d657CD9b7BF622270C50"),
    "USDC": Web3.to_checksum_address("0xf817257fed379853cDe0fa4F97AB987181B1E5Ea"),
    "CHOG": Web3.to_checksum_address("0xE0590015A873bF326bd645c3E1266d4db41C4E6B")
}

erc20_abi = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

# ABI utuk router
router_abi = [
    # Use Method swapExactETHForTokens
    {
        "name": "swapExactETHForTokens",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]
    },
    # Use method execute
    {
        "name": "execute",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {"internalType": "bytes", "name": "data", "type": "bytes"}
        ],
        "outputs": []
    },
    # Use Method multicall
    {
        "name": "multicall",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {"internalType": "bytes[]", "name": "data", "type": "bytes[]"}
        ],
        "outputs": [{"internalType": "bytes[]", "name": "results", "type": "bytes[]"}]
    },
    # Use method swap
    {
        "name": "swap",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {"internalType": "address", "name": "tokenIn", "type": "address"},
            {"internalType": "address", "name": "tokenOut", "type": "address"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"}
        ],
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}]
    }
]

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

# ============================ Connection Web3 Wallet ===================================

RPC_CACHE = None

def connect_to_rpc():
    global RPC_CACHE
    if RPC_CACHE:
        print(f"1 🔄 Already Connected to RPC URL: {RPC_CACHE.provider.endpoint_uri}")
        return RPC_CACHE

    for url in RPC_URLS:
        try:
            web3 = Web3(Web3.HTTPProvider(url))
            if web3.is_connected():
                print(f"1 📶 Connected to RPC URL: {Fore.RED}{url}{Style.RESET_ALL}")
                RPC_CACHE = web3
                return web3
        except Exception as e:
            print(f"Failed to connect to {url}: {e}")

    raise Exception("Unable to connect to any RPC.")

def get_wallet_balance(web3, address):
    balance_wei = web3.eth.get_balance(address)
    balance_eth = web3.from_wei(balance_wei, 'ether')
    return balance_eth

def sleep_seconds(seconds):
    print(f"10 ✈️ {Fore.GREEN} Airplane mode...U dont panic already to sleep in {seconds} seconds...{Style.RESET_ALL}")
    time.sleep(seconds)

def sleep_batch(seconds):
    minutes = seconds // 60
    print(f"{Fore.YELLOW} 🎧 Random waiting in {minutes} minutes is rotating NEXT BATCH ALL bang...{Style.RESET_ALL}")
    time.sleep(seconds)

def get_random_eth_amount():
    return Web3.to_wei(random.uniform(0.0001, 0.0055), 'ether')

def get_reasonable_gas_price(web3):
    current_gas_price = web3.eth.gas_price
    current_gwei = web3.from_wei(current_gas_price, 'gwei')
    target_gwei = random.uniform(50, 52)
    
    if current_gwei < 50:
        final_gwei = current_gwei
    else:
        final_gwei = target_gwei
    
    final_gas_price = web3.to_wei(final_gwei, 'gwei')
    
    estimated_gas = 150000
    estimated_cost_wei = estimated_gas * final_gas_price
    estimated_cost_eth = web3.from_wei(estimated_cost_wei, 'ether')
    
    print(f"6 🔋 Using low gas price:{Fore.YELLOW}{final_gwei:.2f} gwei{Style.RESET_ALL} est. cost {Fore.YELLOW}{estimated_cost_eth:.7f} MON{Style.RESET_ALL}")
    return int(final_gas_price)

def load_private_keys():
    private_keys = []

    env_private_key = os.getenv("PRIVATE_KEY")
    if env_private_key:
        private_keys.append(env_private_key.strip())

    # NO HAVE TRY TO PRIVATE_KEY.txt
    try:
        with open("private_keys.txt", "r") as file:
            keys = [line.strip() for line in file.readlines()]
            private_keys.extend(keys)
    except Exception as e:
        print(f"Error loading private keys from private_keys.txt: {e}")

    print(f"2 📸 To the moon load {len(private_keys)} address are {Fore.GREEN}succesfull..{Style.RESET_ALL}")
    return list(set(private_keys))

def safe_send_transaction(web3, signed_tx, retries=3):
    for i in range(retries):
        try:
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return web3.to_hex(tx_hash)
        except Exception as e:
            print(f"Transaction failed (attempt {i+1}): {e}")
            if i < retries - 1:
                sleep_seconds(3)  # wait 3s
    print("🥵 Transaction ultimately failed after retries 3x.")
    return None

def swap_eth_for_tokens_standard(wallet, token_address, amount_in_wei, token_symbol, web3):
    """Original working swap method with swapExactETHForTokens"""
    router = web3.eth.contract(address=UNISWAP_V2_ROUTER_ADDRESS, abi=[
        {
            "name": "swapExactETHForTokens",
            "type": "function",
            "stateMutability": "payable",
            "inputs": [
                {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                {"internalType": "address[]", "name": "path", "type": "address[]"},
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "uint256", "name": "deadline", "type": "uint256"}
            ],
            "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]
        }
    ])
    try:
        balance_eth = get_wallet_balance(web3, wallet.address)
        print(f"4 💰 Checking wallet balance {Fore.YELLOW}{balance_eth:.6f} MON{Style.RESET_ALL}")
        
        amount_eth = web3.from_wei(amount_in_wei, 'ether')
        print(f"5 🔎 OTW to swapping random amounts {Fore.YELLOW}{amount_eth:.6f} WMON{Style.RESET_ALL} for token {Fore.YELLOW}{token_symbol}{Style.RESET_ALL}")
        
        gas_price = get_reasonable_gas_price(web3)
        nonce = web3.eth.get_transaction_count(wallet.address, 'pending')

        # Set deadline 10 minutes in the future
        deadline = int(time.time()) + 600

        tx = router.functions.swapExactETHForTokens(
            0,
            [WMON_ADDRESS, token_address],
            wallet.address,
            deadline
        ).build_transaction({
            'from': wallet.address,
            'value': amount_in_wei,
            'gas': 150000,
            'gasPrice': gas_price,
            'nonce': nonce
        })

        signed_tx = wallet.sign_transaction(tx)
        tx_hash = safe_send_transaction(web3, signed_tx)
        if tx_hash:
            print(f"7 🟣 Transaction done!!! {Fore.GREEN}Check ok..successful!!!{Style.RESET_ALL} TXiD/Hash: {Fore.RED}{tx_hash}{Style.RESET_ALL}")
            
            new_balance = get_wallet_balance(web3, wallet.address)
            print(f"8 🤑 Checking last balance {Fore.YELLOW}{new_balance:.6f} MON{Style.RESET_ALL}")
            
            return True
        return False
    except Exception as e:
        print(f"🤬 Failed to swap WMON for {token_symbol}: {e}")
        return False

def swap_eth_for_tokens_execute(wallet, token_address, amount_in_wei, token_symbol, web3):
    """New swap method using execute (often used by aggregators)"""
    router = web3.eth.contract(address=UNISWAP_V2_ROUTER_ADDRESS, abi=router_abi)
    try:
        balance_eth = get_wallet_balance(web3, wallet.address)
        print(f"4 💰 Checking wallet balance {Fore.YELLOW}{balance_eth:.6f} MON{Style.RESET_ALL}")
        
        amount_eth = web3.from_wei(amount_in_wei, 'ether')
        print(f"5 🔎 OTW to swapping with execute() method {Fore.YELLOW}{amount_eth:.6f} WMON{Style.RESET_ALL} for token {Fore.YELLOW}{token_symbol}{Style.RESET_ALL}")
        
        gas_price = get_reasonable_gas_price(web3)
        nonce = web3.eth.get_transaction_count(wallet.address, 'pending')

        # Set deadline 10 minutes in the future
        deadline = int(time.time()) + 600
        
        # encode the swapExactETHForTokens call
        swap_data = router.encodeABI(
            fn_name='swapExactETHForTokens',
            args=[
                0,
                [WMON_ADDRESS, token_address],
                wallet.address,
                deadline
            ]
        )
        
        # Now call execute with this data
        tx = router.functions.execute(swap_data).build_transaction({
            'from': wallet.address,
            'value': amount_in_wei,
            'gas': 150000,
            'gasPrice': gas_price,
            'nonce': nonce
        })

        signed_tx = wallet.sign_transaction(tx)
        tx_hash = safe_send_transaction(web3, signed_tx)
        if tx_hash:
            print(f"7 🟣 Transaction with execute {Fore.GREEN}Ok..successful!!!{Style.RESET_ALL} TXiD/Hash: {Fore.RED}{tx_hash}{Style.RESET_ALL}")
            
            new_balance = get_wallet_balance(web3, wallet.address)
            print(f"8 🤑 Checking last balance {Fore.YELLOW}{new_balance:.6f} MON{Style.RESET_ALL}")
            
            return True
        return False
    except Exception as e:
        print(f"🤬 Failed to swap with execute for {token_symbol}: {e}")
        return False

def swap_eth_for_tokens_multicall(wallet, token_address, amount_in_wei, token_symbol, web3):
    """Swap method using multicall (often used by aggregators for batched calls)"""
    router = web3.eth.contract(address=UNISWAP_V2_ROUTER_ADDRESS, abi=router_abi)
    try:
        balance_eth = get_wallet_balance(web3, wallet.address)
        print(f"4 💰 Checking wallet balance {Fore.YELLOW}{balance_eth:.6f} MON{Style.RESET_ALL}")
        
        amount_eth = web3.from_wei(amount_in_wei, 'ether')
        print(f"5 🔎 OTW to swapping with multicall() method {Fore.YELLOW}{amount_eth:.6f} WMON{Style.RESET_ALL} for token {Fore.YELLOW}{token_symbol}{Style.RESET_ALL}")
        
        gas_price = get_reasonable_gas_price(web3)
        nonce = web3.eth.get_transaction_count(wallet.address, 'pending')

        # Set deadline 10 minutes in the future
        deadline = int(time.time()) + 600
        
        # Create the data for swapExactETHForTokens to be passed to multicall
        swap_data = router.encodeABI(
            fn_name='swapExactETHForTokens',
            args=[
                0,
                [WMON_ADDRESS, token_address],
                wallet.address,
                deadline
            ]
        )
        
        call_data = [swap_data]
        
        # Build multicall transaction
        tx = router.functions.multicall(call_data).build_transaction({
            'from': wallet.address,
            'value': amount_in_wei,
            'gas': 150000,
            'gasPrice': gas_price,
            'nonce': nonce
        })

        signed_tx = wallet.sign_transaction(tx)
        tx_hash = safe_send_transaction(web3, signed_tx)
        if tx_hash:
            print(f"7 🟣 Transaction with multicall {Fore.GREEN}Ok..successful!!!{Style.RESET_ALL} TXiD/Hash: {Fore.RED}{tx_hash}{Style.RESET_ALL}")
            
            new_balance = get_wallet_balance(web3, wallet.address)
            print(f"8 🤑 Checking last balance {Fore.YELLOW}{new_balance:.6f} MON{Style.RESET_ALL}")
            
            return True
        return False
    except Exception as e:
        print(f"🤬 Failed to swap with multicall for {token_symbol}: {e}")
        return False

def swap_eth_for_tokens_direct_swap(wallet, token_address, amount_in_wei, token_symbol, web3):
    """Swap method using direct swap method (often used by specialized routers)"""
    router = web3.eth.contract(address=UNISWAP_V2_ROUTER_ADDRESS, abi=router_abi)
    try:
        balance_eth = get_wallet_balance(web3, wallet.address)
        print(f"4 💰 Checking wallet balance {Fore.YELLOW}{balance_eth:.6f} MON{Style.RESET_ALL}")
        
        amount_eth = web3.from_wei(amount_in_wei, 'ether')
        print(f"5 🔎 OTW to swapping with swap() method {Fore.YELLOW}{amount_eth:.6f} WMON{Style.RESET_ALL} for token {Fore.YELLOW}{token_symbol}{Style.RESET_ALL}")
        
        gas_price = get_reasonable_gas_price(web3)
        nonce = web3.eth.get_transaction_count(wallet.address, 'pending')
        
        # Direct swap call (using native token as input)
        tx = router.functions.swap(
            WMON_ADDRESS,
            token_address,
            amount_in_wei,
            0,
            wallet.address
        ).build_transaction({
            'from': wallet.address,
            'value': amount_in_wei,
            'gas': 150000,
            'gasPrice': gas_price,
            'nonce': nonce
        })

        signed_tx = wallet.sign_transaction(tx)
        tx_hash = safe_send_transaction(web3, signed_tx)
        if tx_hash:
            print(f"7 🟣 Transaction with swap {Fore.GREEN}Ok..successful!!!{Style.RESET_ALL} TXiD/Hash: {Fore.RED}{tx_hash}{Style.RESET_ALL}")
            
            new_balance = get_wallet_balance(web3, wallet.address)
            print(f"8 🤑 Checking last balance {Fore.YELLOW}{new_balance:.6f} MON{Style.RESET_ALL}")
            
            return True
        return False
    except Exception as e:
        print(f"🤬 Failed to swap directly for {token_symbol}: {e}")
        return False

# ============ Main Page ============ 
def main():
    try:
        web3 = connect_to_rpc()

        private_keys = load_private_keys()
        if not private_keys:
            print("No private keys found, exiting...")
            return

        for private_key in private_keys:
            wallet = web3.eth.account.from_key(private_key)
            print(f"3 🔑 Oh Yes...!! correct using EVM address --> {wallet.address}")

            for token_symbol, token_address in TOKEN_ADDRESSES.items():
                eth_amount = get_random_eth_amount()
                
                # Option 1: Use standar swapExactETHForTokens
                success = swap_eth_for_tokens_standard(wallet, token_address, eth_amount, token_symbol, web3)
                
                # Option 2: Use execute
                # success = swap_eth_for_tokens_execute(wallet, token_address, eth_amount, token_symbol, web3)
                
                # Option 3: Use multicall
                # success = swap_eth_for_tokens_multicall(wallet, token_address, eth_amount, token_symbol, web3)
                
                # Option 4: Use direct swap
                # success = swap_eth_for_tokens_direct_swap(wallet, token_address, eth_amount, token_symbol, web3)
                
                # Random delay transactions (4-11 menit)
                delay_seconds = random.randint(260, 680)
                print(f"9 {Fore.GREEN}🔄 Used random rotating in {delay_seconds} seconds before next SWAPping transaction...{Style.RESET_ALL}")
                sleep_seconds(delay_seconds)

    except Exception as e:
        print(f"Error in main execution: {e}")

if __name__ == "__main__":
    try:
        while True:
            main()
            # Random delay between batches (16-51 menit)
            delay_minutes = random.randint(16, 51)
            delay_seconds = delay_minutes * 60
            sleep_batch(delay_seconds)
    except KeyboardInterrupt:
        print(f"{Fore.RED}Script stopped by you. So, Run with PM2 background{Style.RESET_ALL}")
