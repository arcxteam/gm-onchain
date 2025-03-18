import os
import time
import json
import random
import logging
import datetime
from web3 import Web3 # type: ignore
from pathlib import Path
from colorama import Fore, Style, init # type: ignore
from dotenv import load_dotenv # type: ignore

init(autoreset=True)
load_dotenv()

# ======================== Configuration ========================
CONFIG = {
    # RPC endpoints untuk jaringan 0G Newton
    "RPC_URLS": os.getenv(
        "RPC_URLS",
        "https://16600.rpc.thirdweb.com,https://evmrpc-testnet.0g.ai,https://evm-rpc.0g.testnet.node75.org,https://rpc.ankr.com/0g_newton"
    ).split(","),
    # File untuk menyimpan private keys
    "PRIVATE_KEY_FILE": os.path.join(os.path.dirname(__file__), "private_keys.txt"),
    # File .env untuk private key alternatif
    "ENV_FILE": ".env",
    # Maksimal retry jika transaksi gagal
    "MAX_RETRIES": 5,
    # Pengali gas price
    "GAS_MULTIPLIER": 1.5,
    # Max priority fee untuk EIP-1559 (gwei)
    "MAX_PRIORITY_GWEI": 2.5,
    # Gas limit default
    "GAS_LIMIT": 280000,
    # Cooldown setelah transaksi (dalam detik)
    "COOLDOWN": {"SUCCESS": (15, 120), "ERROR": (30, 180)},
    # Delay antar wallet (dalam detik)
    "WALLET_SWITCH_DELAY": (120, 480),
    # Delay setelah semua wallet digunakan (dalam detik)
    "CYCLE_COMPLETE_DELAY": (3600, 7200),
    # Jumlah transaksi per wallet per siklus
    "TRANSACTIONS_PER_WALLET": (3, 8),
    # Random swap amounts (in USDT units)
    "SWAP_AMOUNT_USDT": (1.5, 3.5),
    "SWAP_AMOUNT_ETH": (0.002, 0.005),
    "SWAP_AMOUNT_BTC": (0.0002, 0.0005),
}

# ======================== Chain Info ========================
CHAIN_SYMBOLS = {16600: "A0GI"}

# ======================== Token Addresses ========================
TOKEN_ADDRESSES = {
    "ROUTER": "0xD86b764618c6E3C078845BE3c3fCe50CE9535Da7",
    "USDT": "0x9A87C2412d500343c073E5Ae5394E3bE3874F76b",
    "ETH": "0xce830D0905e0f7A9b300401729761579c5FB6bd6",
    "BTC": "0x1e0d871472973c562650e991ed8006549f8cbefc",
}

# ======================== ABIs ========================
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

# Token ABI (ERC20)
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

# ======================== Logging Setup ========================
def log_info(message):
    print(message)

def log_error(message):
    print(f"{Fore.RED}{message}{Style.RESET_ALL}")

def log_success(message):
    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")

def log_warning(message):
    print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")

def log_debug(message, num=None, total=None):
    if num is not None and total is not None:
        print(f"{Fore.CYAN}[{num}/{total}] {message}{Style.RESET_ALL}")
    else:
        print(f"{Fore.CYAN}{message}{Style.RESET_ALL}")

# ======================== Helper Functions ========================
def short_address(address):
    """Format address dengan singkat: 0x1234...5678"""
    return f"{address[:6]}...{address[-4:]}" if address else "Unknown address"

def sleep_seconds(seconds, message=None):
    """Fungsi sleep dengan pesan informatif"""
    if message:
        print(f"⏳ {Fore.YELLOW}{message} dalam {seconds} detik...{Style.RESET_ALL}")
    else:
        print(f"⏳ {Fore.YELLOW}Menunggu {seconds} detik...{Style.RESET_ALL}")
    time.sleep(seconds)

