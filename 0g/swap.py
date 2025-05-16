import os
import time
import json
import random
import datetime
from web3 import Web3
from pathlib import Path
from colorama import Fore, Style, init
from dotenv import load_dotenv

init(autoreset=True)
load_dotenv()

# ======================== Constants ========================
MESSAGES = {
    "GAS_RESET": "⚠️ Gas price di-reset ke nilai yang lebih wajar",
    "TX_SENT": "✅ Transaksi {} dikirim! TxID #{}: {}",
    "TX_CONFIRMED": "✅ Transaksi dikonfirmasi: nomor blok #{}...",
    "TX_FAILED": "❌ Transaksi gagal di blockchain",
    "TX_BUILD_ERROR": "❌ Gagal membangun transaksi {}: {}",
    "RPC_ERROR": "⚠️ Error pada RPC: {}",
    "BALANCE_CHECK": "💰 Saldo duit {}: {:.6f}",
    "NONCE_UPDATE": "🔄 Nonce diperbarui ke {}",
    "WAITING_TX": "⏳ Menunggu transaksi {} dikonfirmasi..."
}

# ======================== Configuration ========================
CONFIG = {
    "RPC_URLS": os.getenv(
        "RPC_URLS",
        "https://evmrpc-testnet.0g.ai,https://0g-testnet-rpc.astrostake.xyz,https://rpc.ankr.com/0g_newton"
    ).split(","),
    "PRIVATE_KEY_FILE": os.path.join(os.path.dirname(__file__), "private_keys.txt"),
    "ENV_FILE": ".env",
    "MAX_RETRIES": 5,
    "GAS_MULTIPLIER": 0.33,
    "MAX_PRIORITY_GWEI": 1.03, # EIP1559
    "GAS_LIMIT": 250000,
    "COOLDOWN": {"SUCCESS": (20, 60), "ERROR": (20, 60)}, # detik bang
    "WALLET_SWITCH_DELAY": (100, 200), # detik
    "CYCLE_COMPLETE_DELAY": (2000, 3000), # detik
    "TRANSACTIONS_PER_WALLET": (15, 60), # tx per wallet random
    "SWAP_AMOUNT_USDT": (10, 30), # swap saldo
    "SWAP_AMOUNT_ETH": (0.003, 0.005),
    "SWAP_AMOUNT_BTC": (0.0003, 0.0005),
    "GAS_MIN_GWEI": 1.03,
    "GAS_MAX_GWEI": 2.0, # Legacy mode
    "GAS_RESET_GWEI": 3,
    "RPC_TIMEOUT": 15,  # detik
    "RPC_RETRY_DELAY": 10,  # detik
}

CHAIN_SYMBOLS = {16601: "0G"}

# ================= Contract Addresses ===================
TOKEN_ADDRESSES = {
    "ROUTER": "0xb95B5953FF8ee5D5d9818CdbEfE363ff2191318c",
    "USDT": "0x3eC8A8705bE1D5ca90066b37ba62c4183B024ebf",
    "ETH": "0x0fE9B43625fA7EdD663aDcEC0728DD635e4AbF7c",
    "BTC": "0x36f6414FF1df609214dDAbA71c84f18bcf00F67d",
}

# ==================== ABIs ========================
ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "internalType": "struct ISwapRouter.ExactInputSingleParams",
                "name": "params",
                "type": "tuple",
            },
        ],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    }
]

TOKEN_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
]

# ======================== Helper Functions ========================
def print_color(message, color=None, prefix=None, num=None, total=None):
    """Fungsi printing dengan warna"""
    prefix_str = f"{prefix} " if prefix else ""
    nums_str = f"[{num}/{total}] " if (num is not None and total is not None) else ""
    
    if color:
        print(f"{color}{prefix_str}{nums_str}{message}{Style.RESET_ALL}")
    else:
        print(f"{prefix_str}{nums_str}{message}")

def print_info(message, prefix=None, num=None, total=None):
    print_color(message, None, prefix, num, total)

def print_success(message, prefix=None, num=None, total=None):
    print_color(message, Fore.GREEN, prefix, num, total)

def print_error(message, prefix=None, num=None, total=None):
    print_color(message, Fore.RED, prefix, num, total)

def print_warning(message, prefix=None, num=None, total=None):
    print_color(message, Fore.YELLOW, prefix, num, total)

def print_debug(message, prefix=None, num=None, total=None):
    print_color(message, Fore.CYAN, prefix, num, total)

def short_address(address):
    """Format address dengan singkat: 0x1234...5678"""
    return f"{address[:6]}...{address[-4:]}" if address else "Unknown address"

def sleep_seconds(seconds, message=None):
    """Fungsi sleep dengan pesan informatif"""
    if message:
        print(f"⏳ {Fore.MAGENTA}{message} dalam {seconds} detik...{Style.RESET_ALL}")
    else:
        print(f"⏳ {Fore.YELLOW}Menunggu {seconds} detik...{Style.RESET_ALL}")
    time.sleep(seconds)

def random_sleep(min_secs, max_secs, message=None):
    """Sleep dengan durasi acak"""
    seconds = random.randint(min_secs, max_secs)
    sleep_seconds(seconds, message)

def validate_rpc_urls(urls):
    """Validasi RPC URLs untuk memastikan formatnya benar"""
    valid_urls = []
    for url in urls:
        url = url.strip()
        if url and url.startswith("http"):
            valid_urls.append(url)
        else:
            print_warning(f"RPC URL tidak valid diabaikan: {url}")
    
    if not valid_urls:
        print_error("Tidak ada RPC URL valid ditemukan. Menggunakan default.")
        return ["https://evmrpc-testnet.0g.ai"]
    
    return valid_urls
    
