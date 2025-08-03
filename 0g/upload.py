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

LOG_FILE = "og_uploader.log"
MAX_LOG_SIZE = 2 * 1024 * 1024  # 2MB
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

def banner(msg=None):
    """Menampilkan banner dengan pesan opsional"""
    banner_text = f"""
{Fore.GREEN}============================ WELCOME TO Onchain DAPPs ============================{Fore.RESET}
{Fore.YELLOW}
 ██████╗██╗   ██║ █████╗ ███╗   ██╗███╗   ██╗ ██████╗ ██████╗ ███████╗
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
    print(banner_text)
    if msg:
        logger.info(f"{Fore.GREEN}{Style.BRIGHT}{msg}{Style.RESET_ALL}")

def section(msg=None):
    line = '─' * 40
    logger.info(f"\n{Fore.CYAN}{line}{Style.RESET_ALL}")
    if msg:
        logger.info(f"{Fore.WHITE}{Style.BRIGHT} {msg} {Style.RESET_ALL}")
    logger.info(f"{Fore.CYAN}{line}{Style.RESET_ALL}\n")

def success(msg):
    logger.info(f"{Fore.GREEN}[+] {msg}{Style.RESET_ALL}")

def loading(msg):
    logger.info(f"{Fore.MAGENTA}[*] {msg}{Style.RESET_ALL}")

def step(msg):
    logger.info(f"{Fore.CYAN}[>] {Style.BRIGHT}{msg}{Style.RESET_ALL}")

def summary(msg):
    logger.info(f"{Fore.YELLOW}{Style.BRIGHT}[SUMMARY] {msg}{Style.RESET_ALL}")

def wallet(msg):
    logger.info(f"{Fore.CYAN}[W] {msg}{Style.RESET_ALL}")

def countdown(msg):
    print(f"\r{Fore.YELLOW} [🧩] {msg}{Style.RESET_ALL}", end="")

def rotate_logs():
    """Rotasi file log untuk mencegah penggunaan disk berlebih"""
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
            logger.info("File log dirotasi")
    except Exception as e:
        logger.error(f"Error saat merotasi log: {e}")

def clean_old_data_files(days=1):
    """Membersihkan file data yang lebih lama dari jumlah hari tertentu"""
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
            logger.info(f"Membersihkan {count} file data lama (lebih dari {days} hari)")
    except Exception as e:
        logger.error(f"Error saat membersihkan file data lama: {e}")

# Konfigurasi
ZERO_G_CHAIN_ID = 16601
ZERO_G_RPC_URL = 'https://evmrpc-testnet.0g.ai'
ZERO_G_CONTRACT_ADDRESS = Web3.to_checksum_address('0xbD75117F80b4E22698D0Cd7612d92BDb8eaff628')
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
    """Memuat private key dari .env dan private_keys.txt"""
    global private_keys
    private_keys = []
    
    # Memuat dari .env
    index = 1
    while True:
        key = os.getenv(f"PRIVATE_KEY_{index}")
        if not key:
            break
        if is_valid_private_key(key):
            private_keys.append(key)
        else:
            logger.error(f"Format private key tidak valid pada PRIVATE_KEY_{index}")
        index += 1
    
    # Memuat dari private_keys.txt
    try:
        with open("private_keys.txt", "r") as file:
            keys = [line.strip() for line in file.readlines() if line.strip()]
            for key in keys:
                if is_valid_private_key(key):
                    private_keys.append(key)
                else:
                    logger.error(f"Format private key tidak valid di private_keys.txt: {key}")
    except Exception as e:
        logger.warning(f"Catatan: private_keys.txt tidak ditemukan atau tidak dapat dibaca: {e}")

    private_keys = list(set(private_keys))
    if not private_keys:
        logger.critical("Tidak ada private key valid yang ditemukan di .env atau private_keys.txt")
        return False
    
    success(f"Memuat {len(private_keys)} private key")
    return True

def is_valid_private_key(key):
    """Memvalidasi format private key"""
    key = key.strip()
    if not key.startswith('0x'):
        key = '0x' + key
    try:
        bytes_key = bytes.fromhex(key.replace('0x', ''))
        return len(key) == 66 and len(bytes_key) == 32
    except:
        return False

def get_next_private_key():
    """Mengambil private key berikutnya"""
    global current_key_index
    return private_keys[current_key_index]

def load_proxies():
    """Memuat proxy dari proxies.txt"""
    global proxies, current_proxy_index
    try:
        if os.path.exists(PROXY_FILE):
            with open(PROXY_FILE, 'r') as file:
                proxies = [line.strip() for line in file.readlines() if line.strip() and not line.startswith('#')]
            if proxies:
                success(f"Memuat {len(proxies)} proxy")
            else:
                logger.warning(f"Tidak ada proxy ditemukan di {PROXY_FILE}")
        else:
            logger.warning(f"File proxy {PROXY_FILE} tidak ditemukan")
    except Exception as e:
        logger.error(f"Gagal memuat proxy: {e}")
    current_proxy_index = 0

def get_next_proxy():
    """Mengambil proxy berikutnya"""
    global current_proxy_index
    if not proxies:
        return None
    proxy = proxies[current_proxy_index]
    current_proxy_index = (current_proxy_index + 1) % len(proxies)
    return proxy

def create_session():
    """Membuat sesi requests dengan proxy dan header"""
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
    """Inisialisasi wallet dengan private key saat ini"""
    private_key = get_next_private_key()
    return w3.eth.account.from_key(private_key)

def check_network_sync():
    """Memeriksa apakah jaringan 0G sudah tersinkronisasi"""
    try:
        loading("Memeriksa sinkronisasi jaringan 0G...")
        block_number = w3.eth.block_number
        logger.info(f"Sinkronsi Jaringan 0G pada blok no {Fore.YELLOW}{block_number}{Fore.RESET}")
        return True
    except Exception as e:
        logger.error(f"Pemeriksaan sinkronisasi jaringan 0G gagal: {e}")
        return False

def fetch_random_image():
    """Mengambil gambar acak dari sumber yang ditentukan"""
    for source in IMAGE_SOURCES:
        try:
            logger.info(f"{Fore.YELLOW}Mengambil gambar 🖼️  dari sumber {source['url']}{Fore.RESET}")
            session = create_session()
            # logger.info(f"Header permintaan: {session.headers}")
            # logger.info(f"Proxy yang digunakan: {session.proxies}")
            response = session.get(source['url'], timeout=20)
            response.raise_for_status()
            success("Random gambar 📸 berhasil diambil")
            return response.content
        except Exception as e:
            logger.error(f"Error saat mengambil gambar 🖼️ dari {source['url']}: {e}")
            if source != IMAGE_SOURCES[-1]:
                logger.info("Mencoba sumber gambar berikutnya...")
            else:
                raise Exception(f"Gagal mengambil gambar dari semua sumber (terakhir: {source['url']}): {e}. Periksa proxy atau koneksi.")

def check_file_exists(file_hash):
    """Memeriksa apakah hash file sudah ada di indexer"""
    try:
        loading(f"Memeriksa root hash (merkle tree) {file_hash}...")
        session = create_session()
        response = session.get(f"{INDEXER_URL}/file/info/{file_hash}", timeout=20)
        return response.json().get('exists', False)
    except Exception as e:
        logger.warning(f"Gagal memeriksa root hash (merkle tree): {e}")
        return False

def prepare_image_data(image_buffer):
    """Menyiapkan data gambar dengan hash unik"""
    MAX_HASH_ATTEMPTS = 5
    for attempt in range(1, MAX_HASH_ATTEMPTS + 1):
        hash_input = image_buffer + os.urandom(16)
        hash_obj = hashlib.sha256(hash_input)
        file_hash = '0x' + hash_obj.hexdigest()
        if not check_file_exists(file_hash):
            success(f"Menghasilkan root hash file unik {file_hash}...")
            return {'root': file_hash, 'data': image_buffer.hex()}
        logger.warning(f"Root Hash {file_hash} sudah ada, mencoba lagi...")
    raise Exception(f"Gagal menghasilkan hash unik setelah {MAX_HASH_ATTEMPTS} percobaan")

def fetch_crypto_prices():
    """Mengambil data harga kripto dari CoinGecko"""
    api_key = os.getenv("COINGECKO_API_KEY")
    if not api_key:
        logger.warning("Tidak ada kunci API CoinGecko, melewati pengambilan harga kripto")
        return None
    try:
        logger.info(f"{Fore.YELLOW}Mengambil JSON data ₿itcoin 🚀 prices dari CoinGecko{Fore.RESET}")
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
        response = session.get(url, headers=headers, params=params, timeout=20)
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
        logger.error(f"Error saat mengambil data harga kripto: {e}")
        return None

def save_data_to_file(data, source_name):
    """Menyimpan data ke file di direktori data_files"""
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
    logger.info(f"Menyimpan data {source_name} ke {filepath} ({file_size_kb:.2f}KB)")
    return filepath

def upload_to_storage(data, wallet, wallet_index):
    """Mengunggah data ke penyimpanan dan mengirim ke kontrak"""
    MAX_RETRIES = 5
    TIMEOUT_SECONDS = 101
    logger.info(f"Memeriksa saldo wallet untuk {wallet.address}...")
    balance = w3.eth.get_balance(wallet.address)
    if balance < Web3.to_wei(0.0015, 'ether'):
        raise Exception(f"Saldo tidak cukup: {Web3.from_wei(balance, 'ether')} OG")
    logger.info(f"{Fore.YELLOW}Saldo wallet: {Web3.from_wei(balance, 'ether')} OG{Fore.RESET}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            loading(f"Mengunggah file untuk wallet #{wallet_index + 1} -> Percobaan ke {attempt}...")
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
                timeout=20
            )
            response.raise_for_status()
            success("Segmen root hash file berhasil di upload...")

            # Data transaksi
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

            value = Web3.to_wei('0.000010001', 'ether')
            gas_price = w3.eth.gas_price or Web3.to_wei('1.033', 'gwei')

            loading("get estimasi gas bang...")
            try:
                gas_estimate = w3.eth.estimate_gas({
                    'to': ZERO_G_CONTRACT_ADDRESS,
                    'data': tx_data,
                    'from': wallet.address,
                    'value': value
                })
            except Exception as e:
                logger.warning(f"Gagal memperkirakan gas dengan akurat, menggunakan default lebih tinggi. Error: {e}")
                gas_estimate = 300003
            gas_limit = int(gas_estimate * 1.1)
            success(f"Batas limit gas tersedia: {gas_limit}")

            loading("Mengirim transaksi...")
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
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            logger.info(f"Transaksi terkirim: {EXPLORER_URL}{tx_hash.hex()}")

            loading(f"{Fore.YELLOW}Menunggu konfirmasi {TIMEOUT_SECONDS} detik...{Fore.RESET}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=TIMEOUT_SECONDS)
            if receipt and receipt.status == 1:
                success(f"Transaksi dikonfirmasi pada blok {receipt.blockNumber}")
                return receipt
            else:
                raise Exception(f"Transaksi gagal (status 0): {EXPLORER_URL}{tx_hash.hex()}")
        except Exception as e:
            logger.error(f"Percobaan upload {attempt} gagal: {e}")
            if hasattr(e, 'receipt') and e.receipt:
                logger.error(f"Status Receipt Transaksi: {e.receipt.status}")
                logger.error(f"Hash Transaksi: {e.receipt.transactionHash.hex()}")
            if attempt < MAX_RETRIES:
                countdown_delay(15, "Mencoba lagi dalam")
            else:
                raise
    return None

def run_uploads(count_per_wallet):
    """Menjalankan upload untuk semua wallet"""
    banner("0G Storage Uploader")
    if not load_private_keys():
        return
    load_proxies()

    loading("Memeriksa status jaringan 0G...")
    chain_id = w3.eth.chain_id
    if chain_id != ZERO_G_CHAIN_ID:
        raise Exception(f"chainId tidak valid: diharapkan {ZERO_G_CHAIN_ID}, mendapatkan {chain_id}")
    logger.info(f"Terhubung ke jaringan 0G: chainId {chain_id}")
    if not check_network_sync():
        raise Exception("Jaringan 0G tidak tersinkronisasi")

    step("Wallet yang Tersedia:")
    for i, key in enumerate(private_keys, 1):
        wallet = w3.eth.account.from_key(key)
        logger.info(f"[{i}] {wallet.address}")

    total_uploads = count_per_wallet * len(private_keys)
    logger.info(f"Memulai {total_uploads} upload ({count_per_wallet} per wallet)")
    successful = 0
    failed = 0

    global current_key_index
    for wallet_index in range(len(private_keys)):
        current_key_index = wallet_index
        wallet = initialize_wallet()
        section(f"Memproses Wallet {Fore.MAGENTA}#{wallet_index + 1} [{wallet.address}]{Fore.RESET}")

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
                        raise Exception("Gagal mengambil harga kripto")
                    filepath = save_data_to_file(crypto_data, data_type)
                    data = prepare_image_data(json.dumps(crypto_data).encode())

                receipt = upload_to_storage(data, wallet, wallet_index)
                successful += 1
                success(f"Upload file {upload_number} selesai")
                if os.path.exists(filepath):
                    logger.info(f"Menghapus file yang diunggah: {filepath}")
                    os.remove(filepath)
                if upload_number < total_uploads:
                    countdown_delay(300, "Menunggu upload berikutnya dalam")  # Jeda 5 menit
            except Exception as e:
                failed += 1
                logger.error(f"Upload {upload_number} gagal: {e}")
                countdown_delay(300, "Melanjutkan setelah error dalam")  # Jeda 5 menit
        if wallet_index < len(private_keys) - 1:
            countdown_delay(300, "Beralih ke wallet berikutnya dalam")  # Jeda 5 menit

    section("Ringkasan upload")
    summary(f"Total wallet: {len(private_keys)}")
    summary(f"Total mencoba: {total_uploads}")
    if successful > 0:
        success(f"Berhasil: {successful}")
    if failed > 0:
        logger.error(f"Gagal: {failed}")

def countdown_delay(duration_in_seconds, message):
    """Menampilkan hitungan mundur untuk jeda"""
    for i in range(duration_in_seconds, 0, -1):
        hours = i // 3600
        minutes = (i % 3600) // 60
        seconds = i % 60
        time_string = f"{hours}j " if hours > 0 else ""
        time_string += f"{minutes}m " if minutes > 0 else ""
        time_string += f"{seconds}d"
        countdown(f"{message} {time_string}")
        time.sleep(1)
    print()

def main():
    """Fungsi utama untuk memulai uploader"""
    twenty_four_hours_in_seconds = 24 * 60 * 60
    def get_random_upload_count():
        return random.randint(10, 25)  # random upload per wallet

    while True:
        try:
            upload_count = get_random_upload_count()
            logger.info(f"Memulai siklus baru dengan {upload_count} upload per wallet")
            run_uploads(upload_count)
            logger.info("Siklus uploader 0G selesai.")
            next_run_time = datetime.now() + timedelta(seconds=twenty_four_hours_in_seconds)
            logger.info(f"Siklus berikutnya akan dimulai pada {next_run_time.strftime('%d/%m/%Y %H:%M:%S')}")
            countdown_delay(twenty_four_hours_in_seconds, "Menunggu siklus berikutnya dalam")
        except Exception as e:
            logger.critical(f"Terjadi error selama siklus uploader: {e}")
            countdown_delay(300, "Mencoba lagi setelah error dalam")  # Jeda 5 menit sebelum coba lagi

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info(f"{Fore.YELLOW}Program dihentikan run dengan pm2 bang{Style.RESET_ALL}")
    except Exception as e:
        logger.critical(f"Terjadi error gilak: {e}")