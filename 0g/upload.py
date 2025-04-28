import requests
import json
import os
import time
import random
import re
import signal
import threading
from datetime import datetime, timedelta
import logging
from web3 import Web3
import math
import shutil
from apscheduler.schedulers.blocking import BlockingScheduler
import traceback
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)
load_dotenv()

LOG_FILE = "og_uploader.log"
MAX_LOG_SIZE = 4 * 1024 * 1024
MAX_LOG_FILES = 3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def rotate_logs():
    """Rotate log files to prevent excessive disk usage"""
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
            for i in range(MAX_LOG_FILES - 1, 0, -1):
                src = f"{LOG_FILE}.{i}" if i > 0 else LOG_FILE
                dst = f"{LOG_FILE}.{i+1}"
                if os.path.exists(src):
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.move(src, dst)
            
            open(LOG_FILE, 'w').close()
            logger.info("Log file rotated")
    except Exception as e:
        print(f"Error rotating logs: {e}")

def clean_old_data_files(days=1):
    """Clean data files older than specified days"""
    try:
        data_dir = os.getenv("DATA_DIR", "data_files")
        if not os.path.exists(data_dir):
            return
            
        cutoff_date = datetime.now() - timedelta(days=days)
        
        count = 0
        for filename in os.listdir(data_dir):
            filepath = os.path.join(data_dir, filename)
            if os.path.isfile(filepath):
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_time < cutoff_date:
                    os.remove(filepath)
                    count += 1
        
        if count > 0:
            logger.info(f"Cleaned {count} old data files (older than {days} days)")
    except Exception as e:
        logger.error(f"Error cleaning old data files: {e}")

def load_private_keys():
    """Load private keys from environment variable and file"""
    private_keys = []

    env_private_key = os.getenv("PRIVATE_KEY")
    if env_private_key and env_private_key.strip():
        private_keys.append(env_private_key.strip())

    try:
        with open("private_keys.txt", "r") as file:
            keys = [line.strip() for line in file.readlines() if line.strip()]
            private_keys.extend(keys)
    except Exception as e:
        print(f"{Fore.YELLOW}Note: private_keys.txt not found or couldn't be read: {e}{Style.RESET_ALL}")

    if not private_keys:
        raise Exception("No private keys found in .env or private_keys.txt")

    private_keys = [k if k.startswith("0x") else "0x" + k for k in private_keys]
    
    print(f"📸 Loaded {len(private_keys)} wallet(s) {Fore.GREEN}successfully{Style.RESET_ALL}")

    return list(set(private_keys))

def load_rpc_urls():
    """Load RPC URLs from environment variable"""
    rpc_urls_str = os.getenv("RPC_URLS")
    if not rpc_urls_str:
        return [
            "https://evmrpc-testnet.0g.ai",
            "https://rpc.ankr.com/0g_newton"
        ]
    
    urls = [url.strip() for url in rpc_urls_str.split(",") if url.strip()]
    return urls

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    """Handler for signal timeout"""
    raise TimeoutError("Function execution timed out")   

