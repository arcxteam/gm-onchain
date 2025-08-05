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
        "https://evmrpc-testnet.0g.ai,https://0g-testnet-rpc.astrostake.xyz,https://0g-galileo-evmrpc2.corenodehq.xyz/"
    ).split(","),
    "PRIVATE_KEY_FILE": os.path.join(os.path.dirname(__file__), "private_keys.txt"),
    "ENV_FILE": ".env",
    "MAX_RETRIES": 5,
    "GAS_MULTIPLIER": 1.01,
    "GAS_RANGE_GWEI": (0.005, 0.1),  # Rentang gas acak untuk EIP-1559 dan Legacy
    "GAS_LIMIT": 250000,
    "GAS_LIMIT_USDT_APPROVAL": 150000,  # Gas approval USDT
    "COOLDOWN": {"SUCCESS": (20, 60), "ERROR": (20, 60)},  # detik
    "WALLET_SWITCH_DELAY": (300, 1000),  # detik
    "CYCLE_COMPLETE_DELAY": (7200, 14400),  # detik
    "TRANSACTIONS_PER_WALLET": (10, 15),  # tx per wallet
    "SWAP_AMOUNT_USDT": 1,  # fixed 1 USDT
    "RPC_TIMEOUT": 15,  # detik
    "RPC_RETRY_DELAY": 10,  # detik
}

CHAIN_SYMBOLS = {16601: "0G"}

# ================= Contract Addresses ===================
TOKEN_ADDRESSES = {
    "ROUTER": Web3.to_checksum_address("0xdcd7d05640be92ec91ceb1c9ea18e88aff3a6900"),
    "USDT": Web3.to_checksum_address("0x217C6f12d186697b16dE9e1ae9F85389B93BdB30"),
    "MTP": Web3.to_checksum_address("0x5506ebd25960fb30704c2dc548c3da7351277eba"),
    "ZFI": Web3.to_checksum_address("0x9fbc11391167f113641492be2b10dfe729ea5063"),
    "FLOV": Web3.to_checksum_address("0x8f65e752bd9bde431808c9d07fa0cb835acf83cc"),
    "GSWP": Web3.to_checksum_address("0x42ce92e9c25d22827b97e3b8cba75bb6f769e8fd"),
    "NPAY": Web3.to_checksum_address("0x25F9F6D80BA137481C2E2C50d4Fe0F7586e06cF0"),
    "BYTX": Web3.to_checksum_address("0xE226Ceb3BfE97d416fE099BCA68251238D28C1E5"),
    "THPY": Web3.to_checksum_address("0xc4d03e091e21a069b8bf9fca254620bcb8ca806a"),
    "MPTC": Web3.to_checksum_address("0xC3461CF239bbf520D0853fFB60fa05cdD819C814"),
    "MCHN": Web3.to_checksum_address("0x56486f582f55448e58c0321a01a61111cfd99d63"),
    "GRMS": Web3.to_checksum_address("0xca223a007868f3efd7d61c6f6f87a2cc3336c123"),
    "DRNT": Web3.to_checksum_address("0x5f9909a75f871320b9a93574bd6589c82291e391"),
    "ECHO": Web3.to_checksum_address("0xefb05f9d387d5c24967439c3b949b14d1e474983"),
}