# Print banner
def print_banner():
    banner = f"""
{Fore.GREEN}============================ WELCOME TO VOTING DAPPs ============================{Fore.RESET}
{Fore.YELLOW}
 ██████╗██╗   ██╗ █████╗ ███╗   ██╗███╗   ██╗ ██████╗ ██████╗ ███████╗
██╔════╝██║   ██║██╔══██╗████╗  ██║████╗  ██║██╔═══██╗██╔══██╗██╔════╝
██║     ██║   ██║███████║██╔██╗ ██║██╔██╗ ██║██║   ██║██║  ██║█████╗  
██║     ██║   ██║██╔══██║██║╚██╗██║██║╚██╗██║██║   ██║██║  ██║██╔══╝  
╚██████╗╚██████╔╝██║  ██║██║ ╚████║██║ ╚████║╚██████╔╝██████╔╝███████╗
 ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝
{Fore.RESET}
{Fore.CYAN}========================================================================={Fore.RESET}
{Fore.MAGENTA}       Welcome to 0G-Gravity Onchain Testnet & Mainnet Interactive   {Fore.RESET}
{Fore.YELLOW}           - CUANNODE By Greyscope&Co, Credit By Arcxteam -     {Fore.RESET}
{Fore.CYAN}========================================================================={Fore.RESET}
"""
    print(banner)

