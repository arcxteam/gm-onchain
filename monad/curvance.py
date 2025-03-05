import os
import random
import time
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

# Config RPC & ABI CA
RPC_URLS = [
    "https://monad-testnet.g.alchemy.com/v2/G9UmvdH6oFBXk4Z_-fbJKt8m6wrdf6Ai",
    "https://testnet-rpc.monad.xyz",
    "https://monad-testnet.drpc.org",
    "https://monad-testnet.blockvision.org/v1/2td1EBS890QoVDhdSdd0Q1OlEGw"
]
CONTRACT_ADDRESS = Web3.to_checksum_address("0x8462c247356d7deB7e26160dbFab16B351Eef242")
CONTRACT_ABI = [
     {
         "constant": False,
         "inputs": [],
         "name": "pump",
         "outputs": [],
         "stateMutability": "nonpayable",
         "type": "function"
     }
 ]
GAS_LIMIT = 35001
CHAIN_ID = 10143

class Logger:
    @staticmethod
    def info(message):
        print(f"[INFO] {message}")

    @staticmethod
    def success(message):
        print(f"[SUCCESS] {message}")

    @staticmethod
    def error(message):
        print(f"{Fore.RED}[ERROR] {message}")

    @staticmethod
    def warning(message):
        print(f"[PUMP4FUN] {message}")
        
    @staticmethod
    def gas_report(message):
        print(f"[REPORT] {message}")

# Banner bang!!
def print_banner():
    banner = f"""
{Fore.GREEN}=========================================================================={Fore.RESET}
{Fore.YELLOW}
 ██████╗██╗   ██╗ █████╗ ███╗   ██╗███╗   ██╗ ██████╗ ██████╗ ███████╗
██╔════╝██║   ██║██╔══██╗████╗  ██║████╗  ██║██╔═══██╗██╔══██╗██╔════╝
██║     ██║   ██║███████║██╔██╗ ██║██╔██╗ ██║██║   ██║██║  ██║█████╗  
██║     ██║   ██║██╔══██║██║╚██╗██║██║╚██╗██║██║   ██║██║  ██║██╔══╝  
╚██████╗╚██████╔╝██║  ██║██║ ╚████║██║ ╚████║╚██████╔╝██████╔╝███████╗
 ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝
{Fore.RESET}
{Fore.GREEN}=========================================================================={Fore.RESET}
{Fore.CYAN}       Welcome to MONAD Onchain Testnet & Mainnet Interactive   {Fore.RESET}
{Fore.YELLOW}        - CUANNODE By Greyscope&Co, Credit By Arcxteam -      {Fore.RESET}
{Fore.GREEN}=========================================================================={Fore.RESET}
"""
    print(banner)

# Connect RPC MONAD
def connect_rpc():
    while True:
        for url in RPC_URLS:
            try:
                w3 = Web3(Web3.HTTPProvider(url))
                if w3.is_connected():
                    Logger.info(f" 📶 Yes..Connected to RPC: {Fore.RED}{url}")
                    return w3
            except Exception as e:
                Logger.error(f"🆙 Failed to connect RPC: {url}: {str(e)}")
        
        Logger.warning("🔁 Retrying RPC connection in 30 seconds...")
        time.sleep(30)

def load_private_keys():
    load_dotenv()
    keys = []
    
    # load .env
    if os.getenv("PRIVATE_KEY"):
        keys.append(os.getenv("PRIVATE_KEY"))
    
    # load .txt
    try:
        with open("private_keys.txt", "r") as f:
            keys.extend([line.strip() for line in f.readlines()])
    except FileNotFoundError:
        Logger.warning("private_keys.txt not found. Using only .env private key.")
    except Exception as e:
        Logger.error(f"Error loading private keys: {str(e)}")
    
    valid_keys = []
    for key in keys:
        if key and not key.startswith("#"):
            try:
                if Web3.is_address(Account.from_key(key).address):
                    valid_keys.append(key)
            except Exception:
                pass
    
    Logger.info(f" 🔓 Loaded EVM wallet {Fore.GREEN}{len(valid_keys)}{Fore.RESET} valid private keys")
    return valid_keys

def get_wallet_balance(w3, address):
    balance = w3.eth.get_balance(address)
    return w3.from_wei(balance, 'ether')

def get_eip1559_gas_params(w3):
    try:
        latest_block = w3.eth.get_block('latest')
        base_fee = latest_block.get('baseFeePerGas', w3.to_wei(50, 'gwei'))
        
        # Calculate max fee and priority fee
        max_priority_fee = w3.to_wei(2, 'gwei')
        max_fee = int(base_fee * 1.03) + max_priority_fee
        
        return {
            'maxFeePerGas': max_fee,
            'maxPriorityFeePerGas': max_priority_fee
        }
    except Exception as e:
        Logger.error(f"Failed to get EIP-1559 gas params: {str(e)}")
        # Fallback to legacy gas price
        return get_legacy_gas_price(w3)

