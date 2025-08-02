import requests
import json
import os
import time
import random
import logging
from datetime import datetime, timedelta
from web3 import Web3
import hashlib
import shutil
from dotenv import load_dotenv
from colorama import Fore, Style, init
from hexbytes import HexBytes

init(autoreset=True)
load_dotenv()

# Konfig logging
LOG_FILE = "og_uploader.log"
MAX_LOG_SIZE = 2 * 1024 * 1024  # 2Mb
MAX_LOG_FILES = 3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        level = record.levelname
        msg = record.getMessage()
        if level == 'INFO':
            return f"{Fore.CYAN}[i] {msg}{Style.RESET_ALL}"
        elif level == 'WARNING':
            return f"{Fore.YELLOW}[!] {msg}{Style.RESET_ALL}"
        elif level == 'ERROR':
            return f"{Fore.RED}[x] {msg}{Style.RESET_ALL}"
        elif level == 'CRITICAL':
            return f"{Fore.RED}{Style.BRIGHT}[FATAL] {msg}{Style.RESET_ALL}"
        return super().format(record)

for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))

def print_banner():
    banner = f"""
{Fore.GREEN}============================ WELCOME TO Onchain DAPPs ============================{Fore.RESET}
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

def section(msg=None):
    line = '─' * 40
    logger.info(f"\n{Fore.GRAY}{line}{Style.RESET_ALL}")
    if msg:
        logger.info(f"{Fore.WHITE}{Style.BRIGHT} {msg} {Style.RESET_ALL}")
    logger.info(f"{Fore.GRAY}{line}{Style.RESET_ALL}\n")

def success(msg):
    logger.info(f"{Fore.GREEN}[+] {msg}{Style.RESET_ALL}")

def loading(msg):
    logger.info(f"{Fore.MAGENTA}[*] {msg}{Style.RESET_ALL}")

def step(msg):
    logger.info(f"{Fore.BLUE}[>] {Style.BRIGHT}{msg}{Style.RESET_ALL}")

def summary(msg):
    logger.info(f"{Fore.GREEN}{Style.BRIGHT}[SUMMARY] {msg}{Style.RESET_ALL}")

def wallet(msg):
    logger.info(f"{Fore.LIGHTBLUE_EX}[W] {msg}{Style.RESET_ALL}")

def countdown(msg):
    print(f"\r{Fore.BLUE}[⏰] {msg}{Style.RESET_ALL}", end="")

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
        logger.error(f"Error rotating logs: {e}")

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

# Konfig
ZERO_G_CHAIN_ID = 16601
ZERO_G_RPC_URL = 'https://evmrpc-testnet.0g.ai'
ZERO_G_CONTRACT_ADDRESS = Web3.to_checksum_address('0x5f1d96895e442fc0168fa2f9fb1ebef93cb5035e')
ZERO_G_METHOD_ID = '0xef3e12dc'
PROXY_FILE = 'proxies.txt'
INDEXER_URL = 'https://indexer-storage-testnet-turbo.0g.ai'
EXPLORER_URL = 'https://chainscan-galileo.0g.ai/tx/'

IMAGE_SOURCES = [
    {'url': 'https://picsum.photos/800/600', 'response_type': 'content'},
    {'url': 'https://loremflickr.com/800/600', 'response_type': 'content'}
]

private_keys = []
current_key_index = 0
proxies = []
current_proxy_index = 0

w3 = Web3(Web3.HTTPProvider(ZERO_G_RPC_URL))

def load_private_keys():
    """Load private keys from .env and private_keys.txt"""
    global private_keys
    private_keys = []
    
    # Load .env
    index = 1
    while True:
        key = os.getenv(f"PRIVATE_KEY_{index}")
        if not key:
            break
        if is_valid_private_key(key):
            private_keys.append(key)
        else:
            logger.error(f"Invalid private key format at PRIVATE_KEY_{index}")
        index += 1
    
    # Load private_keys.txt
    try:
        with open("private_keys.txt", "r") as file:
            keys = [line.strip() for line in file.readlines() if line.strip()]
            for key in keys:
                if is_valid_private_key(key):
                    private_keys.append(key)
                else:
                    logger.error(f"Invalid private key format in private_keys.txt: {key}")
    except Exception as e:
        logger.warning(f"Note: private_keys.txt not found or couldn't be read: {e}")

    private_keys = list(set(private_keys))
    if not private_keys:
        logger.critical("No valid private keys found in .env or private_keys.txt")
        return False
    
    success(f"Loaded {len(private_keys)} private key(s)")
    return True

def is_valid_private_key(key):
    """Validate private key format"""
    key = key.strip()
    if not key.startswith('0x'):
        key = '0x' + key
    try:
        bytes_key = bytes.fromhex(key.replace('0x', ''))
        return len(key) == 66 and len(bytes_key) == 32
    except:
        return False

def get_next_private_key():
    """Get the next private key"""
    global current_key_index
    return private_keys[current_key_index]

def load_proxies():
    """Load proxies from proxies.txt"""
    global proxies, current_proxy_index
    try:
        if os.path.exists(PROXY_FILE):
            with open(PROXY_FILE, 'r') as file:
                proxies = [line.strip() for line in file.readlines() if line.strip() and not line.startswith('#')]
            if proxies:
                logger.info(f"Loaded {len(proxies)} proxies")
            else:
                logger.warning(f"No proxies found in {PROXY_FILE}")
        else:
            logger.warning(f"Proxy file {PROXY_FILE} not found")
    except Exception as e:
        logger.error(f"Failed to load proxies: {e}")
    current_proxy_index = 0

def get_next_proxy():
    """Get the next proxy"""
    global current_proxy_index
    if not proxies:
        return None
    proxy = proxies[current_proxy_index]
    current_proxy_index = (current_proxy_index + 1) % len(proxies)
    return proxy

def create_session():
    """Create a requests session with proxy and headers"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        ]),
        'accept': 'application/json, text/plain, */*',
        'Referer': 'https://storagescan-galileo.0g.ai/'
    })
    proxy = get_next_proxy()
    if proxy:
        session.proxies = {'http': proxy, 'https': proxy}
    return session