# ======================== 0G Swap Class ========================
class OGSwapper:
    def __init__(self):
        self.accounts = []
        self.web3 = None
        self.gas_price = None
        self.current_rpc_index = 0
        self.router_contract = None
        self.cycle_count = 1
        self.tx_counter = 0
        self.token_contracts = {}
        self.rpc_last_error_time = {}
        
        self.token_decimals = {
            "USDT": 18,
            "ETH": 18,
            "BTC": 18
        }

    def initialize(self):
        """Inisialisasi connection dan load accounts"""
        CONFIG["RPC_URLS"] = validate_rpc_urls(CONFIG["RPC_URLS"])
        
        self.connect_to_rpc()
        self.load_accounts()
        self.update_gas_price()
        self.initialize_contracts()

    def connect_to_rpc(self):
        """Connect ke RPC endpoint, dengan rotasi jika gagal"""
        for i, rpc_url in enumerate(CONFIG["RPC_URLS"]):
            try:
                self.current_rpc_index = i
                w3 = Web3(Web3.HTTPProvider(rpc_url.strip(), request_kwargs={'timeout': CONFIG["RPC_TIMEOUT"]}))
                if w3.is_connected():
                    chain_id = w3.eth.chain_id
                    print(f"🌐 Terhubung ke RPC: {Fore.YELLOW}{rpc_url}{Fore.RESET}")
                    print_info(f"📡 Chain ID: {chain_id} - {CHAIN_SYMBOLS.get(chain_id, 'Unknown')}")
                    self.web3 = w3
                    self.rpc_last_error_time[rpc_url] = 0
                    return True
            except Exception as e:
                print_warning(f"⚠️ Gagal terhubung ke RPC {rpc_url}: {str(e)}")
                self.rpc_last_error_time[rpc_url] = time.time()
        
        if not self.web3:
            print_error("❌ Gagal terhubung ke semua RPC endpoint.")
            raise ConnectionError("Tidak dapat terhubung ke jaringan 0G. Periksa RPC URLs.")

    def switch_rpc(self):
        """Beralih ke RPC lain jika terjadi masalah, memprioritaskan yang belum error"""
        old_index = self.current_rpc_index
        old_rpc = CONFIG["RPC_URLS"][old_index]
        
        now = time.time()
        available_rpcs = [
            (i, url) for i, url in enumerate(CONFIG["RPC_URLS"]) 
            if i != old_index and (url not in self.rpc_last_error_time or now - self.rpc_last_error_time[url] > 60)
        ]
        
        # gunakan semua RPC selain yang saat ini
        if not available_rpcs:
            available_rpcs = [(i, url) for i, url in enumerate(CONFIG["RPC_URLS"]) if i != old_index]
        
        if not available_rpcs:
            sleep_seconds(CONFIG["RPC_RETRY_DELAY"], "Menunggu sebelum mencoba ulang RPC yang sama")
            return False
        
        # random RPC
        self.current_rpc_index, new_rpc = random.choice(available_rpcs)
        
        print(f"🔄 Beralih dari RPC {Fore.RED}{old_rpc}{Fore.RESET} ke --> {Fore.YELLOW}{new_rpc}{Fore.RESET}")
        
        try:
            self.web3 = Web3(Web3.HTTPProvider(new_rpc.strip(), request_kwargs={'timeout': CONFIG["RPC_TIMEOUT"]}))
            if self.web3.is_connected():
                self.initialize_contracts()
                print(f"✅ Berhasil beralih ke RPC: {Fore.YELLOW}{new_rpc}{Fore.RESET}")
                self.rpc_last_error_time[new_rpc] = 0
                return True
        except Exception as e:
            print_error(f"❌ Gagal beralih ke RPC {new_rpc}: {str(e)}")
            self.rpc_last_error_time[new_rpc] = time.time()
            # Coba rotasi ke RPC lain
            self.current_rpc_index = old_index
            return self.switch_rpc()

        return False

    def initialize_contracts(self):
        """Inisialisasi kontrak router dan token contracts"""
        try:
            router_address = Web3.to_checksum_address(TOKEN_ADDRESSES["ROUTER"])
            self.router_contract = self.web3.eth.contract(address=router_address, abi=ROUTER_ABI)
            print(f"📝 Kontrak router berhasil diinisialisasi: {short_address(router_address)}")
            
            self.token_contracts = {}
        except Exception as e:
            print_error(f"❌ Gagal inisialisasi kontrak: {str(e)}")
            raise

    def is_valid_private_key(self, key):
        """Validasi format private key"""
        try:
            if not key or key.startswith("#") or len(key.strip()) < 5:
                return None

            if not key.startswith("0x"):
                key = "0x" + key

            if len(key) != 66:
                return None

            self.web3.eth.account.from_key(key)
            return key
        except Exception as e:
            print_warning(f"⚠️ Private key tidak valid: {str(e)}")
            return None

    def load_accounts(self):
        """Load private keys dari file dan env"""
        accounts = []

        if os.path.exists(CONFIG["ENV_FILE"]):
            try:
                load_dotenv(CONFIG["ENV_FILE"])
                private_key = os.getenv("PRIVATE_KEY")
                if private_key:
                    valid_key = self.is_valid_private_key(private_key)
                    if valid_key:
                        account = self.web3.eth.account.from_key(valid_key)
                        accounts.append({"key": valid_key, "address": account.address})
                        print_success(f"✅ Wallet dari .env berhasil dimuat: {short_address(account.address)}")
            except Exception as e:
                print_error(f"❌ Error loading from .env: {str(e)}")

        if os.path.exists(CONFIG["PRIVATE_KEY_FILE"]):
            try:
                with open(CONFIG["PRIVATE_KEY_FILE"], "r") as file:
                    keys = [line.strip() for line in file.readlines()]
                    loaded = 0
                    for key in keys:
                        valid_key = self.is_valid_private_key(key)
                        if valid_key:
                            account = self.web3.eth.account.from_key(valid_key)
                            if not any(acc["address"] == account.address for acc in accounts):
                                accounts.append({"key": valid_key, "address": account.address})
                                loaded += 1
                                print(f"✅ Wallet #{loaded} berhasil dimuat: {Fore.GREEN}{short_address(account.address)}{Fore.RESET}")
                        else:
                            print_warning("⚠️ Private key tidak valid, melewatkan...")
            except Exception as e:
                print_error(f"❌ Error loading private keys: {str(e)}")

        if not accounts:
            print_error("❌ Tidak ada private key valid yang ditemukan.")
            exit(1)

        self.accounts = accounts
        print(f"📊 Total {len(self.accounts)} wallet berhasil dimuat")
    
    def check_eip1559_support(self):
        """Periksa dukungan EIP-1559 pada jaringan"""
        try:
            # Metode 1: cek baseFeePerGas pada blok terakhir
            latest_block = self.web3.eth.get_block('latest')
            if 'baseFeePerGas' in latest_block and latest_block['baseFeePerGas']:
                print("✅ Jaringan mendukung EIP-1559 (metode 1)")
                return True
            
            # Metode 2: cek eriksa fee history
            try:
                fee_history = self.web3.eth.fee_history(1, 'latest')
                if 'baseFeePerGas' in fee_history and fee_history['baseFeePerGas'] and len(fee_history['baseFeePerGas']) > 0:
                    print_success("✅ Jaringan mendukung EIP-1559 (metode 2)")
                    return True
            except:
                pass
            
            print_warning("⚠️ EIP-1559 tidak tersedia, menggunakan legacy gas")
            return False
        except Exception as e:
            print_warning(f"⚠️ Error memeriksa dukungan EIP-1559: {str(e)}")
            return False

    def get_eip1559_gas_params(self):
        """Dapatkan parameter gas EIP-1559"""
        try:
            if not self.check_eip1559_support():
                return None

            fee_history = self.web3.eth.fee_history(1, 'latest')
            base_fee = fee_history['baseFeePerGas'][0]

            max_priority = self.web3.to_wei(CONFIG["MAX_PRIORITY_GWEI"], 'gwei')
            max_fee = int(base_fee * CONFIG["GAS_MULTIPLIER"]) + max_priority

            base_fee_gwei = self.web3.from_wei(base_fee, 'gwei')
            max_fee_gwei = self.web3.from_wei(max_fee, 'gwei')
            max_priority_gwei = self.web3.from_wei(max_priority, 'gwei')

            print_info(f"⛽ Gas: Base Fee: {base_fee_gwei:.2f} Gwei | Max Fee: {max_fee_gwei:.2f} Gwei | Priority: {max_priority_gwei:.2f} Gwei")

            return {'maxFeePerGas': max_fee, 'maxPriorityFeePerGas': max_priority}
        except Exception as e:
            print_error(f"❌ Estimasi EIP-1559 gagal: {str(e)}")
            return None

    def get_legacy_gas_price(self):
        """Dapatkan legacy gas price dengan fallback ke nilai default jika gagal"""
        try:
            # coba gas dari legacy
            current = self.web3.eth.gas_price

            if current <= self.web3.to_wei(0.33, "gwei"):
                print(f"⚠️  Gas price terlalu rendah ({self.web3.from_wei(current, 'gwei'):.2f} Gwei), menggunakan default")
                gas_price = self.web3.to_wei(CONFIG["GAS_MIN_GWEI"], "gwei")
            else:
                min_gas = self.web3.to_wei(CONFIG["GAS_MIN_GWEI"], "gwei")
                max_gas = self.web3.to_wei(CONFIG["GAS_MAX_GWEI"], "gwei")
                
                gas_price = int(current * CONFIG["GAS_MULTIPLIER"])
                
                if gas_price < min_gas:
                    gas_price = min_gas
                elif gas_price > max_gas:
                    gas_price = max_gas
            
            gas_gwei = self.web3.from_wei(gas_price, "gwei")
            print_info(f"⛽ Gas price: {gas_gwei:.2f} Gwei (Legacy Mode)")
            
            return gas_price
        except Exception as e:
            print_error(f"❌ Estimasi legacy gas gagal: {str(e)}")
            default_gas = self.web3.to_wei(CONFIG["GAS_MIN_GWEI"], "gwei")
            print_warning(f"⚠️ Menggunakan gas price default: {CONFIG['GAS_MIN_GWEI']} Gwei")
            return default_gas

    def reset_gas_price(self):
        """Reset gas price ke nilai awal yang wajar setelah terlalu banyak retry"""
        if isinstance(self.gas_price, dict):
            self.gas_price["maxFeePerGas"] = self.web3.to_wei(CONFIG["GAS_RESET_GWEI"], "gwei")
            self.gas_price["maxPriorityFeePerGas"] = self.web3.to_wei(1, "gwei")
            print_warning(MESSAGES["GAS_RESET"])
        else:
            self.gas_price = self.web3.to_wei(CONFIG["GAS_RESET_GWEI"], "gwei")
            print_warning(MESSAGES["GAS_RESET"])

    def update_gas_price(self):
        """Update gas price dengan EIP-1559 atau legacy"""
        # Coba EIP-1559 terlebih dahulu
        eip1559_params = self.get_eip1559_gas_params()
        if eip1559_params:
            self.gas_price = eip1559_params
            print_success("✅ Menggunakan mode gas EIP-1559")
        else:
            # gak ada, fallback ke legacy
            self.gas_price = self.get_legacy_gas_price()
            print_success("✅ Menggunakan mode gas Legacy")

    def get_token_contract(self, token_symbol):
        """Dapatkan kontrak untuk token tertentu (dengan caching)"""
        if token_symbol in self.token_contracts:
            return self.token_contracts[token_symbol]
            
        token_address = TOKEN_ADDRESSES.get(token_symbol)
        if not token_address:
            raise ValueError(f"Alamat tidak ditemukan untuk token: {token_symbol}")
        
        contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=TOKEN_ABI
        )

        self.token_contracts[token_symbol] = contract
        return contract

    def check_wallet_balance(self, address, token_symbol=None):
        """Periksa saldo wallet, native token atau token tertentu"""
        max_retries = 3
        for retry in range(max_retries):
            try:
                balance_wei = self.web3.eth.get_balance(address)
                balance_eth = self.web3.from_wei(balance_wei, "ether")
                chain_id = self.web3.eth.chain_id
                token_name = CHAIN_SYMBOLS.get(chain_id, "0G")
            
                print_info(MESSAGES["BALANCE_CHECK"].format(token_name, balance_eth))

                if token_symbol and token_symbol in TOKEN_ADDRESSES:
                    token_contract = self.get_token_contract(token_symbol)
                    token_balance = token_contract.functions.balanceOf(address).call()
                    token_decimals = self.token_decimals.get(token_symbol, 18)
                    token_amount = token_balance / (10 ** token_decimals)
                    print_info(MESSAGES["BALANCE_CHECK"].format(token_symbol, token_amount))
                    return balance_wei, token_balance
                
                return balance_wei
            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "too many requests" in error_msg:
                    print_warning(f"⚠️ RPC membatasi permintaan saat memeriksa saldo. Mencoba beralih RPC...")
                    if self.switch_rpc():
                        # Berhasil switch RPC, coba lagi
                        continue
            
                if retry == max_retries - 1:  # Jika ini percobaan terakhir
                    print_error(f"❌ Error memeriksa saldo setelah {max_retries} percobaan: {str(e)}")
                    return 0
            
                # Tunggu sebelum retry
                sleep_seconds(10, "Menunggu sebelum mencoba memeriksa saldo lagi")
    
        return 0

    def estimate_gas(self, contract_func, sender):
        """Fungsi generik untuk estimasi gas dengan fallback ke default"""
        try:
            estimate_gas = contract_func.estimate_gas({'from': sender})
            return int(estimate_gas * 1.05)  # 10% buffer
        except Exception as e:
            default_gas = CONFIG["GAS_LIMIT"]
            print(f"⚠️  Estimasi gas gagal: {Fore.RED}{str(e)}{Fore.RESET} Cek nilai default: {default_gas}")
            return default_gas

    def build_transaction(self, to_address, data, sender, gas_limit, description=""):
        """Fungsi generik untuk membangun transaksi"""
        try:
            nonce = self.get_safe_nonce(sender)
            
            tx = {
                "from": sender,
                "to": to_address,
                "gas": gas_limit,
                "nonce": nonce,
                "chainId": self.web3.eth.chain_id,
                "data": data
            }

            if isinstance(self.gas_price, dict):
                tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
            else:
                tx["gasPrice"] = self.gas_price
            
            print_debug(f"📝 Transaksi {description} dibuat dengan nonce {nonce}")
            return tx
        except Exception as e:
            print_error(MESSAGES["TX_BUILD_ERROR"].format(description, str(e)))
            return None

    def build_approval_tx(self, token_symbol, spender, amount, sender):
        """Buat transaksi approval token"""
        try:
            token_contract = self.get_token_contract(token_symbol)
            
            gas_limit = self.estimate_gas(
                token_contract.functions.approve(spender, amount),
                sender
            )
            
            data = token_contract.encodeABI(
                fn_name="approve", 
                args=[spender, amount]
            )
            
            return self.build_transaction(
                TOKEN_ADDRESSES[token_symbol],
                data,
                sender,
                gas_limit,
                f"approval {token_symbol}"
            )
        except Exception as e:
            print_error(MESSAGES["TX_BUILD_ERROR"].format(f"approval {token_symbol}", str(e)))
            return None

    def build_swap_tx(self, token_in, token_out, amount, sender):
        """Buat transaksi swap token"""
        try:
            deadline = int(time.time()) + 300  # 5 menit

            params = {
                'tokenIn': Web3.to_checksum_address(TOKEN_ADDRESSES[token_in]),
                'tokenOut': Web3.to_checksum_address(TOKEN_ADDRESSES[token_out]),
                'fee': 15000,
                'recipient': sender,
                'deadline': deadline,
                'amountIn': amount,
                'amountOutMinimum': 0,
                'sqrtPriceLimitX96': 0
            }

            gas_limit = self.estimate_gas(
                self.router_contract.functions.exactInputSingle(params),
                sender
            )

            data = self.router_contract.encodeABI(
                fn_name="exactInputSingle", 
                args=[params]
            )
            
            tx = self.build_transaction(
                TOKEN_ADDRESSES["ROUTER"],
                data,
                sender,
                gas_limit,
                f"swap {token_in} ke {token_out}"
            )
            
            if tx:
                decimals = self.token_decimals.get(token_in, 18)
                amount_readable = amount / (10 ** decimals)
                print_debug(f"📝 Transaksi swap {amount_readable:.6f} {token_in} </> {token_out} dibuat")
                
            return tx
        except Exception as e:
            print_error(MESSAGES["TX_BUILD_ERROR"].format(f"swap {token_in} ke {token_out}", str(e)))
            return None
    
    def get_safe_nonce(self, address):
        """Dapatkan nonce yang aman, dengan memastikan tidak ada transaksi pending"""
        try:
            pending_nonce = self.web3.eth.get_transaction_count(address, "pending")
            latest_nonce = self.web3.eth.get_transaction_count(address, "latest")
        
            if pending_nonce > latest_nonce:
                print_debug(f"🔄 Menunggu transaksi pending selesai... (pending nonce: {pending_nonce}, latest nonce: {latest_nonce})")
                time.sleep(5)
                return self.get_safe_nonce(address)
        
            print(f"🔢 Menggunakan {Fore.YELLOW}nonce {latest_nonce}{Fore.RESET}")
            return latest_nonce
        except Exception as e:
            print(f"⚠️  Error mendapatkan nonce: {Fore.RED}{str(e)}{Fore.RESET}")
            return self.web3.eth.get_transaction_count(address, "latest")

    def wait_for_transaction_completion(self, tx_hash, timeout=150):
        """Menunggu transaksi selesai dengan penanganan error yang lebih baik"""
        print_info(MESSAGES["WAITING_TX"].format(tx_hash))
        start_time = time.time()
    
        last_error_time = 0  # Untuk menghindari spam log error
        rpc_switched = True # False/True Track apakah sudah switch RPC
        check_interval = 10   # Interval cek status transaksi detik
    
        while time.time() - start_time < timeout:
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    if receipt.status == 1:
                        print_success(MESSAGES["TX_CONFIRMED"].format(receipt.blockNumber))
                        return receipt
                    else:
                        print_error(MESSAGES["TX_FAILED"])
                        return receipt
            except Exception as e:
                current_time = time.time()
                error_msg = str(e).lower()
            
                if current_time - last_error_time > 5:
                    if "not found" not in error_msg:
                        print_warning(f"⚠️ Error checking receipt: {str(e)}")
                        last_error_time = current_time
                    
                        # Jika RPC error, coba switch
                        if "429" in error_msg or "too many requests" in error_msg or "server error" in error_msg:
                            if not rpc_switched:
                                print_warning(f"⚠️ RPC bermasalah, mencoba beralih ke RPC lain...")
                                if self.switch_rpc():
                                    rpc_switched = True
                                    continue

            time.sleep(check_interval)
    
        print(f"⏱️ Timeout menunggu transaksi {tx_hash}.")
        return None

    def reset_pending_transactions(self, address, private_key):
        """Reset transaksi pending dengan mengirim transaksi dummy dengan nonce sama"""
        try:
            pending_nonce = self.web3.eth.get_transaction_count(address, "pending")
            latest_nonce = self.web3.eth.get_transaction_count(address, "latest")
            
            if pending_nonce > latest_nonce:
                print_warning(f"⚠️ Terdeteksi {pending_nonce - latest_nonce} transaksi pending yang mungkin stuck.")
                
                # Coba kirim transaksi dummy untuk reset, krim ke wallet sendiri
                max_reset_tx = 3
                for nonce in range(latest_nonce, min(pending_nonce, latest_nonce + max_reset_tx)):
                    print_warning(f"🔄 Mencoba reset transaksi dengan nonce {nonce}...")
                    tx = {
                        "from": address,
                        "to": address,
                        "value": 0,
                        "gas": 21000,
                        "nonce": nonce,
                        "chainId": self.web3.eth.chain_id,
                    }

                    if isinstance(self.gas_price, dict):
                        tx["maxFeePerGas"] = self.web3.to_wei(2, "gwei")
                        tx["maxPriorityFeePerGas"] = self.web3.to_wei(2, "gwei")
                    else:
                        tx["gasPrice"] = self.web3.to_wei(2, "gwei")

                    try:
                        signed = self.web3.eth.account.sign_transaction(tx, private_key)
                        receipt = self.web3.eth.send_raw_transaction(signed.rawTransaction)
                        print_success(f"✅ Transaksi reset untuk nonce {nonce} berhasil dikirim: {receipt.hex()}")
                    except Exception as e:
                        if "already known" in str(e).lower():
                            print_warning(f"⚠️ Transaksi untuk nonce {nonce} sudah ada di mempool")
                        else:
                            print_error(f"❌ Error reset nonce {nonce}: {str(e)}")
                
            return True
        except Exception as e:
            print_error(f"❌ Error reset transaksi pending: {str(e)}")
            return False

    def handle_tx_error(self, error, tx):
        """Tangani error transaksi dan update tx jika diperlukan"""
        error_message = str(error).lower()
        
        if "insufficient funds" in error_message:
            print_error(f"💰 Error: Dana tidak cukup untuk gas * price + value")
            return None, False
            
        elif "nonce too low" in error_message:
            try:
                new_nonce = self.web3.eth.get_transaction_count(tx["from"], "pending")
                tx["nonce"] = new_nonce
                print_warning(MESSAGES["NONCE_UPDATE"].format(new_nonce))
                return tx, True
            except Exception as nonce_error:
                print_error(f"❌ Error memperbarui nonce: {str(nonce_error)}")
                return None, False
        
        elif any(msg in error_message for msg in ["fee too low", "underpriced"]):
            return self.increase_gas_price(tx, 0.5, "Fee transaksi terlalu rendah")
 
        elif "already known" in error_message or "already exists" in error_message:
            print_warning(f"⚠️ Transaksi sudah diproses. Menunggu konfirmasi...")
            if 'hash' in error_message:
                import re
                hash_match = re.search(r'(0x[a-fA-F0-9]{64})', error_message)
                if hash_match:
                    tx_hash = hash_match.group(1)
                    self.wait_for_transaction_completion(tx_hash)
            return None, False

        elif "mempool is full" in error_message:
            print_warning(f"⚠️ Mempool penuh. Mencoba beralih RPC...")
            if self.switch_rpc():
                return tx, True
            else:
                # Jika tidak bisa beralih RPC, tunggu dan naikkan gas
                sleep_seconds(CONFIG["COOLDOWN"]["ERROR"][1], "Menunggu mempool tidak penuh")
                return self.increase_gas_price(tx, 0.85, "Mempool penuh")
        
        # RPC error (429 too many requests, etc)
        elif "429" in error_message or "too many requests" in error_message:
            print_warning(f"⚠️ RPC membatasi permintaan (429). Mencoba beralih RPC...")
            if self.switch_rpc():
                return tx, True
            sleep_seconds(CONFIG["COOLDOWN"]["ERROR"][0], "Menunggu RPC tersedia")
            return tx, True
            
        else:
            if isinstance(self.gas_price, dict):
                max_fee_gwei = self.web3.from_wei(self.gas_price["maxFeePerGas"], "gwei")
            else:
                max_fee_gwei = self.web3.from_wei(self.gas_price, "gwei")
                
            if max_fee_gwei < 2:
                factor = 0.3
            elif max_fee_gwei < 4:
                factor = 0.6
            else:
                factor = 0.8
                
            return self.increase_gas_price(tx, factor, "Error tidak dikenal")
            
    def increase_gas_price(self, tx, factor, reason):
        """Helper function untuk menaikkan gas price dengan batas maksimum"""
        max_allowed = self.web3.to_wei(CONFIG["GAS_MAX_GWEI"], "gwei")
        
        if isinstance(self.gas_price, dict):
            new_max_fee = int(self.gas_price["maxFeePerGas"] * factor)
            if new_max_fee > max_allowed:
                new_max_fee = max_allowed
                
            self.gas_price["maxFeePerGas"] = new_max_fee
            self.gas_price["maxPriorityFeePerGas"] = min(
                int(self.gas_price["maxPriorityFeePerGas"] * factor),
                self.web3.to_wei(5, "gwei")
            )
            
            tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
            tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
            
            new_max_fee_gwei = self.web3.from_wei(self.gas_price["maxFeePerGas"], "gwei")
            print_warning(f"⚠️ {reason}. Dinaikkan ke {new_max_fee_gwei:.6f} Gwei")
        else:
            new_gas_price = int(self.gas_price * factor)
            if new_gas_price > max_allowed:
                new_gas_price = max_allowed
                
            self.gas_price = new_gas_price
            tx["gasPrice"] = self.gas_price
            
            new_gas_gwei = self.web3.from_wei(self.gas_price, "gwei")
            print_warning(f"⚠️ {reason}. Dinaikkan ke {new_gas_gwei:.6f} Gwei")
            
        return tx, True

    def track_gas_usage(self, tx_receipt, gas_price):
        gas_used = tx_receipt.gasUsed
        cost_wei = gas_used * (
            gas_price if isinstance(gas_price, int) 
            else gas_price["maxFeePerGas"]
        )
        cost_eth = self.web3.from_wei(cost_wei, "ether")
        print_info(f"📊 Gas terpakai: {gas_used} | Biaya: {cost_eth:.8f} {CHAIN_SYMBOLS.get(self.web3.eth.chain_id, '0G')}")

    def send_transaction(self, tx, private_key, tx_type=""):
        """Kirim transaksi dengan penanganan error yang lebih baik"""
        retries = CONFIG["MAX_RETRIES"]

        if "gasPrice" in tx and tx["gasPrice"] <= 0:
            print_warning("⚠️ Gas price nol terdeteksi, memperbaiki...")
            tx["gasPrice"] = self.web3.to_wei(CONFIG["GAS_MIN_GWEI"], "gwei")
        elif "maxFeePerGas" in tx and tx["maxFeePerGas"] <= 0:
            print_warning("⚠️ maxFeePerGas nol terdeteksi, memperbaiki...")
            tx["maxFeePerGas"] = self.web3.to_wei(CONFIG["GAS_MIN_GWEI"], "gwei")
            tx["maxPriorityFeePerGas"] = self.web3.to_wei(0.5, "gwei")

        consecutive_failures = 0
        rpc_switch_attempts = 0  # Menghitung berapa kali mencoba switch RPC

        while retries > 0:
            try:
                wallet = self.web3.eth.account.from_key(private_key)
                signed = self.web3.eth.account.sign_transaction(tx, private_key)
                receipt = self.web3.eth.send_raw_transaction(signed.rawTransaction)
                tx_hash = receipt.hex()
        
                consecutive_failures = 0
                rpc_switch_attempts = 0  # Reset counter setelah berhasil

                self.tx_counter += 1
                print_success(MESSAGES["TX_SENT"].format(tx_type, self.tx_counter, tx_hash))

                tx_receipt = self.wait_for_transaction_completion(tx_hash)
        
                if tx_receipt:
                    if tx_receipt.status == 1:
                        print_success(f"✅ Transaksi berhasil dikonfirmasi!")
                        gas_price = tx.get("gasPrice", tx.get("maxFeePerGas", 0))
                        self.track_gas_usage(tx_receipt, gas_price)
                        return tx_receipt
                    else:
                        print_error(f"❌ Transaksi gagal di blockchain! Cek explorer untuk detail.")
                        return None
                else:
                    print_warning(f"⏱️ Timeout menunggu konfirmasi, tetapi transaksi mungkin berhasil. TxID: {tx_hash}")
                    return {'transactionHash': tx_hash}
                
            except Exception as e:
                error_msg = str(e).lower()
                consecutive_failures += 1
            
                # Jika error terkait dengan RPC (429, dst), coba switch RPC langsung
                if "429" in error_msg or "too many requests" in error_msg:
                    if rpc_switch_attempts < 3:  # Batasi jumlah percobaan switch RPC
                        print_warning(f"⚠️ RPC membatasi permintaan (429). Mencoba beralih RPC...")
                        if self.switch_rpc():
                            rpc_switch_attempts += 1
                            continue  # Langsung coba lagi dengan RPC baru
            
                # Jika gagal 3x berturut-turut, reset gas price
                if consecutive_failures >= 3:
                    self.reset_gas_price()
                    consecutive_failures = 0
            
                    # Update tx dengan gas price yang di-reset
                    if "gasPrice" in tx:
                        tx["gasPrice"] = self.gas_price
                    elif "maxFeePerGas" in tx:
                        tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                        tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
            
                updated_tx, should_retry = self.handle_tx_error(e, tx)
                if not should_retry or updated_tx is None:
                    retries = 0
                    print_error(f"❌ Transaksi tidak dapat dikirim: {str(e)}")
                    return None
        
                tx = updated_tx
                retries -= 1
                print_warning(f"⚠️ Error mengirim transaksi. Sisa percobaan: {retries}.")
        
                if retries > 0:
                    delay = random.randint(CONFIG["COOLDOWN"]["ERROR"][0], CONFIG["COOLDOWN"]["ERROR"][1])
                    sleep_seconds(delay, "Menunggu sebelum retry")

        return None

    def perform_token_approval(self, token_symbol, router_address, amount_in_wei, sender_address, private_key):
        """Fungsi helper untuk proses approval token"""
        approval_tx = self.build_approval_tx(token_symbol, router_address, amount_in_wei, sender_address)
        if not approval_tx:
            print_error(f"❌ Gagal membangun transaksi approval.")
            return None
            
        approval_receipt = self.send_transaction(approval_tx, private_key, f"Approval {token_symbol}")
        if not approval_receipt:
            print_error(f"❌ Approval {token_symbol} gagal.")
            return None
            
        print_success(f"✅ Approval {token_symbol} berhasil!")

        if 'transactionHash' in approval_receipt:
            tx_hash = approval_receipt['transactionHash']
            if isinstance(tx_hash, bytes):
                tx_hash = tx_hash.hex()
            full_receipt = self.wait_for_transaction_completion(tx_hash)
            if not full_receipt or full_receipt.status != 1:
                print_error(f"❌ Approval {token_symbol} gagal pada konfirmasi.")
                return None
        
        # Delay untuk memastikan konfirmasi detik
        sleep_seconds(random.randint(7, 15), "Memastikan konfirmasi approval")
        return approval_receipt
    
    def perform_token_swap(self, token_in, token_out, amount_in_wei, sender_address, private_key):
        """Fungsi helper untuk proses swap token"""
        swap_tx = self.build_swap_tx(token_in, token_out, amount_in_wei, sender_address)
        if not swap_tx:
            print_error(f"❌ Gagal membangun transaksi swap.")
            return None
            
        swap_receipt = self.send_transaction(swap_tx, private_key, f"Swap {token_in}->{token_out}")
        if not swap_receipt:
            print_error(f"❌ Swap {token_in} ke {token_out} gagal.")
            return None
            
        print_success(f"✅ Swap {token_in} ke {token_out} berhasil!")
        return swap_receipt

    def swap_token_to_token(self, private_key, token_in, token_out, wallet_num=0, total_wallets=1):
        """Lakukan swap dari satu token ke token lain dengan penanganan nonce yang lebih baik"""
        max_retries = 2  # Jumlah maksimum percobaan untuk swap keseluruhan
    
        for retry in range(max_retries):
            try:
                # Pastikan RPC terhubung
                if not self.web3.is_connected():
                    print(f" ⚠️ RPC tidak terhubung, mencoba beralih...")
                    if not self.switch_rpc():
                        print_error(f"❌ Gagal terhubung ke RPC. Membatalkan swap.")
                        return False
            
                wallet = self.web3.eth.account.from_key(private_key)
                address = wallet.address

                self.reset_pending_transactions(address, private_key)

                decimals = self.token_decimals.get(token_in, 18)
            
                if token_in == "USDT":
                    random_amount = round(random.uniform(CONFIG["SWAP_AMOUNT_USDT"][0], CONFIG["SWAP_AMOUNT_USDT"][1]), 2)
                elif token_in == "ETH":
                    random_amount = round(random.uniform(CONFIG["SWAP_AMOUNT_ETH"][0], CONFIG["SWAP_AMOUNT_ETH"][1]), 6)
                elif token_in == "BTC":
                    random_amount = round(random.uniform(CONFIG["SWAP_AMOUNT_BTC"][0], CONFIG["SWAP_AMOUNT_BTC"][1]), 6)
                else:
                    random_amount = round(random.uniform(0.01, 0.03), 2)
                
                amount_in_wei = int(random_amount * (10 ** decimals))
            
                print_debug(f"🔄 Memulai random swap {random_amount} {token_in} </> {token_out}", wallet_num, total_wallets)
            
                try:
                    self.check_wallet_balance(address, token_in)
                except Exception as balance_error:
                    if "429" in str(balance_error).lower() and retry < max_retries - 1:
                        print_warning(f"⚠️ Error RPC saat memeriksa saldo. Mencoba beralih RPC...")
                        if self.switch_rpc():
                            continue  # Coba lagi dari awal
                        else:
                            print_error(f"❌ Gagal beralih RPC. Membatalkan swap.")
                            return False
                    else:
                        raise  # Reaise error lainnya
            
                router_address = TOKEN_ADDRESSES["ROUTER"]
                approval_result = self.perform_token_approval(token_in, router_address, amount_in_wei, address, private_key)
                if not approval_result:
                    if retry < max_retries - 1:
                        print(f"⚠️  Approval gagal, mencoba lagi setelah beralih RPC...")
                        if self.switch_rpc():
                            continue  # Coba lagi dari awal
                    return False

                swap_result = self.perform_token_swap(token_in, token_out, amount_in_wei, address, private_key)
                if not swap_result:
                    if retry < max_retries - 1:
                        print_warning(f"⚠️ Swap gagal, mencoba lagi setelah beralih RPC...")
                        if self.switch_rpc():
                            continue  # Coba lagi dari awal
                    return False

                sleep_seconds(5, "Memperbarui saldo")
                self.check_wallet_balance(address, token_out)

                delay = random.randint(CONFIG["COOLDOWN"]["SUCCESS"][0], CONFIG["COOLDOWN"]["SUCCESS"][1])
                sleep_seconds(delay, "Cooldown setelah transaksi berhasil")
            
                return True
            
            except Exception as e:
                error_msg = str(e).lower()
            
                # Jika error terkait dengan RPC, coba switch RPC
                if "429" in error_msg or "too many requests" in error_msg:
                    if retry < max_retries - 1:
                        print_warning(f"⚠️ RPC error: {str(e)}. Mencoba beralih RPC...")
                        if self.switch_rpc():
                            continue  # Coba lagi dari awal dengan RPC baru
            
                print_error(f"❌ Error dalam proses swap: {str(e)}")
            
                if retry < max_retries - 1:
                    print_warning(f"⚠️ Mencoba swap lagi (percobaan {retry+2}/{max_retries})...")
                    sleep_seconds(10, "Menunggu sebelum mencoba lagi")
                else:
                    return False
    
        return False

    def process_swaps(self, account, wallet_num, total_wallets, is_last_wallet=False):
        """Proses beberapa swap untuk satu wallet"""
        private_key = account["key"]
        address = account["address"]
        
        print(f"🔄 Menggunakan wallet {Fore.YELLOW}[{wallet_num}/{total_wallets}]{Fore.RESET} -> {Fore.YELLOW}{short_address(address)}{Fore.RESET}")
        
        tx_count = random.randint(CONFIG["TRANSACTIONS_PER_WALLET"][0], CONFIG["TRANSACTIONS_PER_WALLET"][1])
        print(f"📊 Merencanakan {Fore.MAGENTA}{tx_count} transaksi TXiD{Fore.RESET} untuk wallet ini")

        initial_balance = self.check_wallet_balance(address)

        success_count = 0
        
        swap_sequences = [
            ("USDT", "BTC"),
            ("USDT", "ETH"),
            ("USDT", "BTC"),
            ("USDT", "ETH"),
        ]
        
        for i in range(tx_count):
            print(f"🔄 Transaksi {Fore.YELLOW}[{i+1}/{tx_count}]{Fore.RESET} untuk {Fore.YELLOW}[wallet {wallet_num}]{Fore.RESET}")
            
            swap_in, swap_out = swap_sequences[i % len(swap_sequences)]
            
            success = self.swap_token_to_token(private_key, swap_in, swap_out, wallet_num, total_wallets)
            
            if success:
                success_count += 1
            else:
                print(f"⚠️  Transaksi {i+1} gagal, lanjut ke transaksi berikutnya")
            
            # Delay antara transaksi dalam wallet yang sama deitk
            if i < tx_count - 1:
                delay = random.randint(90, 300)
                sleep_seconds(delay, "Menunggu untuk transaksi berikutnya")
        
        sleep_seconds(5, "Memperbarui saldo")
        final_balance = self.check_wallet_balance(address)

        gas_used = initial_balance - final_balance
        gas_cost_eth = self.web3.from_wei(gas_used, "ether")
        chain_id = self.web3.eth.chain_id
        token_symbol = CHAIN_SYMBOLS.get(chain_id, "0G")
        
        print_info(f"💰 Ringkasan wallet {wallet_num}: {success_count}/{tx_count} transaksi berhasil")
        print_info(f"⛽ Biaya gas total: {gas_cost_eth:.8f} {token_symbol}")
        
        # delay wallet terakhir, terapkan delay panjang cek config
        if is_last_wallet:
            delay_seconds = random.randint(
                CONFIG["CYCLE_COMPLETE_DELAY"][0], 
                CONFIG["CYCLE_COMPLETE_DELAY"][1]
            )
            print_success(f"🔄 Semua wallet telah diproses! Siklus {self.cycle_count} selesai.")

            # Waktu target untuk siklus berikutnya
            #now = datetime.datetime.now()
            #target_time = datetime.datetime(now.year, now.month, now.day, 10, 0, 0)
            
            #if now > target_time:
            #    target_time = target_time + datetime.timedelta(days=1)
                
            # Kalkulasi delay untuk menunggu hingga target_time
            #time_delta = target_time - now
            #if time_delta.total_seconds() > 0:
            #    delay_to_target = int(time_delta.total_seconds())
                # Gunakan waktu yang terpendek antara CYCLE_COMPLETE_DELAY dan waktu ke target
            #    delay_seconds = min(delay_seconds, delay_to_target)
            #    print_info(f"⏳ Menunggu {delay_seconds//60} menit untuk siklus berikutnya ({target_time.strftime('%Y-%m-%d %H:%M:%S')})")
            #else:
            print_info(f"⏳ Menunggu {delay_seconds//60} menit untuk siklus berikutnya")   
            sleep_seconds(delay_seconds, f"Menunggu siklus berikutnya ({self.cycle_count + 1})")
            self.cycle_count += 1
        else:
            delay_seconds = random.randint(
                CONFIG["WALLET_SWITCH_DELAY"][0], 
                CONFIG["WALLET_SWITCH_DELAY"][1]
            )
            sleep_seconds(delay_seconds, "Beralih ke wallet berikutnya")
        
        return success_count > 0

    def execute_cycle(self):
        """Eksekusi satu siklus swap untuk semua wallet"""
        print(f"🔄 Memulai siklus swap ke [{self.cycle_count}] dengan [{len(self.accounts)}] wallet")
    
        # Pastikan RPC terhubung atau beralih
        if not self.web3.is_connected():
            print(f"🔄 Koneksi RPC hilang sebelum siklus, mencoba beralih...")
            if not self.switch_rpc():
                print_warning(f"❌ Gagal menemukan RPC yang berfungsi. Menunggu sebelum mencoba lagi...")
                sleep_seconds(60)  # Tunggu satu menit sebelum mencoba siklus lagi
                if not self.switch_rpc():
                    print_error(f"❌ Masih tidak ada RPC yang berfungsi. Keluar dari siklus.")
                    return False
    
        self.update_gas_price()
    
        for idx, account in enumerate(self.accounts):
            wallet_num = idx + 1
            is_last_wallet = idx == len(self.accounts) - 1
        
            success = self.process_swaps(account, wallet_num, len(self.accounts), is_last_wallet)
            if not success:
                print_warning(f"⚠️ Semua transaksi pada wallet {wallet_num} gagal. Lanjut ke wallet berikutnya.")
    
        print_success(f"✅ Siklus #{self.cycle_count} selesai untuk semua wallet")
        return True

# ======================== Main Function ========================
def main():
    global_retries = 3
    retry_delay = 60  # dtik
    
    while global_retries > 0:
        try:
            print_banner()

            CONFIG["RPC_URLS"] = validate_rpc_urls(CONFIG["RPC_URLS"])
            
            swapper = OGSwapper()
            swapper.initialize()
            
            try:
                while True:
                    swapper.execute_cycle()
            except KeyboardInterrupt:
                print_warning("\n⚠️ Program dihentikan oleh pengguna. Keluar...")
                return
                
        except ConnectionError as e:
            global_retries -= 1
            print_error(f"❌ Error koneksi: {str(e)}")
            if global_retries > 0:
                print_warning(f"⏳ Mencoba ulang dalam {retry_delay} detik...")
                time.sleep(retry_delay)
                retry_delay *= 2  # backoff
            else:
                print_error("❌ Nyerah bang setelah beberapa kali percobaan.")
                exit(1)
        except Exception as e:
            print_error(f"❌ Error dalam program: {str(e)}")
            exit(1)

if __name__ == "__main__":
    main()