class OGDataUploader:
    def __init__(self):
        self.config = {
            "chain_id": int(os.getenv("CHAIN_ID", "80087")),
            "chain_id_hex": hex(int(os.getenv("CHAIN_ID", "80087"))),
            "network_name": os.getenv("NETWORK_NAME", "0G Chain Testnet"),
            "symbol": os.getenv("SYMBOL", "0G"),
            "decimals": int(os.getenv("DECIMALS", "18")),
            "proxy_address": os.getenv("PROXY_CONTRACT_ADDRESS", "0x56A565685C9992BF5ACafb940ff68922980DBBC5"),
            "max_file_size_kb": int(os.getenv("MAX_FILE_SIZE_KB", "300")),
            "data_dir": os.getenv("DATA_DIR", "data_files"),
            "coingecko_api_key": os.getenv("COINGECKO_API_KEY", ""),
            "network": os.getenv("NETWORK", "turbo")
        }

        os.makedirs(self.config["data_dir"], exist_ok=True)
        
        self.private_keys = load_private_keys()
        self.rpc_urls = load_rpc_urls()
        
        self.current_key_index = 0
        
        self.setup_web3_provider()
        
        self.load_contract_abi()

        self.setup_transaction_monitoring()
        
        self.ENTRY_SIZE = 256
        self.MAX_DEPTH = 64
        self.MAX_LENGTH = 4

        self.state = {
            'pending_chunks': [],
            'last_transaction': None,
            'error_counts': {}
        }
        self.state_file = "og_uploader_state.json"
        self.load_state()

    def load_state(self):
        """Load state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                logger.info(f"Loaded state from {self.state_file}")
            else:
                logger.info("No state file found, using default state")
                self.state = {
                    'pending_chunks': [],
                    'last_transaction': None,
                    'error_counts': {}
                }
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            self.state = {
                'pending_chunks': [],
                'last_transaction': None,
                'error_counts': {}
            }

    def save_state(self):
        """Save state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"Saved state to {self.state_file}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
        
        print(f"{Fore.GREEN}✓ OG Data Uploader initialized successfully{Style.RESET_ALL}")
    
    def get_current_private_key(self):
        """Get current private key"""
        return self.private_keys[self.current_key_index]
    
    def rotate_private_key(self):
        """Rotate to next private key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.private_keys)
        logger.info(f"Rotated to the next wallet (index {self.current_key_index})")
        
        self.account = self.w3.eth.account.from_key(self.get_current_private_key())
        logger.info(f"Using wallet: {self.account.address}")
        
        return self.account
    
    def setup_web3_provider(self):
        """Initialize Web3 with failover between multiple RPC providers"""
        random.shuffle(self.rpc_urls)
        
        for rpc_url in self.rpc_urls:
            try:
                logger.info(f"Trying to connect to RPC at {rpc_url}")
                provider = Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 30})
                w3 = Web3(provider)
                
                if w3.is_connected() and w3.eth.chain_id == self.config["chain_id"]:
                    self.w3 = w3
                    self.current_rpc = rpc_url
                    self.account = self.w3.eth.account.from_key(self.get_current_private_key())
                    logger.info(f"Successfully connected to {rpc_url}")
                    logger.info(f"Using wallet: {self.account.address}")
                    return
                else:
                    logger.warning(f"Connected to {rpc_url} but it returned wrong chain ID or status")
            except Exception as e:
                logger.warning(f"Failed to connect to {rpc_url}: {str(e)}")
        
        raise ConnectionError("Failed to connect to any RPC endpoint. Please check your internet connection or RPC availability.")
    
    def retry_with_new_rpc(self):
        """Switch to a different RPC if current one fails"""
        logger.warning(f"Current RPC {self.current_rpc} failed, trying another one...")
        
        remaining_rpcs = [url for url in self.rpc_urls if url != self.current_rpc]
        random.shuffle(remaining_rpcs)
        
        for rpc_url in remaining_rpcs:
            try:
                logger.info(f"Trying to connect to RPC at {rpc_url}")
                provider = Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 30})
                w3 = Web3(provider)
                
                if w3.is_connected() and w3.eth.chain_id == self.config["chain_id"]:
                    self.w3 = w3
                    self.current_rpc = rpc_url
                    self.contract = self.w3.eth.contract(address=self.config["proxy_address"], abi=self.contract_abi)
                    logger.info(f"Successfully switched to {rpc_url}")
                    return True
            except Exception as e:
                logger.warning(f"Failed to connect to {rpc_url}: {str(e)}")
        
        logger.error("Failed to connect to any alternate RPC endpoint")
        return False
    
    def load_contract_abi(self):
        """Load contract ABI from file or use hardcoded ABI"""
        try:
            if os.path.exists('contract_abi.json'):
                with open('contract_abi.json', 'r') as f:
                    self.contract_abi = json.load(f)
                    logger.info("Loaded contract ABI from file")
            else:
                self.contract_abi = json.loads('[{"inputs":[{"components":[{"internalType":"uint256","name":"length","type":"uint256"},{"internalType":"bytes","name":"tags","type":"bytes"},{"components":[{"internalType":"bytes32","name":"root","type":"bytes32"},{"internalType":"uint256","name":"height","type":"uint256"}],"internalType":"struct SubmissionNode[]","name":"nodes","type":"tuple[]"}],"internalType":"struct Submission","name":"submission","type":"tuple"}],"name":"submit","outputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bytes32","name":"","type":"bytes32"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"payable","type":"function"}]')
                logger.info("Using hardcoded ABI (limited functionality)")
                
                with open('contract_abi.json', 'w') as f:
                    json.dump(self.contract_abi, f)
            
            self.contract = self.w3.eth.contract(address=self.config["proxy_address"], abi=self.contract_abi)
            
        except Exception as e:
            logger.error(f"Error loading contract ABI: {str(e)}")
            raise
    
    def verify_wallet_connection(self):
        """Verify wallet connection similar to main.js verifyWalletConnection"""
        try:
            network = self.w3.eth.chain_id
            print(f"\n{Fore.CYAN}=== Wallet Connection Status ==={Style.RESET_ALL}")
            print(f"Network: {self.config['network_name']}")
            print(f"Chain ID: {network} ({self.config['chain_id_hex']})")

            balance = self.w3.eth.get_balance(self.account.address)
            print(f"Address: {self.account.address}")
            print(f"Balance: {Web3.from_wei(balance, 'ether')} {self.config['symbol']}")
            
            block = self.w3.eth.block_number
            print(f"Latest Block: {block}")
            print(f"\n{Fore.GREEN}✓ Wallet connected successfully{Style.RESET_ALL}\n")
            
            return True
        except Exception as e:
            print(f"\n{Fore.RED}❌ Wallet Connection Failed{Style.RESET_ALL}")
            print(f"Error: {str(e)}")
            return False

    def get_min_unit_price(self):
        """Get global minimum unit price from contract if available"""
        try:
            if hasattr(self.contract.functions, 'getMinimumStoragePrice'):
                min_price_wei = self.contract.functions.getMinimumStoragePrice().call()
                min_price = self.w3.from_wei(min_price_wei, 'ether')
                return min_price
            return None
        except Exception as e:
            logger.warning(f"Could not get minimum unit price from contract: {e}")
            return None

    def calculate_storage_fee(self, file_size_bytes):
        """Calculate storage fee based on 0G Network specifications"""
        try:
            SECTOR_SIZE = 256
            num_sectors = math.ceil(file_size_bytes / SECTOR_SIZE)
        
            global_min_price = self.get_min_unit_price()
        
            if global_min_price:
                logger.info(f"Using global minimum unit price: {global_min_price} 0G per sector")
                min_price_per_sector = global_min_price
            else:
                min_price_per_sector = 0.00002
                logger.info(f"Using estimated min price: {min_price_per_sector} 0G per sector")
        
            premium_factor = 1.1
        
            storage_endowment = min_price_per_sector * num_sectors * premium_factor
        
            min_total_endowment = 0.00005
            storage_endowment = max(min_total_endowment, storage_endowment)
        
            storage_endowment_wei = self.w3.to_wei(storage_endowment, 'ether')
        
            logger.info(f"Storage fee calculation:")
            logger.info(f"  File size: {file_size_bytes} bytes")
            logger.info(f"  Number of 256B sectors: {num_sectors}")
            logger.info(f"  Min price per sector: {min_price_per_sector} 0G")
            logger.info(f"  Premium factor: {premium_factor} (for better data availability)")
            logger.info(f"  Total storage endowment: {storage_endowment:.8f} 0G")
            logger.info(f"  Unit price: {storage_endowment/num_sectors:.8f} 0G per sector")
        
            return storage_endowment_wei
        except Exception as e:
            logger.error(f"Error calculating storage fee: {e}")
            default_fee = self.w3.to_wei(0.00002, 'ether')
            logger.info(f"Using default storage fee: 0.00002 0G")
            return default_fee

    def validate_contract_submission(self, submission):
        """Validasi struktur data sesuai dengan ekspektasi kontrak"""
        if not isinstance(submission["length"], int):
            logger.info(f"Converting length from {type(submission['length'])} to int")
            submission["length"] = int(submission["length"])
    
        for i, node in enumerate(submission["nodes"]):
            if not isinstance(node["root"], bytes) or len(node["root"]) != 32:
                logger.error(f"Node {i}: root harus berupa bytes32, bukan {type(node['root'])}")
                return False
        
            if not isinstance(node["height"], int):
                logger.info(f"Converting node height from {type(node['height'])} to int")
                node["height"] = int(node["height"])
    
        if isinstance(submission["tags"], str) and submission["tags"].startswith("0x"):
            logger.info(f"Tags in hex string format: {submission['tags']}")
        elif not isinstance(submission["tags"], bytes):
            logger.warning(f"Tags harus bytes atau hex string, bukan {type(submission['tags'])}")
            try:
                if isinstance(submission["tags"], str):
                    submission["tags"] = "0x" + submission["tags"].encode().hex()
                else:
                    submission["tags"] = "0x" + bytes(submission["tags"]).hex() if submission["tags"] else "0x"
                logger.info(f"Converted tags to hex string: {submission['tags']}")
            except:
                logger.error(f"Failed to convert tags to hex string, using empty hex")
                submission["tags"] = "0x"
    
        if "file_path" in submission:
            del submission["file_path"]
        if "network" in submission:
            del submission["network"]
    
        logger.info(f"Final submission structure validated: length={submission['length']}, tags={submission['tags']}, nodes_count={len(submission['nodes'])}")
        return True
    
    def decode_contract_error(self, error_str):
        """Decode error message dari smart contract revert dengan lebih detail"""
        revert_patterns = [
            r"execution reverted: (.*?)($|,)",
            r"Error: VM Exception.*?: revert (.*?)($|,)",
            r"transact to.*?error: (.*?)($|,)",
            r"Error: (.*?)($|,)"
        ]
    
        for pattern in revert_patterns:
            match = re.search(pattern, error_str)
            if match:
                error_message = match.group(1)
                logger.error(f"Smart Contract Error: {error_message}")
            
                if "Invalid merkle root" in error_message:
                    return "INVALID_MERKLE_ROOT"
                elif "Exceeded max depth" in error_message:
                    return "EXCEEDED_MAX_DEPTH"
                elif "Invalid tags" in error_message:
                    return "INVALID_TAGS"
                elif "mempool is full" in error_message:
                    return "MEMPOOL_FULL"
                elif "gas too low" in error_message or "out of gas" in error_message:
                    return "OUT_OF_GAS"
                elif "reverted" in error_message:
                    return "CONTRACT_REVERTED"
                else:
                    return "CONTRACT_ERROR"
                
        if "transaction underpriced" in error_str.lower():
            return "UNDERPRICED"
        elif "nonce too low" in error_str.lower():
            return "NONCE_TOO_LOW"
        elif "insufficient funds" in error_str.lower():
            return "INSUFFICIENT_FUNDS"
        elif "already known" in error_str.lower():
            return "TX_ALREADY_KNOWN"
        elif "cannot estimate gas" in error_str.lower() or "gas required exceeds allowance" in error_str.lower():
            return "GAS_ESTIMATION_FAILED"
    
        return "UNKNOWN_ERROR"

    def calculate_correct_merkle_height(self, num_leaves):
        """Calculate correct Merkle tree height based on contract requirements"""
        if num_leaves <= 1:
            return 0
        
        calculated_height = math.ceil(math.log2(num_leaves))
        
        current_level = num_leaves
        height = 0
        while current_level > 1:
            current_level = (current_level + 1) // 2
            height += 1
        
        if height != calculated_height:
            logger.warning(f"Height mismatch: calculated={calculated_height}, actual={height}")
        
        max_height = self.MAX_DEPTH - 1
        if height > max_height:
            logger.warning(f"Height {height} exceeds max {max_height}, truncating")
            height = max_height
        
        return height
    
    def implement_data_chunking_strategy(self, file_path):
        """Implement improved strategy for handling large files"""
        file_size = os.path.getsize(file_path)
        
        DIRECT_UPLOAD_LIMIT = 5 * 1024
        CHUNKED_UPLOAD_LIMIT = 50 * 1024
        
        if file_size <= DIRECT_UPLOAD_LIMIT:
            logger.info(f"Small file ({file_size} bytes), using direct upload")
            return self.prepare_submission(file_path)
        
        elif file_size <= CHUNKED_UPLOAD_LIMIT:
            logger.info(f"Medium file ({file_size} bytes), using optimized merkle tree")
            return self.prepare_submission(file_path)
        
        else:
            logger.info(f"Large file ({file_size} bytes), splitting into chunks")
            chunks = self.split_file_into_chunks(file_path)
            logger.info(f"Split into {len(chunks)} chunks")
            
            first_chunk = chunks[0]
            self.state['pending_chunks'] = chunks[1:]
            self.save_state()
            
            return self.prepare_submission(first_chunk)

    def build_merkle_tree(self, leaf_hashes):
        """Bangun Merkle tree dari daftar hash daun dan kembalikan hanya root node untuk file kecil"""
        if not leaf_hashes:
            return []
    
        current_level = leaf_hashes
        height = 0
    
        while len(current_level) > 1:
            next_level = []
            height += 1
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                parent_hash = self.w3.keccak(combined)
                next_level.append(parent_hash)
            current_level = next_level
    
        # Untuk file kecil, kembalikan hanya root node dengan height=0
        return [{"root": current_level[0], "height": 0}]

    def prepare_submission(self, file_path, network="turbo"):
        """Persiapkan submission berdasarkan ukuran file"""
        try:
            logger.info(f"{Fore.YELLOW} Step 1: Upload File Prepared{Fore.RESET} data is {Fore.MAGENTA}{file_path} {Fore.RESET}")

            with open(file_path, 'rb') as f:
                data_bytes = f.read()
    
            file_size = len(data_bytes)
            file_size_kb = file_size / 1024
            logger.info(f"File Size: {file_size_kb:.2f} KB")
    
            SECTOR_SIZE = 256  # DEFAULT_CHUNK_SIZE
            SEGMENT_SIZE = 256 * 1024  # DEFAULT_SEGMENT_SIZE (256 KB)
        
            # Hitung jumlah chunk dan segmen
            num_chunks = (file_size + SECTOR_SIZE - 1) // SECTOR_SIZE  # Ceiling division
            num_segments = (file_size + SEGMENT_SIZE - 1) // SEGMENT_SIZE  # Ceiling division
        
            if file_size <= SECTOR_SIZE:
                # Direct upload untuk file kecil
                root_hash = self.w3.keccak(data_bytes)
                submission_nodes = [{"root": root_hash, "height": 0}]
            else:
                # File besar, bangun Merkle tree
                sectors = [data_bytes[i:i + SECTOR_SIZE] for i in range(0, file_size, SECTOR_SIZE)]
                leaf_hashes = [self.w3.keccak(sector) for sector in sectors]
                submission_nodes = self.build_merkle_tree(leaf_hashes)
                if not submission_nodes:
                    logger.error("Failed to build Merkle tree")
                    return None
    
            # Gunakan jumlah segmen sebagai length (default)
            length = num_segments
            logger.info(f"Setting length to {length} (segments), num_chunks={num_chunks}, num_bytes={file_size}")
    
            tags = "0x"
    
            root_hash_hex = submission_nodes[-1]["root"].hex() if submission_nodes else ""
            logger.info(f"Root Hash is: {root_hash_hex}")
    
            submission = {
                "length": length,
                "tags": tags,
                "nodes": submission_nodes,
                "file_path": file_path,
                "network": network,
                "root_hash": root_hash_hex,
                "file_size_kb": file_size_kb,
                "num_chunks": num_chunks,  # Simpan untuk retry
                "num_bytes": file_size  # Simpan untuk retry
            }
            logger.info(f"{Fore.MAGENTA} ✓ Upload successfully prepared {Fore.RESET}")
    
            logger.info(f"Submission details: length={submission['length']} segments, tags={submission['tags']}")
            logger.info(f"Node details: nodes_count={len(submission['nodes'])}, root-hash {submission['root_hash']}")
    
            if self.validate_submission_against_contract(submission) and self.validate_merkle_tree_structure(submission):
                logger.info("Submission successfully validated against contract requirements")
                return submission
            else:
                logger.error("Could not create valid submission after adjustments")
                return None
    
        except Exception as e:
            logger.error(f"✗ Error preparing file upload: {str(e)}")
            logger.debug(traceback.format_exc())
            return None

    def split_file_into_chunks(self, file_path):
        """Split large file into smaller chunks for more reliable uploads"""
        CHUNK_SIZE = 5 * 1024
        
        chunks_dir = os.path.join(self.config["data_dir"], "chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        
        base_name = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        chunk_files = []
        for i in range(0, len(data), CHUNK_SIZE):
            chunk_data = data[i:i+CHUNK_SIZE]
            chunk_file = os.path.join(chunks_dir, f"{base_name}.chunk{i//CHUNK_SIZE}.{timestamp}")
            
            with open(chunk_file, 'wb') as f:
                f.write(chunk_data)
            
            chunk_files.append(chunk_file)
        
        return chunk_files

    def get_optimal_nonce_strategy(self, address):
        """Implement more sophisticated nonce management"""
        max_attempts = 3
    
        for attempt in range(max_attempts):
            try:
                latest_nonce = self.w3.eth.get_transaction_count(address, 'latest')
                pending_nonce = self.w3.eth.get_transaction_count(address, 'pending')
            
                nonce_gap = pending_nonce - latest_nonce
            
                if nonce_gap > 5:
                    logger.warning(f"Large nonce gap detected: {nonce_gap} pending transactions")
                    if attempt == 0 and nonce_gap > 10:
                        logger.warning("Unusually large nonce gap. Trying to refresh connection...")
                        if self.retry_with_new_rpc():
                            logger.info("Connection refreshed, rechecking nonce")
                            continue
                    logger.info(f"Using conservative nonce approach: {latest_nonce}")
                    return latest_nonce
            
                logger.info(f"Using nonce {pending_nonce} (latest: {latest_nonce}, pending: {nonce_gap})")
                return pending_nonce
        
            except Exception as e:
                logger.error(f"Error determining nonce (attempt {attempt+1}/{max_attempts}): {e}")
            
                if attempt < max_attempts - 1:
                    if self.retry_with_new_rpc():
                        logger.info("Switched RPC, retrying nonce determination")
                        time.sleep(5)
                    else:
                        logger.warning("Could not switch RPC, retrying nonce determination anyway")
                        time.sleep(8)
                else:
                    try:
                        safe_nonce = self.w3.eth.get_transaction_count(address)
                        logger.info(f"Using safe fallback nonce: {safe_nonce}")
                        return safe_nonce
                    except Exception as fallback_err:
                        logger.error(f"Even fallback nonce determination failed: {fallback_err}")
                        return 0
    
        return self.w3.eth.get_transaction_count(address)

    def check_and_replace_stuck_transactions(self, address, latest_nonce, pending_nonce):
        """Check for stuck transactions and try to replace them"""
        logger.info(f"Checking for stuck transactions between nonce {latest_nonce} and {pending_nonce-1}")
        
        for nonce in range(latest_nonce, pending_nonce):
            try:
                txs = self.w3.eth.filter({
                    "fromBlock": self.w3.eth.block_number - 50,
                    "toBlock": "latest",
                    "address": None,
                    "topics": []
                }).get_all_entries()
                
                our_txs = [tx for tx in txs if tx.get('from', '').lower() == address.lower()]
                
                if not our_txs:
                    logger.warning(f"Transaction with nonce {nonce} not found in recent blocks")
                    replacement_tx = {
                        'from': address,
                        'to': address,
                        'value': 0,
                        'gas': 21000,
                        'gasPrice': int(self.w3.eth.gas_price * 1.5),
                        'nonce': nonce,
                        'chainId': self.config["chain_id"]
                    }
                    
                    signed_tx = self.account.sign_transaction(replacement_tx)
                    self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    logger.info(f"Sent replacement transaction for nonce {nonce}")
            
            except Exception as e:
                logger.warning(f"Error checking nonce {nonce}: {e}")

    def setup_transaction_monitoring(self):
        """Setup monitoring for transaction activity"""
        self.diagnostics = {
            "transaction_history": [],
            "gas_price_history": [],
            "rpc_performance": {},
            "errors_by_type": {},
            "network_status": {},
            "wallet_status": {}
        }
        
        self.diagnostics_file = "0g_diagnostics.json"
        if os.path.exists(self.diagnostics_file):
            try:
                with open(self.diagnostics_file, "r") as f:
                    self.diagnostics = json.load(f)
            except:
                pass
        
        def capture_tx_event(event_type, tx_hash=None, details=None):
            event = {
                "timestamp": time.time(),
                "type": event_type,
                "tx_hash": tx_hash,
                "details": details or {}
            }
            self.diagnostics["transaction_history"].append(event)
            if len(self.diagnostics["transaction_history"]) > 100:
                self.diagnostics["transaction_history"] = self.diagnostics["transaction_history"][-100:]
            
            try:
                with open(self.diagnostics_file, "w") as f:
                    json.dump(self.diagnostics, f, indent=2)
            except:
                pass
        
        self.capture_tx_event = capture_tx_event
        
        def update_gas_stats():
            try:
                current_gas = self.w3.eth.gas_price
                current_gwei = self.w3.from_wei(current_gas, 'gwei')
                
                self.diagnostics["gas_price_history"].append({
                    "timestamp": time.time(),
                    "gas_price_gwei": current_gwei
                })
                
                if len(self.diagnostics["gas_price_history"]) > 100:
                    self.diagnostics["gas_price_history"] = self.diagnostics["gas_price_history"][-100:]
            except:
                pass
        
        update_gas_stats()
        
        self.gas_monitor_thread = threading.Thread(target=lambda: (
            time.sleep(60), update_gas_stats(), True
        ))
        self.gas_monitor_thread.daemon = True
        self.gas_monitor_thread.start()
    
    def check_and_handle_stuck_transaction(self, tx_hash, wait_time):
        """Checks if a transaction is stuck and tries to handle it"""
        try:
            if wait_time < 90:
                return False
        
            logger.warning(f"Transaction {tx_hash.hex()} potentially stuck after {wait_time} seconds")
        
            tx = self.w3.eth.get_transaction(tx_hash)
            if not tx:
                logger.warning("Transaction not found in node - may have been dropped")
                return True
            
            if tx.get('blockNumber') is not None:
                logger.info(f"Transaction is mined in block {tx.get('blockNumber')} but awaiting confirmations")
                return False
            
            if wait_time > 180:
                logger.warning("Transaction stuck in mempool for too long")
            
                try:
                    nonce = tx.get('nonce')
                
                    logger.info(f"Attempting to replace stuck transaction. Original nonce: {nonce}")
                
                    replacement_tx = {
                        'from': tx.get('from'),
                        'to': tx.get('to'),
                        'value': tx.get('value'),
                        'gas': tx.get('gas'),
                        'gasPrice': int(tx.get('gasPrice') * 1.5),
                        'nonce': nonce,
                        'chainId': tx.get('chainId'),
                        'data': tx.get('input')
                    }
                
                    signed_tx = self.account.sign_transaction(replacement_tx)
                    replacement_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                
                    logger.info(f"Sent replacement transaction: {replacement_hash.hex()}")
                    return True
                
                except Exception as e:
                    logger.error(f"Failed to replace stuck transaction: {e}")
                    return True
                
            return False
        
        except Exception as e:
            logger.error(f"Error checking stuck transaction: {e}")
            return False
    
    def optimize_data_for_blockchain(self, data_dict):
        """Optimize data structure for blockchain storage to minimize gas"""
        key_mapping = {
            'timestamp': 'ts',
            'data_source': 'src',
            'collection_time': 'ct',
            'headlines': 'hdl',
            'cryptocurrencies': 'cc',
            'market_stats': 'ms',
            'id': 'i',
            'title': 't',
            'category': 'c',
            'published_at': 'p',
            'relevance_score': 'r',
            'symbol': 's',
            'name': 'n',
            'current_price': 'cp',
            'market_cap': 'mc',
            'total_volume': 'tv',
            'price_change_percentage_24h': 'pc',
        }
        
        def optimize_number(n):
            if isinstance(n, float):
                return round(n, 2)
            return n
        
        def optimize_dict(d):
            result = {}
            for k, v in d.items():
                new_key = key_mapping.get(k, k)
                
                if isinstance(v, dict):
                    result[new_key] = optimize_dict(v)
                elif isinstance(v, list):
                    result[new_key] = [
                        optimize_dict(item) if isinstance(item, dict) else optimize_number(item)
                        for item in v
                    ]
                elif isinstance(v, (int, float)):
                    result[new_key] = optimize_number(v)
                else:
                    result[new_key] = v
            return result
        
        optimized = optimize_dict(data_dict)
        
        optimized_json = json.dumps(optimized)
        if len(optimized_json.encode('utf-8')) > 8000:
            if 'hdl' in optimized and len(optimized.get('hdl', [])) > 5:
                optimized['hdl'] = optimized['hdl'][:5]
                optimized['note'] = 'trunc'
            
            if 'cc' in optimized and len(optimized.get('cc', [])) > 3:
                optimized['cc'] = optimized['cc'][:3]
                optimized['note'] = 'trunc'
        
        return optimized

    def analyze_0g_contract_requirements(self):
        """Analyze 0G smart contract requirements for successful submission"""
        try:
            contract_constants = {}
            
            try:
                contract_constants["MAX_DEPTH"] = self.contract.functions.MAX_DEPTH().call()
                logger.info(f"Contract MAX_DEPTH: {contract_constants['MAX_DEPTH']}")
            except:
                contract_constants["MAX_DEPTH"] = self.MAX_DEPTH
                logger.info(f"Using default MAX_DEPTH: {contract_constants['MAX_DEPTH']}")
            
            if self.config.get("network", "").lower() == "turbo":
                logger.info("Using Turbo mode - tags should be empty bytes")
                contract_constants["TAGS_REQUIRED"] = False
            else:
                logger.info("Using Standard mode - tags are recommended")
                contract_constants["TAGS_REQUIRED"] = True
            
            self.contract_constants = contract_constants
            
            return contract_constants
        except Exception as e:
            logger.error(f"Error analyzing contract requirements: {e}")
            return {
                "MAX_DEPTH": self.MAX_DEPTH,
                "TAGS_REQUIRED": self.config.get("network", "").lower() != "turbo"
            }

    def validate_submission_against_contract(self, submission):
        """Validate submission meets contract requirements"""
        if not hasattr(self, 'contract_constants'):
            self.analyze_0g_contract_requirements()
    
        errors = []
    
        if submission["length"] <= 0:
            errors.append("Data length must be positive")
    
        if not submission["nodes"]:
            errors.append("Submission must have at least one node")
    
        for i, node in enumerate(submission["nodes"]):
            if node["height"] >= self.contract_constants.get("MAX_DEPTH", self.MAX_DEPTH):
                errors.append(f"Node {i} height {node['height']} exceeds MAX_DEPTH {self.contract_constants.get('MAX_DEPTH', self.MAX_DEPTH)}")
                node["height"] = self.contract_constants.get("MAX_DEPTH", self.MAX_DEPTH) - 1
                logger.info(f"Auto-adjusted node {i} height to {node['height']}")
        
            if not isinstance(node["root"], bytes) or len(node["root"]) != 32:
                errors.append(f"Node {i} root must be bytes32, not {type(node['root'])} with length {len(node['root']) if isinstance(node['root'], bytes) else 'N/A'}")
                if isinstance(node["root"], bytes) and len(node["root"]) > 32:
                    node["root"] = node["root"][:32]
                    logger.info(f"Truncated node {i} root to 32 bytes")
                elif isinstance(node["root"], bytes) and len(node["root"]) < 32:
                    node["root"] = node["root"].ljust(32, b'\0')
                    logger.info(f"Padded node {i} root to 32 bytes")
    
        if self.contract_constants.get("TAGS_REQUIRED", False) and not submission["tags"]:
            errors.append("Tags are required for this network type")
            submission["tags"] = "0x00"
            logger.info("Added default tag 0x00")
    
        if "file_size_kb" in submission:
            expected_length = int(submission["file_size_kb"] * 1024)
            if submission["length"] > expected_length * 1.1 or submission["length"] < expected_length * 0.9:
                errors.append(f"Length {submission['length']} significantly differs from expected file size {expected_length}")
                submission["length"] = expected_length
                logger.info(f"Auto-adjusted length to match file size: {expected_length}")
    
        if errors:
            critical_errors = [e for e in errors if "must be" in e or "required" in e]
            if critical_errors:
                logger.error(f"Critical submission validation issues: {'; '.join(critical_errors)}")
                return False
            else:
                logger.warning(f"Non-critical submission issues were auto-fixed: {'; '.join(errors)}")
    
        return True

    def validate_merkle_tree_structure(self, submission):
        if not submission["nodes"]:
            logger.error("No merkle nodes in submission")
            return False
        for node in submission["nodes"]:
            if node["height"] < 0:
                logger.error("Negative height in merkle tree")
                return False
        return True
    
    def simplify_crypto_data(self, data):
        """Simplify cryptocurrency data to reduce size"""
        if not data or 'cryptocurrencies' not in data:
            return data
        
        logger.info("Simplifying cryptocurrency data to reduce size")
        
        simplified = {
            'timestamp': data['timestamp'],
            'data_source': data['data_source'],
            'collection_time': data['collection_time'],
            'simplified': True,
            'cryptocurrencies': []
        }
        
        essential_fields = ['id', 'symbol', 'name', 'current_price', 'market_cap', 
                            'market_cap_rank', 'total_volume', 'price_change_percentage_24h']
        
        for coin in data['cryptocurrencies']:
            slim_coin = {field: coin.get(field) for field in essential_fields if field in coin}
            simplified['cryptocurrencies'].append(slim_coin)
        
        if 'market_stats' in data:
            simplified['market_stats'] = data['market_stats']
        
        return simplified
    
    def save_data_to_file(self, data, source_name):
        """Save data to JSON file with size limit"""
        if not data:
            logger.warning(f"No data to save for {source_name}")
            return None
        
        data_str = json.dumps(data) if isinstance(data, dict) else data.decode('utf-8') if isinstance(data, bytes) else str(data)
        data_size_kb = len(data_str.encode('utf-8')) / 1024
        
        if data_size_kb > self.config["max_file_size_kb"]:
            logger.warning(f"Data size ({data_size_kb:.2f}KB) exceeds limit of {self.config['max_file_size_kb']}KB. Trimming...")
            
            if source_name == "news":
                headlines = data.get('headlines', [])
                original_count = len(headlines)
                
                while data_size_kb > self.config["max_file_size_kb"] and len(data['headlines']) > 5:
                    data['headlines'] = data['headlines'][:-1]
                    data['note'] = f"Data trimmed from {original_count} to {len(data['headlines'])} headlines due to size limit"
                    data_str = json.dumps(data)
                    data_size_kb = len(data_str.encode('utf-8')) / 1024
            
            elif source_name == "crypto_prices":
                if 'market_stats' in data:
                    del data['market_stats']
                    data['note'] = "Market stats removed due to size limit"
                    data_str = json.dumps(data)
                    data_size_kb = len(data_str.encode('utf-8')) / 1024
                
                if data_size_kb > self.config["max_file_size_kb"] and 'cryptocurrencies' in data:
                    for coin in data['cryptocurrencies']:
                        for field in ['description', 'links', 'image', 'community_data', 'developer_data']:
                            if field in coin:
                                del coin[field]
                    
                    data['note'] = "Cryptocurrency data simplified due to size limit"
                    data_str = json.dumps(data)
                    data_size_kb = len(data_str.encode('utf-8')) / 1024
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = "jpg" if source_name == "image" else "json"
        filename = f"{source_name}_{timestamp}.{ext}"
        filepath = os.path.join(self.config["data_dir"], filename)
        
        if ext == "jpg":
            with open(filepath, 'wb') as f:
                f.write(data)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(data_str)
        
        logger.info(f"Saved {source_name} data to {filepath} ({data_size_kb:.2f}KB)")
        return filepath

    def submit_data_to_contract(self, submission):
        """Submit data to the contract dengan tiga tahap yang jelas"""
        max_retries = 5
        current_retry = 0
        last_error = None
        length_mode = "segments"  # Coba dengan length dalam segmen terlebih dahulu

        logger.info(f"{Fore.YELLOW} Step 2: Preparing Registration Transaction{Fore.RESET}")

        network = submission.get("network", "turbo")

        initial_delay = random.randint(8, 12)
        logger.info(f"Adding initial delay of {initial_delay} seconds before transaction...")
        time.sleep(initial_delay)

        if hasattr(self, 'last_tx_attempt') and (datetime.now() - self.last_tx_attempt).total_seconds() < 60:
            delay = random.randint(15, 30)
            logger.info(f"Adding {delay} seconds delay before transaction...")
            time.sleep(delay)

        self.last_tx_attempt = datetime.now()

        file_size_bytes = 0
        if 'file_path' in submission and os.path.exists(submission['file_path']):
            file_size_bytes = os.path.getsize(submission['file_path'])
            file_size_kb = file_size_bytes / 1024
        elif 'file_size_kb' in submission:
            file_size_kb = submission['file_size_kb']
            file_size_bytes = int(file_size_kb * 1024)
        else:
            file_size_kb = 0
    
        storage_fee_wei = self.calculate_storage_fee(file_size_bytes)
        storage_fee = self.w3.from_wei(storage_fee_wei, 'ether')

        logger.info(f"File Size: {file_size_kb:.2f} KB")
        logger.info(f"Storage Endowment: {storage_fee:.8f} 0G")

        if file_size_kb > 200:
            logger.warning(f"Data file is {file_size_kb:.2f}KB which may require significant gas")
    
        while current_retry < max_retries:
            try:
                nonce = self.get_optimal_nonce_strategy(self.account.address)
        
                base_multiplier = 1.05
                retry_increment = 0.15
                gas_price_multiplier = base_multiplier + (current_retry * retry_increment)
                gas_price = int(self.w3.eth.gas_price * gas_price_multiplier)
        
                min_gas_price = self.w3.to_wei(5, 'gwei')
                max_gas_price = self.w3.to_wei(10, 'gwei')
                gas_price = max(min_gas_price, min(gas_price, max_gas_price))
        
                logger.info(f"Gas Price: {self.w3.from_wei(gas_price, 'gwei')} Gwei")
        
                if isinstance(submission["tags"], str) and submission["tags"].startswith("0x"):
                    tags_bytes = bytes.fromhex(submission["tags"][2:])
                else:
                    tags_bytes = b''
        
                # Coba length dalam jumlah chunk atau byte jika gagal dengan segmen
                if length_mode == "chunks":
                    submission["length"] = submission["num_chunks"]
                    logger.info(f"Retrying with length in chunks: {submission['length']}")
                elif length_mode == "bytes":
                    submission["length"] = submission["num_bytes"]
                    logger.info(f"Retrying with length in bytes: {submission['length']}")
        
                contract_submission = [
                    submission["length"],
                    tags_bytes,
                    [[node["root"], node["height"]] for node in submission["nodes"]]
                ]
        
                logger.info(f"Contract submission format: [uint256, bytes, [bytes32, uint256][]]")
                logger.info(f"Parameters: length={contract_submission[0]} {length_mode}, tags={submission['tags']}, nodes_count={len(contract_submission[2])}")
        
                gas_limit = 200000 if file_size_bytes > 256 else 100000
                try:
                    gas_estimate = self.contract.functions.submit(contract_submission).estimate_gas({
                        'from': self.account.address,
                        'nonce': nonce,
                        'value': storage_fee_wei
                    })
                    gas_limit = int(gas_estimate * 1.1)
                    logger.info(f"Estimated gas: {gas_estimate}, using {gas_limit} with buffer")
                except Exception as e:
                    logger.warning(f"Gas estimation failed: {e}. Using default: {gas_limit}")
        
                gas_fee = gas_limit * gas_price
                gas_fee_0G = self.w3.from_wei(gas_fee, 'ether')
                logger.info(f"Gas Fee: {gas_fee_0G:.18f} 0G")
        
                total_fee = self.w3.from_wei(gas_fee + storage_fee_wei, 'ether')
                logger.info(f"Total Fee: {total_fee:.18f} 0G")

                pre_tx_delay = 5
                logger.info(f"Waiting {pre_tx_delay} seconds before sending transaction...")
                time.sleep(pre_tx_delay)

                tx = self.contract.functions.submit(contract_submission).build_transaction({
                    'from': self.account.address,
                    'gas': gas_limit,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'chainId': self.config["chain_id"],
                    'value': storage_fee_wei
                })
        
                logger.info(f"Signing transaction...")
                signed_tx = self.account.sign_transaction(tx)
        
                time.sleep(5)
        
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                tx_hash_hex = tx_hash.hex()
        
                logger.info(f"Transaction sent: {tx_hash_hex}")
                logger.info(f"{Fore.MAGENTA} ✓ Registration transaction submitted successfully{Fore.RESET}")
        
                logger.info(f"{Fore.YELLOW} Step 3: Waiting for checking file metadata...{Fore.RESET}")
        
                receipt = None
                wait_time = 0
                max_wait = 300
                base_check_interval = 10
        
                tx_details = {"pending": True, "mined": False, "status": None}
        
                while receipt is None and wait_time < max_wait:
                    try:
                        if wait_time % 30 == 0:
                            try:
                                pending_tx = self.w3.eth.get_transaction(tx_hash)
                                if pending_tx:
                                    block_num = pending_tx.get('blockNumber')
                                    if block_num is None:
                                        logger.info(f"Transaction still in mempool after {wait_time}s")
                                    else:
                                        logger.info(f"Transaction mined in block {block_num}, waiting for confirmations...")
                                        tx_details["mined"] = True
                            except Exception as tx_err:
                                logger.warning(f"Error checking transaction status: {tx_err}")
                    
                        receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                
                        if receipt is None:
                            check_interval = min(base_check_interval + (wait_time // 30) * 5, 30)
                            logger.info(f"Waiting for transaction confirmation... ({wait_time}s / {max_wait}s)")
                            time.sleep(check_interval)
                            wait_time += check_interval
                        else:
                            logger.info(f"Got transaction receipt after {wait_time}s")
                            tx_details["pending"] = False
                            tx_details["status"] = receipt.get('status')
                            break
                    except Exception as e:
                        if "not found" in str(e).lower():
                            if wait_time < 30:
                                logger.info(f"Transaction not found yet, waiting for propagation... ({wait_time}s)")
                            elif wait_time > 150 and not tx_details["mined"]:
                                logger.warning(f"Transaction may have been dropped after {wait_time} seconds")
                                try:
                                    latest_block = self.w3.eth.block_number
                                    start_block = max(0, latest_block - 10)
                            
                                    logger.info(f"Checking recent blocks ({start_block}-{latest_block}) for our transaction...")
                                    for block_num in range(start_block, latest_block + 1):
                                        block = self.w3.eth.get_block(block_num, full_transactions=True)
                                        for tx in block.transactions:
                                            if tx.get('from', '').lower() == self.account.address.lower():
                                                logger.info(f"Found transaction from our account in block {block_num}: {tx.hash.hex()}")
                                except Exception as block_err:
                                    logger.warning(f"Error checking recent blocks: {block_err}")
                            
                                if wait_time > 150:
                                    if self.check_and_handle_stuck_transaction(tx_hash, wait_time):
                                        logger.warning("Transaction not found after extended period, breaking to retry")
                                        break
                
                        check_interval = min(base_check_interval + (wait_time // 30) * 5, 20)
                        time.sleep(check_interval)
                        wait_time += check_interval
        
                if receipt and receipt.get('blockNumber'):
                    confirmation_wait = 0
                    max_confirmation_wait = 60
            
                    while confirmation_wait < max_confirmation_wait:
                        try:
                            current_block = self.w3.eth.block_number
                            tx_block = receipt.get('blockNumber')
                            confirmations = current_block - tx_block + 1
                    
                            if confirmations >= 2:
                                logger.info(f"Transaction confirmed with {confirmations} confirmations")
                                break
                            else:
                                logger.info(f"Waiting for confirmations... (Current: {confirmations}, Block: {current_block}, Tx Block: {tx_block})")
                                time.sleep(10)
                                confirmation_wait += 10
                        except Exception as conf_err:
                            logger.warning(f"Error checking confirmations: {conf_err}")
                            time.sleep(10)
                            confirmation_wait += 10
        
                if receipt:
                    if receipt.get('status') == 1:
                        block_number = receipt.get('blockNumber')
                        gas_used = receipt.get('gasUsed')
                        actual_gas_fee = self.w3.from_wei(gas_used * gas_price, 'ether')
            
                        logger.info(f"Upload complete! Transaction successful in block #{block_number}")
                        logger.info(f"Gas used: {gas_used} ({(gas_used/gas_limit)*100:.1f}% of limit)")
                        logger.info(f"Actual gas fee: {actual_gas_fee:.18f} 0G")
                        logger.info(f"Storage node fee: {storage_fee:.12f} 0G")
                        logger.info(f"Total fee paid: {actual_gas_fee + storage_fee:.12f} 0G")
                        logger.info(f"Root hash: {submission.get('root_hash')}")
                        logger.info(f"{Fore.MAGENTA}✓ Data successfully uploaded and registered on-chain!{Fore.RESET}")
            
                        if 'file_path' in submission and os.path.exists(submission['file_path']):
                            logger.info(f"Removing uploaded file to save space")
                            os.remove(submission['file_path'])
            
                        return receipt
                    else:
                        tx_block = receipt.get('blockNumber')
                        gas_used = receipt.get('gasUsed')
                        logger.error(f"{Fore.RED}✗ Transaction failed on-chain. Status: {receipt.get('status')}{Fore.RESET}")
                        logger.error(f"Gas used: {gas_used} ({(gas_used/gas_limit)*100:.1f}% of limit)")
                        logger.error(f"Block number: {tx_block}")
            
                        if gas_used >= gas_limit * 0.95:
                            logger.warning("Transaction likely failed due to out of gas. Will increase gas limit next time.")
                            gas_limit = int(gas_limit * 1.2)
                        elif gas_used < gas_limit * 0.5:
                            logger.warning("Transaction used less than half of gas limit, likely reverted by contract.")
                            try:
                                self.w3.eth.call(tx, block_identifier=tx_block)
                            except Exception as call_err:
                                error_msg = str(call_err)
                                logger.error(f"Transaction reverted with: {error_msg}")
                        
                                if "execution reverted" in error_msg.lower():
                                    if "mempool is full" in error_msg.lower():
                                        logger.warning("Contract rejected due to mempool being full. Waiting before retry...")
                                        time.sleep(random.randint(45, 90))
                                    elif "invalid merkle" in error_msg.lower():
                                        logger.error("Contract rejected due to invalid Merkle tree structure.")
                                        # Coba length dalam chunks atau byte pada retry berikutnya
                                        if length_mode == "segments":
                                            length_mode = "chunks"
                                        elif length_mode == "chunks":
                                            length_mode = "bytes"
                
                        post_failure_delay = random.randint(15, 30)
                        logger.info(f"Waiting {post_failure_delay} seconds after transaction failure before retry...")
                        time.sleep(post_failure_delay)
                else:
                    logger.warning(f"Transaction not confirmed after {max_wait} seconds.")
                    try:
                        pending_tx = self.w3.eth.get_transaction(tx_hash)
                        if pending_tx:
                            block_num = pending_tx.get('blockNumber')
                            if block_num is None:
                                logger.warning("Transaction still in mempool but not mined after extended period.")
                            else:
                                logger.warning(f"Transaction mined in block {block_num} but receipt unavailable.")
                        else:
                            logger.warning("Transaction not found in node.")
                    except Exception as tx_err:
                        logger.warning(f"Error getting transaction details: {tx_err}")
            
                    if not self.retry_with_new_rpc():
                        logger.info("Could not switch RPC, waiting before next attempt...")
                        time.sleep(random.randint(30, 60))
    
            except Exception as e:
                last_error = e
                error_str = str(e)
                logger.error(f"✗ Error submitting data (attempt {current_retry+1}/{max_retries}): {error_str}")
        
                if "mempool is full" in error_str.lower():
                    delay = random.randint(90, 180)
                    logger.warning(f"Mempool is full, waiting {delay} seconds...")
                    time.sleep(delay)
            
                    if not self.retry_with_new_rpc():
                        logger.warning("Could not switch RPC, increasing gas price and waiting longer")
                        time.sleep(random.randint(30, 60))
                elif "insufficient funds" in error_str.lower():
                    logger.error("Wallet has insufficient funds for this transaction")
                    if len(self.private_keys) > 1:
                        logger.info("Trying with a different wallet...")
                        self.rotate_private_key()
                    else:
                        logger.error("No alternative wallet available. Cannot proceed.")
                        return None
                elif "invalid nonce" in error_str.lower():
                    logger.warning("Nonce issue detected, will adjust in next attempt")
                    try:
                        latest_nonce = self.w3.eth.get_transaction_count(self.account.address, 'latest')
                        logger.info(f"Reset to latest confirmed nonce: {latest_nonce}")
                    except Exception as nonce_err:
                        logger.warning(f"Error refreshing nonce: {nonce_err}")
                elif "underpriced" in error_str.lower():
                    logger.warning("Transaction underpriced, increasing gas price significantly")
                    increase_factor = 1.18
                    min_gas_price = self.w3.to_wei(self.w3.from_wei(gas_price, 'gwei') * increase_factor, 'gwei')
                else:
                    if not self.retry_with_new_rpc():
                        if current_retry > 0 and len(self.private_keys) > 1:
                            logger.info("Trying with a different wallet...")
                            self.rotate_private_key()
        
                backoff_base = 15
                max_backoff = 180
                delay = min(backoff_base * (2 ** current_retry) + random.randint(0, 30), max_backoff)
                logger.info(f"Waiting {delay} seconds before retry {current_retry+1}")
                time.sleep(delay)
    
            current_retry += 1

        logger.error("✗ Failed to submit data after multiple attempts")
        return None
    
    def fetch_crypto_prices(self):
        """Fetch cryptocurrency price data from CoinGecko"""
        api_key = self.config["coingecko_api_key"]
        if not api_key:
            logger.warning("No CoinGecko API key provided, skipping crypto price fetch")
            return None
        
        try:
            logger.info(f"Fetching data from CoinGecko API")
            
            url = "https://api.coingecko.com/api/v3/coins/markets"
            
            params = {
                "vs_currency": "usd",
                "ids": "bitcoin",
                "category": "layer-1",
                "order": "volume_desc",
                "per_page": 21,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "1h",
                "locale": "en",
                "precision": 6
            }
            
            headers = {
                "accept": "application/json",
                "x-cg-demo-api-key": api_key
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            structured_data = {
                'timestamp': datetime.now().isoformat(),
                'data_source': "coingecko_prices",
                'collection_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'cryptocurrencies': data
            }
            
            if len(data) > 0:
                total_market_cap = sum(coin.get('market_cap', 0) for coin in data if coin.get('market_cap') is not None)
                total_volume = sum(coin.get('total_volume', 0) for coin in data if coin.get('total_volume') is not None)
                
                structured_data['market_stats'] = {
                    'total_market_cap': total_market_cap,
                    'total_24h_volume': total_volume,
                    'num_cryptocurrencies': len(data)
                }
            
            return structured_data
        except Exception as e:
            logger.error(f"Error fetching crypto price data: {e}")
            return None

    def fetch_news_from_x(self):
        """Fetch recent posts from X related to AI, Crypto, or other topics"""
        try:
            logger.info("Fetching recent posts from X...")
        
            bearer_token = os.getenv("X_BEARER_TOKEN")
            if not bearer_token:
                logger.error("No X Bearer Token provided. Please set X_BEARER_TOKEN in .env file.")
                logger.info("To get X_BEARER_TOKEN, follow these steps:")
                logger.info("1. Go to https://developer.x.com/ and sign up/log in.")
                logger.info("2. Create a new project and app in the Developer Portal.")
                logger.info("3. Enable Read access for API v2.")
                logger.info("4. Copy the Bearer Token from your app's dashboard.")
                logger.info("5. Add to .env file: X_BEARER_TOKEN=your_bearer_token_here")
                return None
        
            url = "https://api.twitter.com/2/tweets/search/recent"
            headers = {"Authorization": f"Bearer {bearer_token}"}
            params = {
                "query": "(AI OR Testnet OR Bitcoin OR Binance OR Crypto OR Blockchain OR Airdrop OR DeFi) -is:retweet lang:en",
                "max_results": 5,
                "tweet.fields": "created_at"
            }
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
        
            data = response.json().get('data', [])
            if not data:
                logger.warning("No recent tweets found for the given query")
                return None

            structured_data = {
                'timestamp': datetime.now().isoformat(),
                'data_source': "x_news",
                'collection_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'posts': [{"text": tweet["text"], "created_at": tweet["created_at"]} for tweet in data]
            }
            return structured_data
        except Exception as e:
            logger.error(f"Error fetching X news: {e}")
            return None

    def fetch_small_image(self):
        """Fetch a small image (e.g., a thumbnail) for upload"""
        try:
            logger.info("Fetching a small image for upload...")
            max_attempts = 5
            for attempt in range(max_attempts):
                # Gunakan picsum.photos dengan ukuran 50x50 untuk gambar kecil
                random_id = random.randint(1, 1000)
                image_url = f"https://picsum.photos/50/50?random={random_id}"
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            
                response = requests.get(image_url, headers=headers, timeout=10)
                response.raise_for_status()
            
                image_data = response.content
                image_size = len(image_data)
            
                if image_size <= 256:
                    logger.info(f"Image fetched successfully: {image_size} bytes")
                    return image_data
                else:
                    logger.warning(f"Image size ({image_size} bytes) exceeds 256 bytes, retrying... ({attempt+1}/{max_attempts})")
                    if attempt == max_attempts - 1:
                        logger.error("Failed to fetch image under 256 bytes after max attempts")
                        return None
                    time.sleep(3)  # Jeda sebelum mencoba lagi
        
            return None
        except Exception as e:
            logger.error(f"Error fetching image: {e}")
            return None

    def process_hourly_update(self):
        """Main function to run hourly updates with random data source (JSON, image, or X news)"""
        try:
            rotate_logs()
            clean_old_data_files(days=1)
            self.setup_web3_provider()
    
            if not self.verify_wallet_connection():
                logger.error("Wallet connection failed, cannot proceed with upload")
                return
    
            network = self.config.get("network", "turbo").lower()
            logger.info(f"Configured to use '{network}' network")
    
            # Pilih sumber data secara acak (50:50 antara JSON dan lainnya)
            data_choice = random.choice(["json", "other"])
            data_type = None
            filepath = None
        
            if data_choice == "json":
                data_type = "crypto_prices"
                logger.info("Fetching crypto price data from CoinGecko...")
                data = self.fetch_crypto_prices()
                if data:
                    simplified_data = self.simplify_crypto_data(data)
                    optimized_data = self.optimize_data_for_blockchain(simplified_data)
                    filepath = self.save_data_to_file(optimized_data, data_type)
            else:
                # Pilih antara gambar atau berita X
                sub_choice = random.choice(["image", "x_news"])
                if sub_choice == "image":
                    data_type = "image"
                    logger.info("Fetching a small image for upload...")
                    image_data = self.fetch_small_image()
                    if image_data:
                        filepath = self.save_data_to_file(image_data, data_type)
                else:
                    data_type = "x_news"
                    logger.info("Fetching news from X...")
                    news_data = self.fetch_news_from_x()
                    if news_data:
                        optimized_data = self.optimize_data_for_blockchain(news_data)
                        filepath = self.save_data_to_file(optimized_data, data_type)

            if filepath:
                logger.info(f"Selected data type: {data_type}")
                logger.info(f"Preparing submission for {filepath}...")
                submission = self.implement_data_chunking_strategy(filepath)

                if submission:
                    if self.validate_submission_against_contract(submission) and self.validate_merkle_tree_structure(submission):
                        logger.info(f"Submitting {data_type} data to contract...")
                        receipt = self.submit_data_to_contract(submission)
                        if receipt:
                            logger.info(f"{Fore.GREEN}✅ {data_type.capitalize()} data upload successful!{Style.RESET_ALL}")
                            # Pastikan file dihapus setelah diunggah
                            if os.path.exists(filepath):
                                logger.info(f"Removing uploaded file: {filepath}")
                                os.remove(filepath)
                        else:
                            logger.error(f"{Fore.RED}❌ Failed to submit {data_type} data to contract{Style.RESET_ALL}")
                    else:
                        logger.warning("Submission validation failed")
                else:
                    logger.error("Failed to prepare submission")
            else:
                logger.error(f"No {data_type} data to upload")
            
        except Exception as e:
            logger.error(f"Error in hourly update process: {str(e)}")
            logger.debug(traceback.format_exc())

def main():
    """Main function to start the scheduler"""
    print(f"{Fore.CYAN}OG Chain Data Uploader Start.....{Style.RESET_ALL}")
    try:
        uploader = OGDataUploader()
        print(f"\n{Fore.CYAN}Running initial test update...{Style.RESET_ALL}")
        uploader.process_hourly_update()
        
        # Setup scheduler dengan interval acak 30-90 menit
        scheduler = BlockingScheduler()
        # Tambahkan job dengan interval awal 0 detik, lalu atur ulang interval di dalam job
        scheduler.add_job(
            lambda: uploader.process_hourly_update(), 
            'interval', 
            seconds=0,  # Akan diatur ulang di dalam job
            id='random_update_job',
            max_instances=1
        )
        
        def schedule_random_interval(scheduler, uploader):
            delay = random.randint(500, 800)  # 30-90 menit
            logger.info(f"Next update in {delay // 60} minutes")
            scheduler.modify_job('random_update_job', next_run_time=datetime.now() + timedelta(seconds=delay))
            uploader.process_hourly_update()
            # Jadwalkan ulang setelah selesai
            scheduler.modify_job('random_update_job', next_run_time=datetime.now() + timedelta(seconds=delay))
        
        # Mulai scheduler dengan job pertama
        scheduler.add_job(lambda: schedule_random_interval(scheduler, uploader), 'date', run_date=datetime.now())
        
        print(f"\n{Fore.GREEN}Starting scheduler with random intervals (30-90 minutes)...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Press Ctrl+C to exit{Style.RESET_ALL}")
        scheduler.start()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Program interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Critical error: {str(e)}{Style.RESET_ALL}")
        logger.critical(f"Critical error: {str(e)}")
        logger.debug(traceback.format_exc())

if __name__ == "__main__":
    main()