def initialize_wallet():
    """Initialize wallet with the current private key"""
    private_key = get_next_private_key()
    return w3.eth.account.from_key(private_key)

def check_network_sync():
    """Check if the 0G network is synced"""
    try:
        loading("Checking 0G network sync...")
        block_number = w3.eth.block_number
        success(f"0G Network synced at block {block_number}")
        return True
    except Exception as e:
        logger.error(f"0G Network sync check failed: {e}")
        return False

def fetch_random_image():
    """Fetch a random image from predefined sources"""
    try:
        loading("Fetching random image...")
        session = create_session()
        source = random.choice(IMAGE_SOURCES)
        response = session.get(source['url'], timeout=10)
        response.raise_for_status()
        success("Image fetched successfully")
        return response.content
    except Exception as e:
        logger.error(f"Error fetching image: {e}")
        raise

def check_file_exists(file_hash):
    """Check if a file hash already exists on the indexer"""
    try:
        loading(f"Checking file hash {file_hash}...")
        session = create_session()
        response = session.get(f"{INDEXER_URL}/file/info/{file_hash}", timeout=10)
        return response.json().get('exists', False)
    except Exception as e:
        logger.warning(f"Failed to check file hash: {e}")
        return False

def prepare_image_data(image_buffer):
    """Prepare image data with unique hash"""
    MAX_HASH_ATTEMPTS = 5
    for attempt in range(1, MAX_HASH_ATTEMPTS + 1):
        hash_input = image_buffer + os.urandom(16)
        hash_obj = hashlib.sha256(hash_input)
        file_hash = '0x' + hash_obj.hexdigest()
        if not check_file_exists(file_hash):
            success(f"Generated unique file hash: {file_hash}")
            return {'root': file_hash, 'data': image_buffer.hex()}
        logger.warning(f"Hash {file_hash} already exists, retrying...")
    raise Exception(f"Failed to generate unique hash after {MAX_HASH_ATTEMPTS} attempts")

def fetch_crypto_prices():
    """Fetch cryptocurrency price data from CoinGecko"""
    api_key = os.getenv("COINGECKO_API_KEY")
    if not api_key:
        logger.warning("No CoinGecko API key provided, skipping crypto price fetch")
        return None
    try:
        logger.info("Fetching data from CoinGecko API")
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
        headers = {"accept": "application/json", "x-cg-demo-api-key": api_key}
        session = create_session()
        response = session.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        structured_data = {
            'timestamp': datetime.now().isoformat(),
            'data_source': "coingecko_prices",
            'collection_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'cryptocurrencies': data
        }
        if data:
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