def get_legacy_gas_price(w3):
    try:
        current_gas = w3.eth.gas_price
        current_gwei = w3.from_wei(current_gas, 'gwei')
        
        if current_gwei < 50:
            return {'gasPrice': current_gas}
        else:
            target_gwei = random.uniform(50, 52)
            return {'gasPrice': w3.to_wei(target_gwei, 'gwei')}
    except Exception as e:
        Logger.error(f"Failed to get gas price: {str(e)}")
        return {'gasPrice': w3.to_wei(50, 'gwei')}

class PumpBot:
    def __init__(self, use_eip1559=True):
        self.w3 = connect_rpc()
        self.private_keys = load_private_keys()
        if not self.private_keys:
            raise ValueError("No valid private keys found. Please check your wallet keys.")
        
        self.current_key_index = 0
        self.batch_count = 1
        self.transaction_count = 1
        self.use_eip1559 = use_eip1559
        self.wallet_cycle_complete = False
        self.total_gas_used = 0
        
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI
        )
        
        Logger.info(f" {Fore.YELLOW} 🎮 CURVANCE PUMP 4 GAINS - MONAD TESTNET 🎮 {Fore.RESET}")
        self.current_batch_size = random.randint(5, 13)  # random tx per-batch
        Logger.info(f" 🧵 Initial batch PUMP we get {Fore.YELLOW}#{self.current_batch_size}{Fore.RESET} TXiD transactions")
        gas_type = "EIP-1559" if self.use_eip1559 else "Legacy"
        Logger.info(f" ⛽️ Using {gas_type} {Fore.RED}gas{Fore.RESET} pricing")
        Logger.info(f" 👛 Will rotate through {Fore.GREEN}{len(self.private_keys)}{Fore.RESET} wallets before random long delay")

    def switch_wallet(self):
        old_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.private_keys)
        
        # siklus wallet
        if self.current_key_index == 0 and old_index != 0:
            self.wallet_cycle_complete = True
            Logger.warning(f" 🔄 Completed full wallet rotation cycle! All {len(self.private_keys)} wallets used.")
        else:
            self.wallet_cycle_complete = False
            
        Logger.info(f" 🔂 Switched to other EVM wallet {Fore.YELLOW}#{self.current_key_index + 1}{Fore.RESET}")
        
        current_address = Account.from_key(self.private_keys[self.current_key_index]).address
        truncated_address = f"{current_address[:6]}...{current_address[-4:]}"
        Logger.info(f" 💲 Current wallet address: {Fore.YELLOW}{truncated_address}{Fore.RESET}")
        
        return self.wallet_cycle_complete

    def calculate_gas_cost(self, receipt, gas_price=None, max_fee_per_gas=None, max_priority_fee_per_gas=None):
        """Calculate actual gas cost from transaction receipt"""
        gas_used = receipt.get('gasUsed', 0)
        
        if 'effectiveGasPrice' in receipt:
            effective_gas_price = receipt['effectiveGasPrice']
            gas_cost_wei = gas_used * effective_gas_price
        elif max_fee_per_gas:
            gas_cost_wei = gas_used * max_fee_per_gas
        elif gas_price:
            gas_cost_wei = gas_used * gas_price
        else:
            gas_cost_wei = gas_used * self.w3.eth.gas_price
        
        gas_cost_eth = self.w3.from_wei(gas_cost_wei, 'ether')
        self.total_gas_used += gas_cost_eth
        
        return {
            'gas_used': gas_used,
            'gas_cost_eth': gas_cost_eth,
            'gas_cost_wei': gas_cost_wei
        }

    def execute_pump(self):
        try:
            priv_key = self.private_keys[self.current_key_index]
            account = Account.from_key(priv_key)

            # Check balance before
            balance_before = get_wallet_balance(self.w3, account.address)
            Logger.info(f" 🤑 [Batch {self.batch_count}] Checking wallet balance: {Fore.YELLOW}{balance_before:.6f} MON{Fore.RESET}")

            if balance_before < 0.01:
                Logger.warning(f" 🤣 Low balance detected --> {Fore.YELLOW}{balance_before:.6f} MON{Fore.RESET} Consider adding funds.")
                if balance_before < 0.005:
                    Logger.error(f" 🤣 Insufficient balance isi bang gas. Switching wallet.")
                    self.switch_wallet()
                    return False

            nonce = self.w3.eth.get_transaction_count(account.address)
            
            # Get gas based on selected
            gas_params = get_eip1559_gas_params(self.w3) if self.use_eip1559 else get_legacy_gas_price(self.w3)
            
            tx_params = {
                'chainId': CHAIN_ID,
                'gas': GAS_LIMIT,
                'nonce': nonce,
                'value': 0
            }
            
            max_fee_per_gas = gas_params.get('maxFeePerGas')
            max_priority_fee_per_gas = gas_params.get('maxPriorityFeePerGas')
            gas_price = gas_params.get('gasPrice')
            
            # Add gas based on method (EIP-1559 or legacy)
            tx_params.update(gas_params)
            
            tx = self.contract.functions.pump().build_transaction(tx_params)

            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, priv_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            try:
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt.status == 1:
                    # Calculate actual gas cost
                    gas_info = self.calculate_gas_cost(
                        receipt, 
                        gas_price=gas_price,
                        max_fee_per_gas=max_fee_per_gas,
                        max_priority_fee_per_gas=max_priority_fee_per_gas
                    )
                    
                    # Get balance after transaction
                    balance_after = get_wallet_balance(self.w3, account.address)
                    actual_cost = balance_before - balance_after
                    
                    Logger.success(f" 🧵 [Batch {Fore.GREEN}#{self.batch_count}{Fore.RESET} TXiD counted {Fore.YELLOW}#{self.transaction_count}{Fore.RESET}] {Fore.GREEN}Successful!{Fore.RESET} HashID -> {tx_hash.hex()}")
                    Logger.gas_report(f" 🧵 [Batch {Fore.GREEN}#{self.batch_count}{Fore.RESET} TXiD counted {Fore.YELLOW}#{self.transaction_count}{Fore.RESET}] Actual cost fees {Fore.YELLOW}{actual_cost:.8f} MON{Fore.RESET}")
                    Logger.gas_report(f" ⛽ Gas Used: {gas_info['gas_used']} units | Est.cost: {Fore.YELLOW}{gas_info['gas_cost_eth']:.8f} MON{Fore.RESET}")
                    
                    return True
                else:
                    Logger.error(f" ↪️ [Batch {Fore.GREEN}#{self.batch_count}{Fore.RESET} TXiD count {Fore.YELLOW}#{self.transaction_count}{Fore.RESET}] Transaction reverted: {tx_hash.hex()}")
                    return False
            except Exception as e:
                Logger.warning(f" ❎ Transaction sent but receipt not confirmed: {str(e)}. HashID: {tx_hash.hex()}")
                return False
            
        except ValueError as e:
            if "insufficient funds" in str(e).lower():
                Logger.error(f" 😂 Insufficient funds for wallet #{self.current_key_index + 1} 🔑 Switching wallets.")
                self.switch_wallet()
            else:
                Logger.error(f"Value error: {str(e)}")
            return False
        except Exception as e:
            Logger.error(f"Transaction failed: {str(e)}")
            return False

    def run(self):
        while True:
            try:
                # Execution batch
                Logger.info(f" 🔎 Here We PUMP..Batch {Fore.GREEN}#{self.batch_count}{Fore.RESET} with random rotating get count {Fore.YELLOW}#{self.current_batch_size}{Fore.RESET} TXiD transactions")
                
                successful_txs = 0
                for tx_num in range(1, self.current_batch_size + 1):
                    self.transaction_count = tx_num
                    if self.execute_pump():
                        successful_txs += 1
                        # Delay tx/id in batch (45s-80s)
                        intra_delay = random.randint(45, 80)
                        minutes, seconds = divmod(intra_delay, 60)
                        Logger.warning(f" 🔮 Sub-batch get random rotating in --> {Fore.CYAN} {minutes} mins {seconds} secs{Fore.RESET}")
                        time.sleep(intra_delay)
                    else:
                        time.sleep(10)
                
                # Batch end
                Logger.warning(f" ✅ Batch {Fore.GREEN}#{self.batch_count}{Fore.RESET} for wallet {Fore.GREEN}#{self.current_key_index + 1}{Fore.RESET} completed with {Fore.GREEN}{successful_txs}/{self.current_batch_size} successful{Fore.RESET} TxID")
                
                cycle_completed = self.switch_wallet()
                # Update batch counter
                self.batch_count += 1
                self.current_batch_size = random.randint(5, 13)
                
                if cycle_completed:
                    success_rate = successful_txs / self.current_batch_size
                    
                    # Shorter delay if success rate is low
                    if success_rate < 0.5:
                        batch_delay = random.randint(3600, 5400)  # 1-1.5 hours
                    else:
                        batch_delay = random.randint(10800, 14400) # delay on batch (3-4 hours)
                    
                    minutes, seconds = divmod(batch_delay, 60)
                    Logger.warning(f" ✅ Main-batch has {Fore.GREEN}Completed!!{Fore.RESET} Next sub-batch random rotating in -> {Fore.GREEN} {minutes} mins {seconds} secs{Fore.RESET}")
                    Logger.gas_report(f" 💲 Total gas used so far: {Fore.YELLOW} {self.total_gas_used:.8f} MON{Fore.RESET}")
                    time.sleep(batch_delay)
                else:
                    short_delay = random.randint(10, 30) # delay switch wallet 10s-30s
                    Logger.warning(f" 🔁 Moving to next wallet in {Fore.YELLOW}{short_delay}{Fore.RESET} seconds")
                    time.sleep(short_delay)

            except KeyboardInterrupt:
                Logger.info(f" ❌ {Fore.YELLOW}Curvance Pump4Fun has been stopped by. Consider run at PM2 background.")
                break
            except Exception as e:
                Logger.error(f" ⭕️ Unexpected error in run loop: {str(e)}")
                time.sleep(60)

if __name__ == "__main__":
    print_banner()
    try:
        # change this to False=legacy or True=eip1559
        bot = PumpBot(use_eip1559=True)
        bot.run()
    except Exception as e:
        Logger.error(f"Fatal error: {str(e)}")