# ==================== ABIs ========================
ROUTER_ABI = [
    {
        "name": "swapExactTokensForTokens",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]
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
 ██████╗██╗   ██║ █████╗ ███╗   ██╗███╗   ██║ ██████╗ ██████╗ ███████╗
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
            "MTP": 18,
            "ZFI": 18,
            "FLOV": 18,
            "GSWP": 18,
            "NPAY": 18,
            "BYTX": 18,
            "THPY": 18,
            "MPTC": 18,
            "MCHN": 18,
            "GRMS": 18,
            "DRNT": 18,
            "ECHO": 18,
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
        
        if not available_rpcs:
            available_rpcs = [(i, url) for i, url in enumerate(CONFIG["RPC_URLS"]) if i != old_index]
        
        if not available_rpcs:
            sleep_seconds(CONFIG["RPC_RETRY_DELAY"], "Menunggu sebelum mencoba ulang RPC yang sama")
            return False
        
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
            latest_block = self.web3.eth.get_block('latest')
            if 'baseFeePerGas' in latest_block and latest_block['baseFeePerGas']:
                print("✅ Jaringan mendukung EIP-1559 (metode 1)")
                return True
            
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
        """Dapatkan parameter gas EIP-1559 dengan nilai acak"""
        try:
            if not self.check_eip1559_support():
                return None

            fee_history = self.web3.eth.fee_history(1, 'latest')
            base_fee = fee_history['baseFeePerGas'][0]

            # Gunakan nilai acak dalam rentang GAS_RANGE_GWEI untuk maxPriorityFeePerGas
            max_priority_gwei = random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1])
            max_priority = self.web3.to_wei(max_priority_gwei, 'gwei')
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
        """Dapatkan legacy gas price dengan nilai acak dalam rentang"""
        try:
            # Gunakan nilai acak dalam rentang GAS_RANGE_GWEI
            gas_price_gwei = random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1])
            gas_price = self.web3.to_wei(gas_price_gwei, "gwei")
            
            print_info(f"⛽ Gas price: {gas_price_gwei:.2f} Gwei (Legacy Mode)")
            
            return gas_price
        except Exception as e:
            print_error(f"❌ Estimasi legacy gas gagal: {str(e)}")
            gas_price_gwei = random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1])
            gas_price = self.web3.to_wei(gas_price_gwei, "gwei")
            print_warning(f"⚠️ Menggunakan gas price acak: {gas_price_gwei:.2f} Gwei")
            return gas_price

    def reset_gas_price(self):
        """Reset gas price ke nilai acak dalam rentang setelah terlalu banyak retry"""
        if isinstance(self.gas_price, dict):
            max_priority_gwei = random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1])
            self.gas_price["maxFeePerGas"] = self.web3.to_wei(max_priority_gwei, "gwei")
            self.gas_price["maxPriorityFeePerGas"] = self.web3.to_wei(max_priority_gwei, "gwei")
            print_warning(MESSAGES["GAS_RESET"] + f": {max_priority_gwei:.2f} Gwei")
        else:
            gas_price_gwei = random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1])
            self.gas_price = self.web3.to_wei(gas_price_gwei, "gwei")
            print_warning(MESSAGES["GAS_RESET"] + f": {gas_price_gwei:.2f} Gwei")

    def update_gas_price(self):
        """Update gas price dengan EIP-1559 atau legacy menggunakan nilai acak"""
        eip1559_params = self.get_eip1559_gas_params()
        if eip1559_params:
            self.gas_price = eip1559_params
            print_success("✅ Menggunakan mode gas EIP-1559")
        else:
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
                        continue
            
                if retry == max_retries - 1:
                    print_error(f"❌ Error memeriksa saldo setelah {max_retries} percobaan: {str(e)}")
                    return 0
            
                sleep_seconds(10, "Menunggu sebelum mencoba memeriksa saldo lagi")
    
        return 0

    def estimate_gas(self, contract_func, sender):
        """Fungsi generik untuk estimasi gas dengan fallback ke default"""
        try:
            estimate_gas = contract_func.estimate_gas({'from': sender})
            gas_limit = max(int(estimate_gas * 0.8), CONFIG["GAS_LIMIT"])  # Buffer 120%, minimal GAS_LIMIT
            print_info(f"⛽ Estimasi gas: {estimate_gas}, digunakan: {gas_limit}")
            return gas_limit
        except Exception as e:
            default_gas = CONFIG["GAS_LIMIT"]
            print_warning(f"⚠️ Estimasi gas gagal: {str(e)}. Menggunakan default: {default_gas}")
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
            
            print_info(f"📝 Transaksi {description} dibuat dengan nonce {nonce}, gas limit: {gas_limit}")
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
            # Gunakan gas limit khusus untuk USDT
            if token_symbol == "USDT":
                gas_limit = max(gas_limit, CONFIG["GAS_LIMIT_USDT_APPROVAL"])
                print_info(f"⛽ Menggunakan gas limit khusus untuk approval USDT: {gas_limit}")
            
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
        """Buat transaksi swap token menggunakan swapExactTokensForTokens"""
        try:
            deadline = int(time.time()) + 300  # 5 menit
            path = [
                Web3.to_checksum_address(TOKEN_ADDRESSES[token_in]),
                Web3.to_checksum_address(TOKEN_ADDRESSES[token_out])
            ]
            
            gas_limit = self.estimate_gas(
                self.router_contract.functions.swapExactTokensForTokens(
                    amount, 0, path, sender, deadline
                ),
                sender
            )

            data = self.router_contract.encodeABI(
                fn_name="swapExactTokensForTokens", 
                args=[amount, 0, path, sender, deadline]
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
        max_retries = 3
        for retry in range(max_retries):
            try:
                pending_nonce = self.web3.eth.get_transaction_count(address, "pending")
                latest_nonce = self.web3.eth.get_transaction_count(address, "latest")
            
                if pending_nonce > latest_nonce:
                    print_debug(f"🔄 Menunggu transaksi pending selesai... (pending nonce: {pending_nonce}, latest nonce: {latest_nonce})")
                    time.sleep(15)  # Tunggu lebih lama untuk memastikan sinkronisasi
                    continue
                
                print_info(f"🔢 Menggunakan nonce {latest_nonce}")
                return latest_nonce
            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "too many requests" in error_msg:
                    print_warning(f"⚠️ RPC membatasi permintaan saat mendapatkan nonce. Mencoba beralih RPC...")
                    if self.switch_rpc():
                        continue
                
                if retry == max_retries - 1:
                    print_error(f"❌ Error mendapatkan nonce setelah {max_retries} percobaan: {str(e)}")
                    return self.web3.eth.get_transaction_count(address, "latest")
                
                sleep_seconds(10, "Menunggu sebelum mencoba nonce lagi")
        
        return self.web3.eth.get_transaction_count(address, "latest")

    def wait_for_transaction_completion(self, tx_hash, timeout=150):
        """Menunggu transaksi selesai dengan penanganan error yang lebih baik"""
        print_info(MESSAGES["WAITING_TX"].format(tx_hash))
        start_time = time.time()
    
        last_error_time = 0
        rpc_switched = True # only true or false
        check_interval = 15
    
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

                    # Gunakan gas price acak untuk transaksi dummy
                    if isinstance(self.gas_price, dict):
                        gas_price_gwei = random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1])
                        tx["maxFeePerGas"] = self.web3.to_wei(gas_price_gwei, "gwei")
                        tx["maxPriorityFeePerGas"] = self.web3.to_wei(gas_price_gwei, "gwei")
                    else:
                        gas_price_gwei = random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1])
                        tx["gasPrice"] = self.web3.to_wei(gas_price_gwei, "gwei")

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
        
        elif any(msg in error_message for msg in ["fee too low", "underpriced", "replacement transaction underpriced"]):
            return self.increase_gas_price(tx, 1.5, "Fee transaksi terlalu rendah")
 
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
                sleep_seconds(CONFIG["COOLDOWN"]["ERROR"][1], "Menunggu mempool tidak penuh")
                return self.increase_gas_price(tx, 1.5, "Mempool penuh")
        
        elif "429" in error_message or "too many requests" in error_message:
            print_warning(f"⚠️ RPC membatasi permintaan (429). Mencoba beralih RPC...")
            if self.switch_rpc():
                return tx, True
            sleep_seconds(CONFIG["COOLDOWN"]["ERROR"][0], "Menunggu RPC tersedia")
            return tx, True
            
        else:
            max_fee_gwei = (
                self.web3.from_wei(self.gas_price["maxFeePerGas"], "gwei")
                if isinstance(self.gas_price, dict)
                else self.web3.from_wei(self.gas_price, "gwei")
            )
                
            if max_fee_gwei < CONFIG["GAS_RANGE_GWEI"][1]:
                factor = 1.3
            else:
                factor = 1.0  # Tidak meningkatkan di luar rentang maksimum
                
            return self.increase_gas_price(tx, factor, f"Error tidak dikenal: {error_message}")
            
    def increase_gas_price(self, tx, factor, reason):
        """Helper function untuk menaikkan gas price dengan batas maksimum acak"""
        max_allowed = self.web3.to_wei(CONFIG["GAS_RANGE_GWEI"][1], "gwei")
        min_allowed = self.web3.to_wei(CONFIG["GAS_RANGE_GWEI"][0], "gwei")
        
        if isinstance(self.gas_price, dict):
            current_max_fee = self.gas_price["maxFeePerGas"]
            new_max_fee = int(current_max_fee * factor)
            if new_max_fee > max_allowed:
                new_max_fee = self.web3.to_wei(random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1]), "gwei")
            if new_max_fee < min_allowed:
                new_max_fee = min_allowed
                
            self.gas_price["maxFeePerGas"] = new_max_fee
            self.gas_price["maxPriorityFeePerGas"] = self.web3.to_wei(
                random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1]), "gwei"
            )
            
            tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
            tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
            
            new_max_fee_gwei = self.web3.from_wei(self.gas_price["maxFeePerGas"], "gwei")
            print_warning(f"⚠️ {reason}. Dinaikkan ke {new_max_fee_gwei:.6f} Gwei")
        else:
            current_gas_price = self.gas_price
            new_gas_price = int(current_gas_price * factor)
            if new_gas_price > max_allowed:
                new_gas_price = self.web3.to_wei(random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1]), "gwei")
            if new_gas_price < min_allowed:
                new_gas_price = min_allowed
                
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
            gas_price_gwei = random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1])
            tx["gasPrice"] = self.web3.to_wei(gas_price_gwei, "gwei")
        elif "maxFeePerGas" in tx and tx["maxFeePerGas"] <= 0:
            print_warning("⚠️ maxFeePerGas nol terdeteksi, memperbaiki...")
            gas_price_gwei = random.uniform(CONFIG["GAS_RANGE_GWEI"][0], CONFIG["GAS_RANGE_GWEI"][1])
            tx["maxFeePerGas"] = self.web3.to_wei(gas_price_gwei, "gwei")
            tx["maxPriorityFeePerGas"] = self.web3.to_wei(gas_price_gwei, "gwei")

        consecutive_failures = 0
        rpc_switch_attempts = 0

        while retries > 0:
            try:
                wallet = self.web3.eth.account.from_key(private_key)
                signed = self.web3.eth.account.sign_transaction(tx, private_key)
                receipt = self.web3.eth.send_raw_transaction(signed.rawTransaction)
                tx_hash = receipt.hex()
        
                consecutive_failures = 0
                rpc_switch_attempts = 0

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
            
                if "out of gas" in error_msg:
                    print_warning(f"⚠️ Transaksi kehabisan gas, meningkatkan gas limit...")
                    tx["gas"] = int(tx["gas"] * 1.1)  # Tingkatkan gas limit 50%
                    if tx["gas"] > 200000:  # Batasi gas limit maksimum
                        tx["gas"] = 200000
                    print_info(f"⛽ Gas limit baru: {tx['gas']}")
                    retries -= 1
                    if retries > 0:
                        sleep_seconds(CONFIG["COOLDOWN"]["ERROR"][0], "Menunggu sebelum retry")
                    continue
                
                if "429" in error_msg or "too many requests" in error_msg:
                    if rpc_switch_attempts < 3:
                        print_warning(f"⚠️ RPC membatasi permintaan (429). Mencoba beralih RPC...")
                        if self.switch_rpc():
                            rpc_switch_attempts += 1
                            continue
            
                if consecutive_failures >= 3:
                    self.reset_gas_price()
                    consecutive_failures = 0
            
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
        
        sleep_seconds(random.randint(10, 20), "Memastikan konfirmasi approval")
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
        """Lakukan swap dari USDT ke token lain dengan penanganan nonce yang lebih baik"""
        max_retries = 2
    
        for retry in range(max_retries):
            try:
                if not self.web3.is_connected():
                    print(f" ⚠️ RPC tidak terhubung, mencoba beralih...")
                    if not self.switch_rpc():
                        print_error(f"❌ Gagal terhubung ke RPC. Membatalkan swap.")
                        return False
            
                wallet = self.web3.eth.account.from_key(private_key)
                address = wallet.address

                self.reset_pending_transactions(address, private_key)

                decimals = self.token_decimals.get(token_in, 18)
                amount_in_wei = int(CONFIG["SWAP_AMOUNT_USDT"] * (10 ** decimals))
            
                print_debug(f"🔄 Memulai swap {CONFIG['SWAP_AMOUNT_USDT']} {token_in} </> {token_out}", wallet_num, total_wallets)
            
                try:
                    self.check_wallet_balance(address, token_in)
                except Exception as balance_error:
                    if "429" in str(balance_error).lower() and retry < max_retries - 1:
                        print_warning(f"⚠️ Error RPC saat memeriksa saldo. Mencoba beralih RPC...")
                        if self.switch_rpc():
                            continue
                        else:
                            print_error(f"❌ Gagal beralih RPC. Membatalkan swap.")
                            return False
                    else:
                        raise
            
                router_address = TOKEN_ADDRESSES["ROUTER"]
                approval_result = self.perform_token_approval(token_in, router_address, amount_in_wei, address, private_key)
                if not approval_result:
                    if retry < max_retries - 1:
                        print(f"⚠️ Approval gagal, mencoba lagi setelah beralih RPC...")
                        if self.switch_rpc():
                            continue
                    return False

                swap_result = self.perform_token_swap(token_in, token_out, amount_in_wei, address, private_key)
                if not swap_result:
                    if retry < max_retries - 1:
                        print_warning(f"⚠️ Swap gagal, mencoba lagi setelah beralih RPC...")
                        if self.switch_rpc():
                            continue
                    return False

                sleep_seconds(5, "Memperbarui saldo")
                self.check_wallet_balance(address, token_out)

                delay = random.randint(CONFIG["COOLDOWN"]["SUCCESS"][0], CONFIG["COOLDOWN"]["SUCCESS"][1])
                sleep_seconds(delay, "Cooldown setelah transaksi berhasil")
            
                return True
            
            except Exception as e:
                error_msg = str(e).lower()
            
                if "429" in error_msg or "too many requests" in error_msg:
                    if retry < max_retries - 1:
                        print_warning(f"⚠️ RPC error: {str(e)}. Mencoba beralih RPC...")
                        if self.switch_rpc():
                            continue
            
                print_error(f"❌ Error dalam proses swap: {str(e)}")
            
                if retry < max_retries - 1:
                    print_warning(f"⚠️ Mencoba swap lagi (percobaan {retry+2}/{max_retries})...")
                    sleep_seconds(10, "Menunggu sebelum mencoba lagi")
                else:
                    return False
    
        return False

    def process_swaps(self, account, wallet_num, total_wallets, is_last_wallet=False):
        """Proses beberapa swap untuk satu wallet, hanya USDT ke token lain"""
        private_key = account["key"]
        address = account["address"]
        
        print(f"🔄 Menggunakan wallet {Fore.YELLOW}[{wallet_num}/{total_wallets}]{Fore.RESET} -> {Fore.YELLOW}{short_address(address)}{Fore.RESET}")
        
        tx_count = random.randint(CONFIG["TRANSACTIONS_PER_WALLET"][0], CONFIG["TRANSACTIONS_PER_WALLET"][1])
        print(f"📊 Merencanakan {Fore.MAGENTA}{tx_count} transaksi TXiD{Fore.RESET} untuk wallet ini")

        initial_balance = self.check_wallet_balance(address)

        success_count = 0
        
        swap_sequences = [
            ("USDT", "ZFI"),
            ("USDT", "MTP"),
            ("USDT", "FLOV"),
            ("USDT", "GSWP"),
            ("USDT", "NPAY"),
            ("USDT", "BYTX"),
            ("USDT", "THPY"),
            ("USDT", "MPTC"),
            ("USDT", "MCHN"),
            ("USDT", "GRMS"),
            ("USDT", "DRNT"),
            ("USDT", "ECHO"),
        ]
        
        for i in range(tx_count):
            print(f"🔄 Transaksi {Fore.YELLOW}[{i+1}/{tx_count}]{Fore.RESET} untuk {Fore.YELLOW}[wallet {wallet_num}]{Fore.RESET}")
            
            swap_in, swap_out = swap_sequences[i % len(swap_sequences)]
            
            success = self.swap_token_to_token(private_key, swap_in, swap_out, wallet_num, total_wallets)
            
            if success:
                success_count += 1
            else:
                print(f"⚠️ Transaksi {i+1} gagal, lanjut ke transaksi berikutnya")
            
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
        
        if is_last_wallet:
            delay_seconds = random.randint(
                CONFIG["CYCLE_COMPLETE_DELAY"][0], 
                CONFIG["CYCLE_COMPLETE_DELAY"][1]
            )
            print_success(f"🔄 Semua wallet telah diproses! Siklus {self.cycle_count} selesai.")
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
    
        if not self.web3.is_connected():
            print(f"🔄 Koneksi RPC hilang sebelum siklus, mencoba beralih...")
            if not self.switch_rpc():
                print_warning(f"❌ Gagal menemukan RPC yang berfungsi. Menunggu sebelum mencoba lagi...")
                sleep_seconds(60)
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
    retry_delay = 60
    
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
                retry_delay *= 2
            else:
                print_error("❌ Nyerah bang setelah beberapa kali percobaan.")
                exit(1)
        except Exception as e:
            print_error(f"❌ Error dalam program: {str(e)}")
            exit(1)

if __name__ == "__main__":
    main()