def random_sleep(min_secs, max_secs, message=None):
    """Sleep dengan durasi acak"""
    seconds = random.randint(min_secs, max_secs)
    sleep_seconds(seconds, message)
    
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
{Fore.GREEN}========================================================================={Fore.RESET}
{Fore.MAGENTA}       Welcome to 0G-Gravity Onchain Testnet & Mainnet Interactive   {Fore.RESET}
{Fore.YELLOW}           - CUANNODE By Greyscope&Co, Credit By Arcxteam -     {Fore.RESET}
{Fore.GREEN}========================================================================={Fore.RESET}
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
        
        # Token decimals
        self.token_decimals = {
            "USDT": 18,
            "ETH": 18,
            "BTC": 18
        }

    def initialize(self):
        """Inisialisasi connection dan load accounts"""
        self.connect_to_rpc()
        self.load_accounts()
        self.update_gas_price()
        self.initialize_contracts()

    def connect_to_rpc(self):
        """Connect ke RPC endpoint, dengan rotasi jika gagal"""
        for i, rpc_url in enumerate(CONFIG["RPC_URLS"]):
            try:
                self.current_rpc_index = i
                w3 = Web3(Web3.HTTPProvider(rpc_url.strip()))
                if w3.is_connected():
                    chain_id = w3.eth.chain_id
                    log_success(f"🌐 Terhubung ke RPC: {rpc_url}")
                    log_info(f"📡 Chain ID: {chain_id} - {CHAIN_SYMBOLS.get(chain_id, 'Unknown')}")
                    self.web3 = w3
                    return True
            except Exception as e:
                log_warning(f"⚠️ Gagal terhubung ke RPC {rpc_url}: {str(e)}")
        
        if not self.web3:
            log_error("❌ Gagal terhubung ke semua RPC endpoint.")
            raise ConnectionError("Tidak dapat terhubung ke jaringan 0G. Periksa RPC URLs.")

    def switch_rpc(self):
        """Beralih ke RPC lain jika terjadi masalah"""
        old_rpc = CONFIG["RPC_URLS"][self.current_rpc_index]
        self.current_rpc_index = (self.current_rpc_index + 1) % len(CONFIG["RPC_URLS"])
        new_rpc = CONFIG["RPC_URLS"][self.current_rpc_index]
        
        log_warning(f"🔄 Beralih dari RPC {old_rpc} ke {new_rpc}")
        
        try:
            self.web3 = Web3(Web3.HTTPProvider(new_rpc.strip()))
            if self.web3.is_connected():
                self.initialize_contracts()
                log_success(f"✅ Berhasil beralih ke RPC: {new_rpc}")
                return True
        except Exception as e:
            log_error(f"❌ Gagal beralih ke RPC {new_rpc}: {str(e)}")
            return False

    def initialize_contracts(self):
        """Inisialisasi kontrak router"""
        try:
            router_address = Web3.to_checksum_address(TOKEN_ADDRESSES["ROUTER"])
            self.router_contract = self.web3.eth.contract(address=router_address, abi=ROUTER_ABI)
            log_success(f"📝 Kontrak router berhasil diinisialisasi: {short_address(router_address)}")
        except Exception as e:
            log_error(f"❌ Gagal inisialisasi kontrak: {str(e)}")
            raise

    def is_valid_private_key(self, key):
        """Validasi format private key"""
        try:
            if not key or key.startswith("#") or len(key.strip()) < 5:
                return None

            # Standarisasi format key (tambahkan 0x jika tidak ada)
            if not key.startswith("0x"):
                key = "0x" + key

            # Validasi panjang private key
            if len(key) != 66:  # 32 bytes = 64 chars + '0x'
                return None

            # Coba buat akun dari private key
            self.web3.eth.account.from_key(key)
            return key
        except Exception as e:
            log_warning(f"⚠️ Private key tidak valid: {str(e)}")
            return None

    def load_accounts(self):
        """Load private keys dari file dan env"""
        accounts = []

        # Coba load dari .env
        if os.path.exists(CONFIG["ENV_FILE"]):
            try:
                load_dotenv(CONFIG["ENV_FILE"])
                private_key = os.getenv("PRIVATE_KEY")
                if private_key:
                    valid_key = self.is_valid_private_key(private_key)
                    if valid_key:
                        account = self.web3.eth.account.from_key(valid_key)
                        accounts.append({"key": valid_key, "address": account.address})
                        log_success(f"✅ Wallet dari .env berhasil dimuat: {short_address(account.address)}")
            except Exception as e:
                log_error(f"❌ Error loading from .env: {str(e)}")

        # Coba load dari private_keys.txt
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
                                log_success(f"✅ Wallet #{loaded} berhasil dimuat: {short_address(account.address)}")
                        else:
                            log_warning("⚠️ Private key tidak valid, melewatkan...")
            except Exception as e:
                log_error(f"❌ Error loading private keys: {str(e)}")

        if not accounts:
            log_error("❌ Tidak ada private key valid yang ditemukan.")
            exit(1)

        self.accounts = accounts
        log_success(f"📊 Total {len(self.accounts)} wallet berhasil dimuat")

    def get_eip1559_gas_params(self):
        """Dapatkan parameter gas EIP-1559"""
        try:
            # Cek block terbaru memiliki baseFeePerGas
            latest_block = self.web3.eth.get_block('latest')
            if 'baseFeePerGas' in latest_block:
                log_success("✅ Jaringan mendukung EIP-1559")
                return True
            
            # Dapatkan base fee dari blockchain
            fee_history = self.web3.eth.fee_history(1, 'latest')
            if 'baseFeePerGas' not in fee_history or not fee_history['baseFeePerGas'] or len(fee_history['baseFeePerGas']) == 0:
                log_warning("⚠️ EIP-1559 tidak tersedia, menggunakan legacy gas")
                return None
            
            base_fee = fee_history['baseFeePerGas'][0]
            if base_fee is None:
                log_warning("⚠️ EIP-1559 tidak tersedia, menggunakan legacy gas")
                return None

            max_priority = self.web3.to_wei(CONFIG["MAX_PRIORITY_GWEI"], 'gwei')
            max_fee = int(base_fee * CONFIG["GAS_MULTIPLIER"]) + max_priority

            # Convert to Gwei for display
            base_fee_gwei = self.web3.from_wei(base_fee, 'gwei')
            max_fee_gwei = self.web3.from_wei(max_fee, 'gwei')
            max_priority_gwei = self.web3.from_wei(max_priority, 'gwei')

            log_info(f"⛽ Gas: Base Fee: {base_fee_gwei:.2f} Gwei | Max Fee: {max_fee_gwei:.2f} Gwei | Priority: {max_priority_gwei:.2f} Gwei")

            return {'maxFeePerGas': max_fee, 'maxPriorityFeePerGas': max_priority}
        except Exception as e:
            log_error(f"❌ Estimasi EIP-1559 gagal: {str(e)}")
            return None

    def get_legacy_gas_price(self):
        """Dapatkan legacy gas price dengan fallback ke nilai default jika gagal"""
        try:
            # Coba dapatkan gas price dari blockchain
            current = self.web3.eth.gas_price
        
            # Jika gas price terlalu rendah atau 0, gunakan nilai default yang masuk akal
            if current <= self.web3.to_wei(0.5, "gwei"):
                log_warning(f"⚠️ Gas price terlalu rendah ({self.web3.from_wei(current, 'gwei'):.2f} Gwei), menggunakan default")
                gas_price = self.web3.to_wei(1.5, "gwei")  # Nilai default 1.5 Gwei
            else:
                gas_price = int(current * CONFIG["GAS_MULTIPLIER"])
        
            gas_gwei = self.web3.from_wei(gas_price, "gwei")
            log_info(f"⛽ Gas price: {gas_gwei:.2f} Gwei (Legacy Mode)")
        
            return gas_price
        except Exception as e:
            log_error(f"❌ Estimasi legacy gas gagal: {str(e)}")
            # Gunakan nilai default yang masuk akal untuk jaringan 0G
            default_gas = self.web3.to_wei(1.5, "gwei")
            log_warning(f"⚠️ Menggunakan gas price default: 1.5 Gwei")
            return default_gas

    def reset_gas_price(self):
        """Reset gas price ke nilai awal yang wajar setelah terlalu banyak retry"""
        if isinstance(self.gas_price, dict):
            self.gas_price["maxFeePerGas"] = self.web3.to_wei(5, "gwei")
            self.gas_price["maxPriorityFeePerGas"] = self.web3.to_wei(1, "gwei")
            log_warning(f"⚠️ Terlalu banyak retry, mereset gas price ke 5 Gwei")
        else:
            self.gas_price = self.web3.to_wei(5, "gwei")
            log_warning(f"⚠️ Terlalu banyak retry, mereset gas price ke 5 Gwei")

    def update_gas_price(self):
        """Update gas price dengan EIP-1559 atau legacy"""
        # Coba EIP-1559 terlebih dahulu
        eip1559_params = self.get_eip1559_gas_params()
        if eip1559_params:
            self.gas_price = eip1559_params
            log_success("✅ Menggunakan mode gas EIP-1559")
        else:
            # Fallback ke legacy
            self.gas_price = self.get_legacy_gas_price()
            log_success("✅ Menggunakan mode gas Legacy")

    def get_token_contract(self, token_symbol):
        """Dapatkan kontrak untuk token tertentu"""
        token_address = TOKEN_ADDRESSES.get(token_symbol)
        if not token_address:
            raise ValueError(f"Alamat tidak ditemukan untuk token: {token_symbol}")
        
        return self.web3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=TOKEN_ABI
        )

    def check_wallet_balance(self, address, token_symbol=None):
        """Periksa saldo wallet, native token atau token tertentu"""
        try:
            # Native token (A0GI)
            balance_wei = self.web3.eth.get_balance(address)
            balance_eth = self.web3.from_wei(balance_wei, "ether")
            chain_id = self.web3.eth.chain_id
            token_name = CHAIN_SYMBOLS.get(chain_id, "A0GI")
            
            log_info(f"💰 Saldo {token_name}: {balance_eth:.6f}")
            
            # Jika token tertentu diminta
            if token_symbol and token_symbol in TOKEN_ADDRESSES:
                token_contract = self.get_token_contract(token_symbol)
                token_balance = token_contract.functions.balanceOf(address).call()
                token_decimals = self.token_decimals.get(token_symbol, 18)
                token_amount = token_balance / (10 ** token_decimals)
                log_info(f"💰 Saldo {token_symbol}: {token_amount:.6f}")
                return balance_wei, token_balance
                
            return balance_wei
        except Exception as e:
            log_error(f"❌ Error memeriksa saldo: {str(e)}")
            return 0

    def estimate_gas_for_approval(self, token_contract, spender, amount, sender):
        """Estimasi gas untuk approval token"""
        try:
            gas_estimate = token_contract.functions.approve(
                spender, amount
            ).estimate_gas({'from': sender})
            return int(gas_estimate * 1.2)  # Add 20% buffer
        except Exception as e:
            log_warning(f"⚠️ Estimasi gas approval gagal: {str(e)}. Menggunakan nilai default.")
            return 85000  # Default dari ogbot.js

    def estimate_gas_for_swap(self, token_in, token_out, amount, sender):
        """Estimasi gas untuk swap token"""
        try:
            deadline = int(time.time()) + 300  # 5 menit
            gas_estimate = self.router_contract.functions.exactInputSingle(
                {
                    'tokenIn': Web3.to_checksum_address(TOKEN_ADDRESSES[token_in]),
                    'tokenOut': Web3.to_checksum_address(TOKEN_ADDRESSES[token_out]),
                    'fee': 3000,
                    'recipient': sender,
                    'deadline': deadline,
                    'amountIn': amount,
                    'amountOutMinimum': 0,
                    'sqrtPriceLimitX96': 0
                }
            ).estimate_gas({'from': sender})
            return int(gas_estimate * 1.2)  # Add 20% buffer
        except Exception as e:
            log_warning(f"⚠️ Estimasi gas swap gagal: {str(e)}. Menggunakan nilai default.")
            return 280000  # Default dari ogbot.js

    def build_approval_tx(self, token_symbol, spender, amount, sender):
        """Buat transaksi approval token dengan nonce yang aman"""
        try:
            token_contract = self.get_token_contract(token_symbol)
        
            # Gunakan nonce yang aman
            nonce = self.get_safe_nonce(sender)
        
            gas_limit = self.estimate_gas_for_approval(token_contract, spender, amount, sender)
        
            tx = {
                "from": sender,
                "to": TOKEN_ADDRESSES[token_symbol],
                "gas": gas_limit,
                "nonce": nonce,
                "chainId": self.web3.eth.chain_id,
            }
        
            # Data untuk appprove
            tx["data"] = token_contract.encodeABI(
                fn_name="approve", 
                args=[spender, amount]
            )
        
            # Tambahkan parameter gas sesuai mode
            if isinstance(self.gas_price, dict):
                tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
            else:
                tx["gasPrice"] = self.gas_price
        
            log_debug(f"📝 Transaksi approval {token_symbol} dibuat dengan nonce {nonce}")
            return tx
        except Exception as e:
            log_error(f"❌ Error membuat transaksi approval: {str(e)}")
            return None

    def build_swap_tx(self, token_in, token_out, amount, sender):
        """Buat transaksi swap token dengan nonce yang aman"""
        try:
            # Gunakan nonce yang aman
            nonce = self.get_safe_nonce(sender)
        
            gas_limit = self.estimate_gas_for_swap(token_in, token_out, amount, sender)
            deadline = int(time.time()) + 300  # 5 menit
        
            # Parameter untuk exactInputSingle
            params = {
                'tokenIn': Web3.to_checksum_address(TOKEN_ADDRESSES[token_in]),
                'tokenOut': Web3.to_checksum_address(TOKEN_ADDRESSES[token_out]),
                'fee': 3000,
                'recipient': sender,
                'deadline': deadline,
                'amountIn': amount,
                'amountOutMinimum': 0,
                'sqrtPriceLimitX96': 0
            }
        
            tx = {
                "from": sender,
                "to": TOKEN_ADDRESSES["ROUTER"],
                "gas": gas_limit,
                "nonce": nonce,
                "chainId": self.web3.eth.chain_id,
            }
        
            # Data untuk exactInputSingle
            tx["data"] = self.router_contract.encodeABI(
                fn_name="exactInputSingle", 
                args=[params]
            )
        
            # Tambahkan parameter gas sesuai mode
            if isinstance(self.gas_price, dict):
                tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
            else:
                tx["gasPrice"] = self.gas_price
        
            decimals = self.token_decimals.get(token_in, 18)
            amount_readable = amount / (10 ** decimals)
            log_debug(f"📝 Transaksi swap {amount_readable:.6f} {token_in} ke {token_out} dibuat dengan nonce {nonce}")
            return tx
        except Exception as e:
            log_error(f"❌ Error membuat transaksi swap: {str(e)}")
            return None

    def handle_tx_error(self, error, tx):
        """Tangani error transaksi dan update tx jika diperlukan"""
        error_message = str(error).lower()
        
        if "insufficient funds" in error_message:
            log_error(f"💰 Error: Dana tidak cukup untuk gas * price + value")
            return None, False
            
        elif "nonce too low" in error_message:
            try:
                new_nonce = self.web3.eth.get_transaction_count(tx["from"], "pending")
                tx["nonce"] = new_nonce
                log_warning(f"🔄 Nonce diperbarui ke {new_nonce}")
                return tx, True
            except Exception as nonce_error:
                log_error(f"❌ Error memperbarui nonce: {str(nonce_error)}")
                return None, False
                
        elif any(msg in error_message for msg in ["fee too low", "underpriced"]):
            if isinstance(self.gas_price, dict):
                current_max_fee_gwei = self.web3.from_wei(self.gas_price["maxFeePerGas"], "gwei")
        
                # Batasi maksimum ke 30 Gwei
                new_max_fee = int(self.gas_price["maxFeePerGas"] * 1.3)  # Kenaikan 30%
                max_allowed = self.web3.to_wei(30, "gwei")
                if new_max_fee > max_allowed:
                    new_max_fee = max_allowed
                
                self.gas_price["maxFeePerGas"] = new_max_fee
                self.gas_price["maxPriorityFeePerGas"] = int(self.gas_price["maxPriorityFeePerGas"] * 1.3)
            
                tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
            
                new_max_fee_gwei = self.web3.from_wei(self.gas_price["maxFeePerGas"], "gwei")
                log_warning(f"⚠️ Fee transaksi terlalu rendah. Dinaikkan ke {new_max_fee_gwei:.6f} Gwei")
            else:
                current_gwei = self.web3.from_wei(self.gas_price, "gwei")
            
                # Batasi maksimum ke 30 Gwei
                new_gas_price = int(self.gas_price * 1.3)  # Kenaikan 30%
                max_allowed = self.web3.to_wei(30, "gwei")
                if new_gas_price > max_allowed:
                    new_gas_price = max_allowed
                
                self.gas_price = new_gas_price
                tx["gasPrice"] = self.gas_price
            
                new_gas_gwei = self.web3.from_wei(self.gas_price, "gwei")
                log_warning(f"⚠️ Fee transaksi terlalu rendah. Dinaikkan ke {new_gas_gwei:.6f} Gwei")
                
            return tx, True
            
        elif "mempool is full" in error_message:
            log_warning(f"⚠️ Mempool penuh. Mencoba beralih RPC...")
            if self.switch_rpc():
                return tx, True
            else:
                # Jika tidak bisa beralih RPC, tunggu lebih lama dan coba lagi dengan gas lebih tinggi
                sleep_seconds(CONFIG["COOLDOWN"]["ERROR"][1], "Menunggu mempool tidak penuh")
                if isinstance(self.gas_price, dict):
                    self.gas_price["maxFeePerGas"] = int(self.gas_price["maxFeePerGas"] * 2)
                    self.gas_price["maxPriorityFeePerGas"] = int(self.gas_price["maxPriorityFeePerGas"] * 2)
                    tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                    tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
                else:
                    self.gas_price = int(self.gas_price * 2)
                    tx["gasPrice"] = self.gas_price
                return tx, True
                
        else:
            if isinstance(self.gas_price, dict):
                # Tentukan batas maksimum gas untuk EIP-1559
                max_fee_gwei = self.web3.from_wei(self.gas_price["maxFeePerGas"], "gwei")
                if max_fee_gwei < 10:  # Jika masih di bawah 10 Gwei
                    increase_factor = 1.3  # Kenaikan 30%
                elif max_fee_gwei < 20:  # Jika antara 10-20 Gwei
                    increase_factor = 1.2  # Kenaikan 20%
                else:  # Jika sudah di atas 20 Gwei
                    increase_factor = 1.1  # Kenaikan hanya 10%
            
                # Batasi maksimum gas ke 30 Gwei
                new_max_fee = int(self.gas_price["maxFeePerGas"] * increase_factor)
                max_allowed = self.web3.to_wei(30, "gwei")
                if new_max_fee > max_allowed:
                    new_max_fee = max_allowed
            
                self.gas_price["maxFeePerGas"] = new_max_fee
                self.gas_price["maxPriorityFeePerGas"] = int(self.gas_price["maxPriorityFeePerGas"] * increase_factor)
            
                tx["maxFeePerGas"] = self.gas_price["maxFeePerGas"]
                tx["maxPriorityFeePerGas"] = self.gas_price["maxPriorityFeePerGas"]
            
                new_max_fee_gwei = self.web3.from_wei(self.gas_price["maxFeePerGas"], "gwei")
                log_warning(f"⚠️ Error tidak dikenal. Meningkatkan gas: {new_max_fee_gwei:.6f} Gwei")
            else:
                # Untuk legacy gas price
                current_gwei = self.web3.from_wei(self.gas_price, "gwei")
                if current_gwei < 10:  # Jika masih di bawah 10 Gwei
                    increase_factor = 1.3  # Kenaikan 30%
                elif current_gwei < 20:  # Jika antara 10-20 Gwei
                    increase_factor = 1.2  # Kenaikan 20%
                else:  # Jika sudah di atas 20 Gwei
                    increase_factor = 1.1  # Kenaikan hanya 10%
            
                # Batasi maksimum gas ke 30 Gwei
                new_gas_price = int(self.gas_price * increase_factor)
                max_allowed = self.web3.to_wei(30, "gwei")
                if new_gas_price > max_allowed:
                    new_gas_price = max_allowed
                
                self.gas_price = new_gas_price
                tx["gasPrice"] = self.gas_price
            
                new_gas_gwei = self.web3.from_wei(self.gas_price, "gwei")
                log_warning(f"⚠️ Error tidak dikenal. Meningkatkan gas: {new_gas_gwei:.6f} Gwei")
                
            return tx, True
    
    def wait_for_transaction_completion(self, tx_hash, timeout=210):
        """Menunggu transaksi selesai sebelum melanjutkan untuk menghindari konflik nonce"""
        log_info(f"⏳ Menunggu transaksi {tx_hash} dikonfirmasi...")
        start_time = time.time()
    
        while time.time() - start_time < timeout:
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    if receipt.status == 1:
                        log_success(f"✅ Transaksi dikonfirmasi: blok #{receipt.blockNumber}")
                        return receipt
                    else:
                        log_error(f"❌ Transaksi gagal di blockchain.")
                        return receipt
            except Exception as e:
                if "not found" not in str(e).lower():
                    log_warning(f"⚠️ Error checking receipt: {str(e)}")
        
            # Tunggu 3 detik sebelum cek lagi
            time.sleep(3)
    
        log_warning(f"⏱️ Timeout menunggu transaksi {tx_hash}.")
        return None
    
    def get_safe_nonce(self, address):
        """Dapatkan nonce yang aman, dengan memastikan tidak ada transaksi pending"""
        try:
            # Coba dapatkan nonce dari transaksi pending
            pending_nonce = self.web3.eth.get_transaction_count(address, "pending")
            # Dapatkan nonce dari transaksi yang sudah dikonfirmasi
            latest_nonce = self.web3.eth.get_transaction_count(address, "latest")
        
            if pending_nonce > latest_nonce:
                log_debug(f"🔄 Menunggu transaksi pending selesai... (pending nonce: {pending_nonce}, latest nonce: {latest_nonce})")
                # Tunggu beberapa saat untuk transaksi pending selesai
                time.sleep(5)
                return self.get_safe_nonce(address)  # Rekursif, coba lagi
        
            log_debug(f"🔢 Menggunakan nonce: {latest_nonce}")
            return latest_nonce
        except Exception as e:
            log_warning(f"⚠️ Error mendapatkan nonce: {str(e)}")
            # Fallback ke nonce latest yang biasa
            return self.web3.eth.get_transaction_count(address, "latest")
    
    def send_transaction(self, tx, private_key, tx_type=""):
        """Kirim transaksi yang sudah ditandatangani dan tunggu sampai selesai"""
        retries = CONFIG["MAX_RETRIES"]
    
        # Pastikan gas price tidak nol
        if "gasPrice" in tx and tx["gasPrice"] <= 0:
            log_warning("⚠️ Gas price nol terdeteksi, memperbaiki...")
            tx["gasPrice"] = self.web3.to_wei(1.5, "gwei")
        elif "maxFeePerGas" in tx and tx["maxFeePerGas"] <= 0:
            log_warning("⚠️ maxFeePerGas nol terdeteksi, memperbaiki...")
            tx["maxFeePerGas"] = self.web3.to_wei(1.5, "gwei")
            tx["maxPriorityFeePerGas"] = self.web3.to_wei(0.5, "gwei")
    
        consecutive_failures = 0

        while retries > 0:
            try:
                wallet = self.web3.eth.account.from_key(private_key)
                signed = self.web3.eth.account.sign_transaction(tx, private_key)
                receipt = self.web3.eth.send_raw_transaction(signed.rawTransaction)
                tx_hash = receipt.hex()
            
                consecutive_failures = 0

                self.tx_counter += 1
                log_success(f"✅ Transaksi {tx_type} dikirim! TxID #{self.tx_counter}: {tx_hash}")
            
                # Tunggu transaksi selesai sebelum melanjutkan
                tx_receipt = self.wait_for_transaction_completion(tx_hash)
            
                if tx_receipt:
                    if tx_receipt.status == 1:
                        log_success(f"✅ Transaksi berhasil dikonfirmasi!")
                        return tx_receipt
                    else:
                        log_error(f"❌ Transaksi gagal di blockchain! Cek explorer untuk detail.")
                        return None
                else:
                    log_warning(f"⏱️ Timeout menunggu konfirmasi, tetapi transaksi mungkin berhasil. TxID: {tx_hash}")
                    return {'transactionHash': tx_hash}  # Return dict with hash
                    
            except Exception as e:
                # Increment failure counter
                consecutive_failures += 1
            
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
                
                log_warning(f"⚠️ Gas price di-reset setelah beberapa kali gagal berturut-turut")
                
                updated_tx, should_retry = self.handle_tx_error(e, tx)
                if not should_retry:
                    retries = 0
                    log_error(f"❌ Transaksi tidak dapat dikirim: {str(e)}")
                    return None
            
                tx = updated_tx
                retries -= 1
                log_warning(f"⚠️ Error mengirim transaksi. Sisa percobaan: {retries}.")
            
                if retries > 0:
                    # Random delay before retry
                    delay = random.randint(CONFIG["COOLDOWN"]["ERROR"][0], CONFIG["COOLDOWN"]["ERROR"][1])
                    sleep_seconds(delay, "Menunggu sebelum retry")
    
        return None
    
    def swap_token_to_token(self, private_key, token_in, token_out, wallet_num=0, total_wallets=1):
        """Lakukan swap dari satu token ke token lain dengan penanganan nonce yang aman"""
        try:
            wallet = self.web3.eth.account.from_key(private_key)
            address = wallet.address
        
            # Random amount berdasarkan jenis token
            decimals = self.token_decimals.get(token_in, 18)
        
            if token_in == "USDT":
                random_amount = round(random.uniform(CONFIG["SWAP_AMOUNT_USDT"][0], CONFIG["SWAP_AMOUNT_USDT"][1]), 2)
            elif token_in == "ETH":
                random_amount = round(random.uniform(CONFIG["SWAP_AMOUNT_ETH"][0], CONFIG["SWAP_AMOUNT_ETH"][1]), 6)
            elif token_in == "BTC":
                random_amount = round(random.uniform(CONFIG["SWAP_AMOUNT_BTC"][0], CONFIG["SWAP_AMOUNT_BTC"][1]), 6)
            else:
                random_amount = round(random.uniform(0.01, 0.02), 0.03)
            
            amount_in_wei = int(random_amount * (10 ** decimals))
        
            log_debug(f"🔄 Memulai swap {random_amount} {token_in} ke {token_out}", wallet_num, total_wallets)
        
            # Cek saldo sebelum transaksi
            self.check_wallet_balance(address, token_in)
        
            # 1. Approval token
            router_address = TOKEN_ADDRESSES["ROUTER"]
            approval_tx = self.build_approval_tx(token_in, router_address, amount_in_wei, address)
        
            if not approval_tx:
                log_error(f"❌ Gagal membangun transaksi approval.")
                return False
            
            approval_receipt = self.send_transaction(approval_tx, private_key, f"Approval {token_in}")
        
            if not approval_receipt:
                log_error(f"❌ Approval {token_in} gagal.")
                return False
            
            log_success(f"✅ Approval {token_in} berhasil!")
        
            # Pastikan approval sudah benar-benar selesai sebelum melanjutkan
            if 'transactionHash' in approval_receipt:
                # Jika kita mengembalikan hanya hash, tunggu sampai benar-benar selesai
                tx_hash = approval_receipt['transactionHash']
                if isinstance(tx_hash, bytes):
                    tx_hash = tx_hash.hex()
                full_receipt = self.wait_for_transaction_completion(tx_hash)
                if not full_receipt or full_receipt.status != 1:
                    log_error(f"❌ Approval {token_in} gagal pada konfirmasi.")
                    return False
        
            # Delay antara approval dan swap (opsional, tapi baik untuk mencegah nonce conflict)
            sleep_seconds(random.randint(5, 15), "Memastikan konfirmasi approval")
        
            # 2. Swap token
            swap_tx = self.build_swap_tx(token_in, token_out, amount_in_wei, address)
        
            if not swap_tx:
                log_error(f"❌ Gagal membangun transaksi swap.")
                return False
            
            swap_receipt = self.send_transaction(swap_tx, private_key, f"Swap {token_in}->{token_out}")
        
            if not swap_receipt:
                log_error(f"❌ Swap {token_in} ke {token_out} gagal.")
                return False
            
            log_success(f"✅ Swap {random_amount} {token_in} ke {token_out} berhasil!")
        
            # Cek saldo setelah transaksi
            sleep_seconds(3, "Memperbarui saldo")
            self.check_wallet_balance(address, token_out)
        
            # Delay berhasil
            delay = random.randint(CONFIG["COOLDOWN"]["SUCCESS"][0], CONFIG["COOLDOWN"]["SUCCESS"][1])
            sleep_seconds(delay, "Cooldown setelah transaksi berhasil")
        
            return True
        
        except Exception as e:
            log_error(f"❌ Error dalam proses swap: {str(e)}")
            return False

    def process_swaps(self, account, wallet_num, total_wallets, is_last_wallet=False):
        """Proses beberapa swap untuk satu wallet"""
        private_key = account["key"]
        address = account["address"]
        
        log_info(f"🔄 Menggunakan wallet {wallet_num}/{total_wallets}: {short_address(address)}")
        
        # Jumlah transaksi acak per wallet
        tx_count = random.randint(CONFIG["TRANSACTIONS_PER_WALLET"][0], CONFIG["TRANSACTIONS_PER_WALLET"][1])
        log_info(f"📊 Merencanakan {tx_count} transaksi untuk wallet ini")
        
        # Cek saldo awal
        initial_balance = self.check_wallet_balance(address)
        
        # Transaksi yang akan dilakukan
        success_count = 0
        
        for i in range(tx_count):
            log_info(f"🔄 Transaksi {i+1}/{tx_count} untuk wallet {wallet_num}")
            
            # Variasi transaksi swap yang mungkin dilakukan
            swap_types = [
                ("USDT", "ETH"),   # USDT -> ETH
                ("ETH", "USDT"),   # ETH -> USDT
                ("USDT", "BTC"),   # USDT -> BTC
                ("BTC", "USDT"),   # BTC -> USDT
            ]
            
            # Pilih jenis swap secara acak
            swap_in, swap_out = random.choice(swap_types)
            
            # Eksekusi swap
            success = self.swap_token_to_token(private_key, swap_in, swap_out, wallet_num, total_wallets)
            
            if success:
                success_count += 1
            else:
                log_warning(f"⚠️ Transaksi {i+1} gagal, lanjut ke transaksi berikutnya")
            
            # Delay antara transaksi dalam wallet yang sama (jika masih ada transaksi berikutnya)
            if i < tx_count - 1:
                delay = random.randint(30, 120)
                sleep_seconds(delay, "Menunggu untuk transaksi berikutnya")
        
        # Cek saldo akhir
        sleep_seconds(3, "Memperbarui saldo")
        final_balance = self.check_wallet_balance(address)
        
        # Hitung biaya gas yang digunakan
        gas_used = initial_balance - final_balance
        gas_cost_eth = self.web3.from_wei(gas_used, "ether")
        chain_id = self.web3.eth.chain_id
        token_symbol = CHAIN_SYMBOLS.get(chain_id, "A0GI")
        
        log_info(f"💰 Ringkasan wallet {wallet_num}: {success_count}/{tx_count} transaksi berhasil")
        log_info(f"⛽ Biaya gas total: {gas_cost_eth:.8f} {token_symbol}")
        
        # Jika ini adalah wallet terakhir, terapkan delay panjang
        if is_last_wallet:
            delay_seconds = random.randint(
                CONFIG["CYCLE_COMPLETE_DELAY"][0], 
                CONFIG["CYCLE_COMPLETE_DELAY"][1]
            )
            log_success(f"🔄 Semua wallet telah diproses! Siklus {self.cycle_count} selesai.")
            log_info(f"⏳ Menunggu {delay_seconds//60} menit untuk siklus berikutnya...")
            sleep_seconds(delay_seconds, f"Menunggu siklus berikutnya ({self.cycle_count + 1})")
            self.cycle_count += 1
        else:
            # Delay pendek antar wallet
            delay_seconds = random.randint(
                CONFIG["WALLET_SWITCH_DELAY"][0], 
                CONFIG["WALLET_SWITCH_DELAY"][1]
            )
            sleep_seconds(delay_seconds, "Beralih ke wallet berikutnya")
        
        return success_count > 0

    def execute_cycle(self):
        """Eksekusi satu siklus swap untuk semua wallet"""
        log_success(f"🔄 Memulai siklus swap #{self.cycle_count} dengan {len(self.accounts)} wallet")
        
        self.update_gas_price()
        
        for idx, account in enumerate(self.accounts):
            wallet_num = idx + 1
            is_last_wallet = idx == len(self.accounts) - 1
            
            success = self.process_swaps(account, wallet_num, len(self.accounts), is_last_wallet)
            if not success:
                log_warning(f"⚠️ Semua transaksi pada wallet {wallet_num} gagal. Lanjut ke wallet berikutnya.")
        
        log_success(f"✅ Siklus #{self.cycle_count} selesai untuk semua wallet")
        return True

# ======================== Main Function ========================
def main():
    try:
        print_banner()
        
        swapper = OGSwapper()
        swapper.initialize()
        
        try:
            while True:
                swapper.execute_cycle()
        except KeyboardInterrupt:
            log_warning("\n⚠️ Program dihentikan oleh pengguna. Keluar...")
            return
            
    except Exception as e:
        log_error(f"❌ Error dalam program: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
    