def save_data_to_file(data, source_name):
    """Save data to file in data_files directory"""
    data_dir = os.getenv("DATA_DIR", "data_files")
    os.makedirs(data_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = "jpg" if source_name == "image" else "json"
    filename = f"{source_name}_{timestamp}.{ext}"
    filepath = os.path.join(data_dir, filename)
    
    if source_name == "image":
        with open(filepath, 'wb') as f:
            f.write(bytes.fromhex(data['data']))
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    
    file_size_kb = os.path.getsize(filepath) / 1024
    logger.info(f"Saved {source_name} data to {filepath} ({file_size_kb:.2f}KB)")
    return filepath

def upload_to_storage(data, wallet, wallet_index):
    """Upload data to storage and submit to contract"""
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 300
    loading(f"Checking wallet balance for {wallet.address}...")
    balance = w3.eth.get_balance(wallet.address)
    if balance < Web3.to_wei(0.0015, 'ether'):
        raise Exception(f"Insufficient balance: {Web3.from_wei(balance, 'ether')} OG")
    success(f"Wallet balance: {Web3.from_wei(balance, 'ether')} OG")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            loading(f"Uploading file for wallet #{wallet_index + 1} (Attempt {attempt})...")
            session = create_session()
            response = session.post(
                f"{INDEXER_URL}/file/segment",
                json={
                    'root': data['root'],
                    'index': 0,
                    'data': data['data'],
                    'proof': {'siblings': [data['root']], 'path': []}
                },
                headers={'content-type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            success("File segment uploaded")

            # Data transactions
            tx_data = (
                HexBytes(ZERO_G_METHOD_ID) +
                HexBytes('0000000000000000000000000000000000000000000000000000000000000020') +
                HexBytes('0000000000000000000000000000000000000000000000000000000000000014') +
                HexBytes('0000000000000000000000000000000000000000000000000000000000000060') +
                HexBytes('0000000000000000000000000000000000000000000000000000000000000080') +
                HexBytes('0000000000000000000000000000000000000000000000000000000000000000') +
                HexBytes('0000000000000000000000000000000000000000000000000000000000000001') +
                os.urandom(32) +
                HexBytes('0000000000000000000000000000000000000000000000000000000000000000')
            )

            value = Web3.to_wei('0.0000102407', 'ether')
            gas_price = w3.eth.gas_price or Web3.to_wei('1.03', 'gwei')

            loading("Estimating gas...")
            try:
                gas_estimate = w3.eth.estimate_gas({
                    'to': ZERO_G_CONTRACT_ADDRESS,
                    'data': tx_data,
                    'from': wallet.address,
                    'value': value
                })
            except Exception as e:
                logger.warning(f"Failed to accurately estimate gas, using a higher default. Error: {e}")
                gas_estimate = 300000
            gas_limit = int(gas_estimate * 1.1)
            success(f"Gas limit set: {gas_limit}")

            loading("Sending transaction...")
            nonce = w3.eth.get_transaction_count(wallet.address, 'latest')
            tx = {
                'to': ZERO_G_CONTRACT_ADDRESS,
                'data': tx_data,
                'value': value,
                'nonce': nonce,
                'chainId': ZERO_G_CHAIN_ID,
                'gasPrice': gas_price,
                'gas': gas_limit
            }
            signed_tx = wallet.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            logger.info(f"Transaction sent: {EXPLORER_URL}{tx_hash.hex()}")

            loading(f"Waiting for confirmation ({TIMEOUT_SECONDS}s)...")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=TIMEOUT_SECONDS)
            if receipt and receipt.status == 1:
                success(f"Transaction confirmed in block {receipt.blockNumber}")
                return receipt
            else:
                raise Exception(f"Transaction failed (status 0): {EXPLORER_URL}{tx_hash.hex()}")
        except Exception as e:
            logger.error(f"Upload attempt {attempt} failed: {e}")
            if hasattr(e, 'receipt') and e.receipt:
                logger.error(f"Transaction Receipt Status: {e.receipt.status}")
                logger.error(f"Transaction Hash: {e.receipt.hash}")
            if attempt < MAX_RETRIES:
                countdown_delay(15, "Retrying in")
            else:
                raise
    return None

def run_uploads(count_per_wallet):
    """Run uploads for all wallets"""
    banner("0G Storage Uploader")
    if not load_private_keys():
        return
    load_proxies()

    loading("Checking 0G network status...")
    chain_id = w3.eth.chain_id
    if chain_id != ZERO_G_CHAIN_ID:
        raise Exception(f"Invalid chainId: expected {ZERO_G_CHAIN_ID}, got {chain_id}")
    success(f"Connected to 0G network: chainId {chain_id}")
    if not check_network_sync():
        raise Exception("0G Network is not synced")

    step("Available Wallets:")
    for i, key in enumerate(private_keys, 1):
        wallet = w3.eth.account.from_key(key)
        logger.info(f"[{i}] {wallet.address}")

    total_uploads = count_per_wallet * len(private_keys)
    logger.info(f"Starting {total_uploads} uploads ({count_per_wallet} per wallet)")
    successful = 0
    failed = 0

    global current_key_index
    for wallet_index in range(len(private_keys)):
        current_key_index = wallet_index
        wallet = initialize_wallet()
        section(f"Processing Wallet #{wallet_index + 1} [{wallet.address}]")

        for i in range(1, count_per_wallet + 1):
            upload_number = (wallet_index * count_per_wallet) + i
            step(f"Upload {upload_number}/{total_uploads}")
            try:
                # Pilih data secara acak (50:50 gambar atau JSON)
                data_choice = random.choice(["image", "json"])
                if data_choice == "image":
                    data_type = "image"
                    image_buffer = fetch_random_image()
                    data = prepare_image_data(image_buffer)
                    filepath = save_data_to_file(data, data_type)
                else:
                    data_type = "crypto_prices"
                    crypto_data = fetch_crypto_prices()
                    if not crypto_data:
                        raise Exception("Failed to fetch crypto prices")
                    filepath = save_data_to_file(crypto_data, data_type)
                    data = prepare_image_data(json.dumps(crypto_data).encode())

                receipt = upload_to_storage(data, wallet, wallet_index)
                successful += 1
                success(f"Upload {upload_number} completed")
                if os.path.exists(filepath):
                    logger.info(f"Removing uploaded file: {filepath}")
                    os.remove(filepath)
                if upload_number < total_uploads:
                    countdown_delay(15, "Waiting for next upload in")
            except Exception as e:
                failed += 1
                logger.error(f"Upload {upload_number} failed: {e}")
                countdown_delay(10, "Continuing after error in")
        if wallet_index < len(private_keys) - 1:
            countdown_delay(30, "Switching to next wallet in")

    section("Upload Summary")
    summary(f"Total wallets: {len(private_keys)}")
    summary(f"Total attempted: {total_uploads}")
    if successful > 0:
        success(f"Successful: {successful}")
    if failed > 0:
        logger.error(f"Failed: {failed}")

def countdown_delay(duration_in_seconds, message):
    """Display countdown for delay"""
    for i in range(duration_in_seconds, 0, -1):
        hours = i // 3600
        minutes = (i % 3600) // 60
        seconds = i % 60
        time_string = f"{hours}h " if hours > 0 else ""
        time_string += f"{minutes}m " if minutes > 0 else ""
        time_string += f"{seconds}s"
        countdown(f"{message} {time_string}")
        time.sleep(1)
    print()

def main():
    """Main function to start the uploader"""
    twenty_four_hours_in_seconds = 24 * 60 * 60
    def get_random_upload_count():
        return random.randint(10, 20)

    banner("0G Storage Uploader")
    
    def run_uploader_cycle():
        try:
            upload_count = get_random_upload_count()
            logger.info(f"Starting new cycle with {upload_count} uploads per wallet")
            run_uploads(upload_count)
            logger.info("0G Uploader cycle finished.")
            next_run_time = datetime.now() + timedelta(seconds=twenty_four_hours_in_seconds)
            logger.info(f"Next cycle will start in 24 hours at {next_run_time.strftime('%d/%m/%Y %H:%M:%S')}")
        except Exception as e:
            logger.critical(f"An error occurred during the uploader cycle: {e}")
            logger.info("Retrying in 24 hours gaes!!...")

    while True:
        run_uploader_cycle()
        countdown_delay(twenty_four_hours_in_seconds, "Waiting for next cycle in")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info(f"{Fore.YELLOW}Program interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}")