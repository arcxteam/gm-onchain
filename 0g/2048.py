import os
import random
import time
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
# from web3.middleware import geth_poa_middleware
from eth_account import Account
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

# =================== Konfigurasi ==================== #
RPC_URLS = [
    "https://evmrpc-testnet.0g.ai",
    "https://0g-testnet-rpc.astrostake.xyz",
    "https://0g-evm.zstake.xyz",
    "https://lightnode-json-rpc-0g.grandvalleys.com",
    "https://0g-evm.maouam.nodelab.my.id",
    "https://0g-galileo.shachopra.com",
    "https://evmrpc.vinnodes.com",
    "https://evm-0gchaind.onenov.xyz",
    "https://evmrpc-0g-testnet.unitynodes.app",
    "https://0g-galileo-evmrpc2.corenodehq.xyz",
    "https://0g-evmrpc-galileo.komado.xyz",
    "https://0g.json-rpc.cryptomolot.com",
    "https://0g.bangcode.id"
]
GAS_LIMIT_RANGE = (100000, 3000000)
GWEI_RANGE = (0.05, 2.0)
CONTRACT_ADDRESS = Web3.to_checksum_address("0xdF0d5abC614EF45C4bCEA121624644523BAc80b7")
WALLET_DELAY_RANGE = (80, 200)  # Delay antar wallet
GAME_CYCLE_DELAY_RANGE = (150, 420)  # Delay game over
GAME_MODE = "off-chain"  # mode bisa pilih "on-chain" atau "off-chain"
GAME_STEPS_RANGE = (70, 250)  # Jumlah step per game max2000 bang
USE_EIP1559 = True  # False (gas legacy)
CHAIN_ID = 16601
TIMEOUT = 300

# ABI untuk Game2048 (author @0xgrey)
CONTRACT_ABI = [
    {"inputs": [], "stateMutability": "nonpayable", "type": "constructor"},
    {"inputs": [], "name": "GameAlreadyEnded", "type": "error"},
    {"inputs": [], "name": "GameBoardInvalid", "type": "error"},
    {"inputs": [], "name": "GameIdUsed", "type": "error"},
    {"inputs": [], "name": "GameNotOver", "type": "error"},
    {"inputs": [], "name": "GamePlayed", "type": "error"},
    {"inputs": [], "name": "GamePlayerInvalid", "type": "error"},
    {"inputs": [], "name": "InvalidMoveCount", "type": "error"},
    {"inputs": [], "name": "ModeNotSet", "type": "error"},
    {"inputs": [], "name": "NoNFTToClaim", "type": "error"},
    {"inputs": [], "name": "NotApproved", "type": "error"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "owner", "type": "address"}, {"indexed": True, "internalType": "address", "name": "approved", "type": "address"}, {"indexed": True, "internalType": "uint256", "name": "tokenId", "type": "uint256"}], "name": "Approval", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "owner", "type": "address"}, {"indexed": True, "internalType": "address", "name": "operator", "type": "address"}, {"indexed": False, "internalType": "bool", "name": "approved", "type": "bool"}], "name": "ApprovalForAll", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": False, "internalType": "uint256", "name": "_fromTokenId", "type": "uint256"}, {"indexed": False, "internalType": "uint256", "name": "_toTokenId", "type": "uint256"}], "name": "BatchMetadataUpdate", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "player", "type": "address"}, {"indexed": True, "internalType": "bytes32", "name": "gameId", "type": "bytes32"}, {"indexed": False, "internalType": "uint8[]", "name": "moves", "type": "uint8[]"}, {"indexed": False, "internalType": "uint128[]", "name": "resultBoards", "type": "uint128[]"}], "name": "BatchMoves", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "player", "type": "address"}, {"indexed": True, "internalType": "bytes32", "name": "id", "type": "bytes32"}, {"indexed": False, "internalType": "uint256", "name": "highestTile", "type": "uint256"}, {"indexed": False, "internalType": "uint256", "name": "moves", "type": "uint256"}], "name": "GameOver", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": False, "internalType": "uint256", "name": "_tokenId", "type": "uint256"}], "name": "MetadataUpdate", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "player", "type": "address"}, {"indexed": False, "internalType": "bool", "name": "isOnchain", "type": "bool"}], "name": "ModeSelected", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "player", "type": "address"}, {"indexed": True, "internalType": "bytes32", "name": "gameId", "type": "bytes32"}, {"indexed": False, "internalType": "uint256", "name": "tokenId", "type": "uint256"}, {"indexed": False, "internalType": "uint256", "name": "level", "type": "uint256"}], "name": "NFTMinted", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "player", "type": "address"}, {"indexed": True, "internalType": "bytes32", "name": "id", "type": "bytes32"}, {"indexed": False, "internalType": "uint256", "name": "board", "type": "uint256"}], "name": "NewGame", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "player", "type": "address"}, {"indexed": True, "internalType": "bytes32", "name": "id", "type": "bytes32"}, {"indexed": False, "internalType": "uint256", "name": "move", "type": "uint256"}, {"indexed": False, "internalType": "uint256", "name": "result", "type": "uint256"}], "name": "NewMove", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "previousOwner", "type": "address"}, {"indexed": True, "internalType": "address", "name": "newOwner", "type": "address"}], "name": "OwnershipTransferred", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "bytes32", "name": "gameId", "type": "bytes32"}], "name": "PendingNFTCleared", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "from", "type": "address"}, {"indexed": True, "internalType": "address", "name": "to", "type": "address"}, {"indexed": True, "internalType": "uint256", "name": "tokenId", "type": "uint256"}], "name": "Transfer", "type": "event"},
    {"inputs": [], "name": "CLAIM_PERIOD", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "MAX_SUPPLY", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "tokenId", "type": "uint256"}], "name": "approve", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "approvePlayer", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "", "type": "address"}], "name": "approvedPlayers", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "gameId", "type": "bytes32"}], "name": "claimNFT", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "gameId", "type": "bytes32"}], "name": "clearExpiredNFT", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "gameId", "type": "bytes32"}], "name": "endGame", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "name": "endGameTimestamps", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "name": "gameHashOf", "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "name": "games", "outputs": [{"internalType": "address", "name": "player", "type": "address"}, {"internalType": "uint128", "name": "board", "type": "uint128"}, {"internalType": "uint8", "name": "lastMove", "type": "uint8"}, {"internalType": "uint120", "name": "moveCount", "type": "uint120"}, {"internalType": "bool", "name": "isActive", "type": "bool"}, {"internalType": "uint256", "name": "highestTile", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}], "name": "getApproved", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "gameId", "type": "bytes32"}], "name": "getBoard", "outputs": [{"internalType": "uint8[16]", "name": "boardArr", "type": "uint8[16]"}, {"internalType": "uint256", "name": "nextMoveNumber_", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "level", "type": "uint256"}], "name": "getDescription", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getLeaderboard", "outputs": [{"components": [{"internalType": "address", "name": "player", "type": "address"}, {"internalType": "uint256", "name": "highestTile", "type": "uint256"}, {"internalType": "uint120", "name": "moves", "type": "uint120"}], "internalType": "struct Game2048.LeaderboardEntry[]", "name": "", "type": "tuple[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "player", "type": "address"}], "name": "getPlayerPoints", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "", "type": "address"}], "name": "hasSelectedMode", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "owner", "type": "address"}, {"internalType": "address", "name": "operator", "type": "address"}], "name": "isApprovedForAll", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "gameId", "type": "bytes32"}], "name": "latestBoard", "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "name": "leaderboard", "outputs": [{"internalType": "address", "name": "player", "type": "address"}, {"internalType": "uint256", "name": "highestTile", "type": "uint256"}, {"internalType": "uint120", "name": "moves", "type": "uint120"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "leaderboardSize", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "name": "levelToDescription", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "name": "levelToURI", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "name", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "gameId", "type": "bytes32"}], "name": "nextMove", "outputs": [{"internalType": "uint120", "name": "", "type": "uint120"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "name": "nextMoveNumber", "outputs": [{"internalType": "uint120", "name": "", "type": "uint120"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "owner", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}], "name": "ownerOf", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "name": "pendingNFTs", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "gameId", "type": "bytes32"}, {"internalType": "uint8", "name": "move", "type": "uint8"}, {"internalType": "uint128", "name": "resultBoard", "type": "uint128"}], "name": "play", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "", "type": "address"}], "name": "playerMode", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "", "type": "address"}], "name": "playerPoints", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "renounceOwnership", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "from", "type": "address"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "tokenId", "type": "uint256"}], "name": "safeTransferFrom", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "from", "type": "address"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "tokenId", "type": "uint256"}, {"internalType": "bytes", "name": "data", "type": "bytes"}], "name": "safeTransferFrom", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bool", "name": "isOnchain", "type": "bool"}], "name": "selectMode", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "operator", "type": "address"}, {"internalType": "bool", "name": "approved", "type": "bool"}], "name": "setApprovalForAll", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "gameId", "type": "bytes32"}, {"internalType": "uint128[4]", "name": "boards", "type": "uint128[4]"}, {"internalType": "uint8[3]", "name": "", "type": "uint8[3]"}], "name": "startGame", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "gameId", "type": "bytes32"}], "name": "state", "outputs": [{"internalType": "uint8", "name": "move", "type": "uint8"}, {"internalType": "uint120", "name": "nextMove_", "type": "uint120"}, {"internalType": "uint128", "name": "board", "type": "uint128"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "gameId", "type": "bytes32"}, {"internalType": "uint8[]", "name": "moves", "type": "uint8[]"}, {"internalType": "uint128[]", "name": "resultBoards", "type": "uint128[]"}], "name": "submitBatchMoves", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes4", "name": "interfaceId", "type": "bytes4"}], "name": "supportsInterface", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}], "name": "tokenURI", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalMinted", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "from", "type": "address"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "tokenId", "type": "uint256"}], "name": "transferFrom", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "newOwner", "type": "address"}], "name": "transferOwnership", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "level", "type": "uint256"}, {"internalType": "string", "name": "uri", "type": "string"}], "name": "updateLevelURI", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
]

class Logger:
    @staticmethod
    def info(message):
        print(f"[INFO] {message}")

    @staticmethod
    def success(message):
        print(f"{Fore.GREEN}[SUCCESS]{Fore.RESET} {message}")

    @staticmethod
    def error(message):
        print(f"{Fore.RED}[ERROR]{Fore.RESET} {message}")

    @staticmethod
    def warning(message):
        print(f"{Fore.MAGENTA}[2048GAME]{Fore.RESET} {message}")
        
    @staticmethod
    def gas_report(message):
        print(f"{Fore.YELLOW}[REPORT]{Fore.RESET} {message}")

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
{Fore.CYAN}    Welcome to Game 2048 & Reward NFTs on Testnet - Mainnet     {Fore.RESET}
{Fore.YELLOW}        🧩 Code. Greyscope&Co, Author. Arcxteam 🧩   {Fore.RESET}
{Fore.GREEN}=========================================================================={Fore.RESET}
"""
    print(banner)

def load_private_keys():
    load_dotenv()
    keys = []
    
    if os.getenv("PRIVATE_KEY"):
        keys.append(os.getenv("PRIVATE_KEY"))
    
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
        base_fee = latest_block.get('baseFeePerGas', w3.to_wei(0.5, 'gwei'))
        priority_fee = w3.eth.max_priority_fee
        max_fee = int(base_fee * 1.3) + priority_fee  # Margin lebih besar (30%)
        return {
            'maxFeePerGas': max_fee,
            'maxPriorityFeePerGas': priority_fee
        }
    except Exception as e:
        Logger.error(f"Failed to get EIP-1559 gas params: {str(e)}")
        priority_fee = w3.to_wei(random.uniform(*GWEI_RANGE), 'gwei')
        return {
            'maxFeePerGas': w3.to_wei(random.uniform(*GWEI_RANGE) * 2, 'gwei'),
            'maxPriorityFeePerGas': priority_fee
        }

def get_legacy_gas_price(w3):
    try:
        current_gas = w3.eth.gas_price
        current_gwei = w3.from_wei(current_gas, 'gwei')
        if current_gwei > 0:
            return {'gasPrice': current_gas}
        else:
            target_gwei = random.uniform(*GWEI_RANGE)
            return {'gasPrice': w3.to_wei(target_gwei, 'gwei')}
    except Exception as e:
        Logger.error(f"Failed to get gas price: {str(e)}")
        return {'gasPrice': w3.to_wei(random.uniform(*GWEI_RANGE), 'gwei')}

def generate_game_id(player_address):
    addr = player_address[2:] if player_address.startswith('0x') else player_address
    addr_bytes = bytes.fromhex(addr)

    # Buat 32 byte gameId
    # Byte 0-11 (12 byte pertama): acak
    # Byte 12-31 (20 byte terakhir): alamat pemain
    nonce = random.randint(0, 2**96-1).to_bytes(12, byteorder='big')  # 12 byte acak
    game_id_bytes = nonce + addr_bytes  # 12 byte + 20 byte = 32 byte

    # Konversi ke format bytes32
    game_id = Web3.to_bytes(hexstr=game_id_bytes.hex())
    
    # Debug: Cetak gameId dan periksa apakah alamatnya sesuai
    game_id_hex = game_id.hex()
    addr_part = game_id_hex[-40:]
    Logger.info(f"Generated gameId: 0x{game_id_hex}")
    Logger.info(f"{Fore.GREEN}Player address: 0x{addr}{Fore.RESET}")
    Logger.info(f"Address part in gameId (last 20 bytes): 0x{addr_part}")
    
    return game_id

def generate_initial_boards():
    # Papan awal 2048: hanya 2 ubin acak (nilai log2: 1 atau 2 untuk 2 atau 4)
    board = 0
    for _ in range(2):  # 2 ubin awal
        pos = random.randint(0, 15)
        value = random.choice([1, 2])  # 2 atau 4
        board = set_tile(board, pos, value)
    initial_boards = [board] + [random.randint(0, 2**128-1) for _ in range(3)]  # Placeholder untuk 3 langkah
    return initial_boards

def generate_initial_moves():
    return [random.randint(0, 3) for _ in range(3)]  # 0=up, 1=right, 2=down, 3=left

def set_tile(board, pos, value):
    # Set tile di posisi tertentu (simulasi sederhana)
    return (board & ~(0xF << (pos * 4))) | (value << (pos * 4))

def get_tile(board, pos):
    # Ambil nilai tile di posisi tertentu (simulasi sederhana)
    return (board >> (pos * 4)) & 0xF

def slide_board(board, direction):
    # Logika sederhana untuk menggeser papan 2048
    grid = [get_tile(board, i) for i in range(16)]
    if direction == 0:  # Up
        for j in range(4):
            column = [grid[j + i * 4] for i in range(4)]
            column = merge_left(column)
            for i in range(4):
                grid[j + i * 4] = column[i]
    elif direction == 1:  # Right
        for i in range(4):
            row = grid[i * 4:(i + 1) * 4][::-1]
            row = merge_left(row)[::-1]
            grid[i * 4:(i + 1) * 4] = row
    elif direction == 2:  # Down
        for j in range(4):
            column = [grid[j + i * 4] for i in range(3, -1, -1)]
            column = merge_left(column)
            for i in range(4):
                grid[j + (3 - i) * 4] = column[i]
    elif direction == 3:  # Left
        for i in range(4):
            row = grid[i * 4:(i + 1) * 4]
            row = merge_left(row)
            grid[i * 4:(i + 1) * 4] = row
    
    new_board = 0
    for i in range(16):
        new_board = set_tile(new_board, i, grid[i])
    return new_board

def merge_left(row):
    # Menggabungkan ubin ke kiri (logika sederhana 2048)
    new_row = [x for x in row if x > 0]
    for i in range(len(new_row) - 1):
        if new_row[i] == new_row[i + 1] and new_row[i] > 0:
            new_row[i] = new_row[i] + 1
            new_row[i + 1] = 0
    new_row = [x for x in new_row if x > 0]
    while len(new_row) < 4:
        new_row.append(0)
    return new_row

def generate_next_move_and_result(board):
    # Prioritaskan gerakan: Kiri → Atas → Kanan → Bawah
    moves_priority = [3, 0, 1, 2]
    for move in moves_priority:
        new_board = slide_board(board, move)
        if new_board != board:  # Jika gerakan menghasilkan perubahan
            return move, new_board
    # Jika tidak ada gerakan valid, return move dummy (biar game over)
    return moves_priority[0], board

def check_game_over(board):
    # Cek apakah masih ada gerakan valid di papan
    # 1. Cek apakah ada ubin yang sama bersebelahan (horizontal atau vertikal)
    # 2. Cek apakah ada slot kosong (nilai 0)
    grid = [get_tile(board, i) for i in range(16)]
    
    # Cek slot kosong
    if 0 in grid:
        return False
    
    # Cek horizontal (baris)
    for i in range(4):
        row = grid[i * 4:(i + 1) * 4]
        for j in range(3):
            if row[j] == row[j + 1] and row[j] != 0:
                return False
    
    # Cek vertikal (kolom)
    for j in range(4):
        column = [grid[j + i * 4] for i in range(4)]
        for i in range(3):
            if column[i] == column[i + 1] and column[i] != 0:
                return False
    
    return True  # Tidak ada gerakan valid, game selesai

class Game2048:
    def __init__(self):
        self.w3 = self.connect_rpc()
        self.private_keys = load_private_keys()
        if not self.private_keys:
            raise ValueError("No valid private keys found. Please check your wallet keys.")
        
        self.current_key_index = 0
        self.batch_count = 1
        self.transaction_count = 1
        self.use_eip1559 = USE_EIP1559
        self.wallet_cycle_complete = False
        self.total_gas_used = 0
        
        self.contract = self.w3.eth.contract(
            address=CONTRACT_ADDRESS,
            abi=CONTRACT_ABI
        )
        
        Logger.info(f"{Fore.YELLOW}🎮 2048 GAME WITH NFT MINTED{Fore.RESET} - {Fore.MAGENTA}ONCHAIN TESTNET 🎮 {Fore.RESET}")
        self.game_steps = random.randint(*GAME_STEPS_RANGE)
        Logger.info(f" 🧵 Initial game with {Fore.YELLOW}#{self.game_steps}{Fore.RESET} steps")
        gas_type = "EIP-1559" if self.use_eip1559 else "Legacy"
        Logger.info(f" ⛽️ Using {gas_type} {Fore.MAGENTA}gas{Fore.RESET} pricing")
        Logger.info(f" 👛 Will rotate through {Fore.GREEN}{len(self.private_keys)}{Fore.RESET} wallets before random long delay")

    def connect_rpc(self):
        while True:
            for url in RPC_URLS:
                try:
                    w3 = Web3(Web3.HTTPProvider(url))
                    if w3.is_connected():
                        Logger.info(f" 📶 Yes..Connected to RPC: {Fore.MAGENTA}{url}")
                        if hasattr(self, 'contract'):
                            self.contract = w3.eth.contract(
                                address=CONTRACT_ADDRESS,
                                abi=CONTRACT_ABI
                            )
                        return w3
                except Exception as e:
                    Logger.error(f"🆙 Failed to connect RPC: {url}: {str(e)}")
            
            Logger.warning("🔁 Retrying RPC connection in 20 seconds...")
            time.sleep(20)

    def switch_wallet(self):
        old_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.private_keys)
        
        if self.current_key_index == 0 and old_index != 0:
            self.wallet_cycle_complete = True
            Logger.warning(f"{Fore.MAGENTA} 🔄 Completed full wallet rotation cycle! All {len(self.private_keys)} wallets used.{Fore.RESET}")
        else:
            self.wallet_cycle_complete = False
            
        Logger.info(f"{Fore.MAGENTA} 🔂 Switched to other EVM wallet{Fore.RESET} {Fore.YELLOW}#{self.current_key_index + 1}{Fore.RESET}")
        current_address = Account.from_key(self.private_keys[self.current_key_index]).address
        truncated_address = f"{current_address[:6]}...{current_address[-4:]}"
        Logger.info(f" 💲 Current wallet address: {Fore.MAGENTA}{truncated_address}{Fore.RESET}")
        
        # Delay antar wallet
        wallet_delay = random.randint(*WALLET_DELAY_RANGE)
        Logger.warning(f" 🔁 Wallet delay for {Fore.YELLOW}{wallet_delay}{Fore.RESET} seconds")
        time.sleep(wallet_delay)
        
        return self.wallet_cycle_complete

    def calculate_gas_cost(self, receipt, gas_price=None, max_fee_per_gas=None, max_priority_fee_per_gas=None):
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

    def retry_transaction(self, build_tx_func, priv_key, max_retries=10, delay=25):
        """
        Fungsi untuk mencoba ulang transaksi hingga max_retries kali.
        Menggunakan nonce dari tx_params dengan opsi cadangan jika gagal.
        """
        account = self.w3.eth.account.from_key(priv_key)
        for attempt in range(max_retries):
            try:
                tx = build_tx_func()
                if 'nonce' not in tx:
                    raise ValueError("Nonce not provided in tx_params")
                signed_tx = account.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                Logger.info(f" 🧵 Transaction sent: {tx_hash.hex()} {Fore.YELLOW}(Attempt {attempt + 1}/{max_retries}){Fore.RESET}")
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=TIMEOUT)
                if receipt.status == 1:
                    return tx_hash, receipt
                else:
                    Logger.error(f" ↪️ Transaction reverted: {tx_hash.hex()} {Fore.YELLOW}(Attempt {attempt + 1}/{max_retries}){Fore.RESET}")
                    if attempt < max_retries - 1:
                        Logger.warning(f"🔁 Retrying transaction in {delay} seconds...")
                        time.sleep(delay)
                    continue
            except Exception as e:
                Logger.error(f"Transaction failed: {str(e)} (Attempt {attempt + 1}/{max_retries})")
                # Opsi cadangan: Jika error "nonce too low" atau masalah lain, ambil nonce terbaru secara manual
                if "nonce too low" in str(e).lower() or "missing kwargs" in str(e).lower():
                    Logger.warning(f"🔁 {Fore.YELLOW}Nonce issue detected. Switching to manual nonce management...{Fore.RESET}")
                    try:
                        nonce = self.w3.eth.get_transaction_count(account.address, 'pending')
                        Logger.info(f"🔁 {Fore.GREEN}Updated nonce to {nonce}{Fore.RESET}")
                        # Bangun ulang transaksi dengan nonce manual
                        tx = build_tx_func()
                        tx['nonce'] = nonce  # Pastikan nonce diperbarui
                        signed_tx = self.w3.eth.account.sign_transaction(tx, priv_key)
                        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                        Logger.info(f" 🧵 Transaction sent with manual nonce: {tx_hash.hex()} {Fore.YELLOW}(Attempt {attempt + 1}/{max_retries}){Fore.RESET}")
                        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=TIMEOUT)
                        if receipt.status == 1:
                            return tx_hash, receipt
                        else:
                            Logger.error(f" ↪️ Transaction reverted: {tx_hash.hex()} {Fore.YELLOW}(Attempt {attempt + 1}/{max_retries}){Fore.RESET}")
                    except Exception as e2:
                        Logger.error(f"Manual nonce retry failed: {str(e2)}")
                # Tangani error lain seperti timeout atau koneksi
                elif "timeout" in str(e).lower() or "connection" in str(e).lower():
                    Logger.warning("🔁 RPC might be disconnected. Switching to another RPC...")
                    self.w3 = self.connect_rpc()
                if attempt < max_retries - 1:
                    Logger.warning(f"🔁 Retrying transaction in {delay} seconds...")
                    time.sleep(delay)
                continue
        Logger.error(f" ↪️ Transaction failed after {max_retries} attempts.")
        return None, None
    
    def execute_game_interaction(self):
        try:
            priv_key = self.private_keys[self.current_key_index]
            account = Account.from_key(priv_key)
            player_address = account.address

            balance_before = get_wallet_balance(self.w3, player_address)
            Logger.info(f" 🤑 [Game {self.batch_count}] Checking wallet balance: {Fore.YELLOW}{balance_before:.6f} 0G{Fore.RESET}")

            if balance_before < 0.001:
                Logger.warning(f" 🤣 Low balance detected --> {Fore.YELLOW}{balance_before:.6f} 0G{Fore.RESET} Consider adding funds.")
                if balance_before < 0.0005:
                    Logger.error(f" 🤣 Insufficient balance isi bang gas. Switching wallet.")
                    self.switch_wallet()
                    return False

            # Ambil nonce terbaru sebelum transaksi pertama
            nonce = self.w3.eth.get_transaction_count(player_address, 'pending')
            gas_limit = random.randint(*GAS_LIMIT_RANGE)
            gas_params = get_eip1559_gas_params(self.w3) if self.use_eip1559 else get_legacy_gas_price(self.w3)
            tx_params = {
                'chainId': CHAIN_ID,
                'gas': gas_limit,
                'nonce': nonce,
                'value': 0,
                'from': player_address
            }
            tx_params.update(gas_params)

            # Langkah 1: Setujui pemain
            Logger.info(f" 🧵 [Game {self.batch_count}] Sending ApprovePlayer transaction...")
            def build_approve_tx():
                return self.contract.functions.approvePlayer().build_transaction(tx_params)
            approve_tx_hash, approve_receipt = self.retry_transaction(build_approve_tx, priv_key)
            if approve_receipt is None or approve_receipt.status != 1:
                Logger.error(f" ↪️ [Game {self.batch_count}] ApprovePlayer failed after retries.")
                return False

            Logger.success(f" 🧵 [Game {self.batch_count}] {Fore.MAGENTA}ApprovePlayer{Fore.RESET} Successful! HashID -> {Fore.GREEN}{approve_tx_hash.hex()}{Fore.RESET}")

            # Ambil nonce terbaru sebelum transaksi berikutnya
            nonce = self.w3.eth.get_transaction_count(player_address, 'pending')
            tx_params['nonce'] = nonce

            # Langkah 2: Pilih mode permainan
            is_onchain = (GAME_MODE == "on-chain")
            Logger.info(f" 🧵 [Game {self.batch_count}] Sending SelectMode transaction (Mode: {GAME_MODE})...")
            def build_select_tx():
                return self.contract.functions.selectMode(is_onchain).build_transaction(tx_params)
            select_tx_hash, select_receipt = self.retry_transaction(build_select_tx, priv_key)
            if select_receipt is None or select_receipt.status != 1:
                Logger.error(f" ↪️ [Game {self.batch_count}] SelectMode failed after retries.")
                return False

            Logger.success(f" 🧵 [Game {self.batch_count}] {Fore.MAGENTA}SelectMode{Fore.RESET} Successful! {Fore.GREEN}Mode: {GAME_MODE}{Fore.RESET}")

            # Ambil nonce terbaru sebelum transaksi berikutnya
            nonce = self.w3.eth.get_transaction_count(player_address, 'pending')
            tx_params['nonce'] = nonce

            # Langkah 3: Mulai game baru
            game_id = generate_game_id(player_address)
            initial_boards = generate_initial_boards()
            initial_moves = generate_initial_moves()

            Logger.info(f" 🧵 [Game {self.batch_count}] Sending StartGame transaction...")
            def build_start_tx():
                return self.contract.functions.startGame(
                    game_id,
                    initial_boards,
                    initial_moves
                ).build_transaction(tx_params)
            start_tx_hash, start_receipt = self.retry_transaction(build_start_tx, priv_key)
            if start_receipt is None or start_receipt.status != 1:
                Logger.error(f" ↪️ [Game {self.batch_count}] StartGame failed after retries.")
                return False

            gas_info_start = self.calculate_gas_cost(start_receipt)
            Logger.success(f" 🧵 [Game {self.batch_count}] {Fore.MAGENTA}StartGame{Fore.RESET} Successful! HashID -> {Fore.GREEN}{start_tx_hash.hex()}{Fore.RESET}")
            Logger.gas_report(f" ⛽ Gas Used for StartGame: {gas_info_start['gas_used']} units | Cost: {Fore.YELLOW}{gas_info_start['gas_cost_eth']:.8f} 0G{Fore.RESET}")
            start_success = True

            # Langkah 4: Lakukan langkah dalam game
            if start_success:
                board = initial_boards[0]
                highest_tile = 0
                current_step = 0

                if GAME_MODE == "on-chain":
                    # Mode on-chain: Kirim setiap gerakan
                    for step in range(self.game_steps):
                        current_step += 1
                        move, result_board = generate_next_move_and_result(board)
                        move_str = ["Up", "Right", "Down", "Left"][move]
                        Logger.info(f" 🧵 [Game {self.batch_count} Step {Fore.GREEN}#{step+1}{Fore.RESET}] Move: {Fore.MAGENTA}{move_str}{Fore.RESET}")
                        time.sleep(7)  # Jeda 7 detik antar langkah
                        Logger.info(f" 🧵 [Game {self.batch_count}] Sending Play transaction for step {Fore.GREEN}#{step+1}...{Fore.RESET}")
                        # Ambil nonce terbaru sebelum transaksi
                        nonce = self.w3.eth.get_transaction_count(player_address, 'pending')
                        tx_params['nonce'] = nonce
                        def build_play_tx():
                            return self.contract.functions.play(
                                game_id,
                                move,
                                result_board
                            ).build_transaction(tx_params)
                        play_tx_hash, play_receipt = self.retry_transaction(build_play_tx, priv_key)
                        if play_receipt is None or play_receipt.status != 1:
                            Logger.error(f" ↪️ [Game {Fore.GREEN}#{self.batch_count}{Fore.RESET} Step #{step+1}] Play failed after retries.")
                            break

                        gas_info_play = self.calculate_gas_cost(play_receipt)
                        
                        # Parse event NewMoves
                        new_move_event = []
                        new_move_signature = self.w3.keccak(text="NewMove(address,bytes32,uint256,uint256)").hex()
                        for log in play_receipt['logs']:
                            if len(log['topics']) > 0 and log['topics'][0].hex() == new_move_signature:
                                new_move_event.append(self.contract.events.NewMove().process_log(log))
                        if new_move_event:
                            Logger.success(f" 🧵 [Game {self.batch_count} Step {Fore.GREEN}#{step+1}{Fore.RESET}] {Fore.MAGENTA}Play{Fore.RESET} Successful! HashID -> {Fore.GREEN}{play_tx_hash.hex()}{Fore.RESET}")
                            Logger.gas_report(f" ⛽ Gas Used for Play: {gas_info_play['gas_used']} units | Cost: {Fore.YELLOW}{gas_info_play['gas_cost_eth']:.8f} 0G{Fore.RESET}")
                        board = result_board
                        # Hitung highest tile
                        for i in range(16):
                            tile = get_tile(result_board, i)
                            if tile > highest_tile:
                                highest_tile = tile
                        time.sleep(20)  # Delay untuk menghindari error nonce
                else:
                    # Mode off-chain: Kumpulkan semua langkah, lalu kirim batch
                    moves = []
                    result_boards = []
                    for step in range(self.game_steps):
                        current_step += 1
                        move, result_board = generate_next_move_and_result(board)
                        move_str = ["Up", "Right", "Down", "Left"][move]
                        Logger.info(f" 🧵 [Game {self.batch_count} Step {Fore.GREEN}#{step+1}{Fore.RESET}] Move: {Fore.MAGENTA}{move_str}{Fore.RESET}")
                        time.sleep(7)  # Jeda 7 detik antar langkah
                        moves.append(move)
                        result_boards.append(result_board)
                        # Hitung highest tile
                        for i in range(16):
                            tile = get_tile(result_board, i)
                            if tile > highest_tile:
                                highest_tile = tile
                        board = result_board

                    # Validasi data sebelum mengirim batch
                    if len(moves) != len(result_boards):
                        Logger.error(f" ↪️ [Game {self.batch_count}] Invalid batch: moves ({len(moves)}) and resultBoards ({len(result_boards)}) length mismatch")
                        return False

                    # Estimasi gas untuk batch
                    Logger.info(f" 🧵 [Game {self.batch_count}] Estimating gas for batch of {self.game_steps} step moves...")
                    tx_params_for_estimate = tx_params.copy()
                    tx_params_for_estimate['gas'] = GAS_LIMIT_RANGE[1]
                    # Ambil nonce terbaru sebelum estimasi
                    nonce = self.w3.eth.get_transaction_count(player_address, 'pending')
                    tx_params_for_estimate['nonce'] = nonce
                    estimated_gas = self.contract.functions.submitBatchMoves(
                        game_id,
                        moves,
                        result_boards
                    ).estimate_gas(tx_params_for_estimate)
                    Logger.info(f" 🧵 Estimated gas for batch: {estimated_gas} units")

                    # Gunakan gas limit lebih besar dari estimasi
                    gas_limit = int(estimated_gas * 1.1)  # Margin 10%
                    if gas_limit < GAS_LIMIT_RANGE[0]:
                        gas_limit = GAS_LIMIT_RANGE[0]
                    if gas_limit > GAS_LIMIT_RANGE[1]:
                        gas_limit = GAS_LIMIT_RANGE[1]
                    tx_params['gas'] = gas_limit

                    Logger.info(f" 🧵 [Game {self.batch_count}] Sending batch of {self.game_steps} moves with gas limit {gas_limit}...")
                    # Ambil nonce terbaru sebelum transaksi
                    nonce = self.w3.eth.get_transaction_count(player_address, 'pending')
                    tx_params['nonce'] = nonce
                    def build_batch_tx():
                        return self.contract.functions.submitBatchMoves(
                            game_id,
                            moves,
                            result_boards
                        ).build_transaction(tx_params)
                    submit_tx_hash, submit_receipt = self.retry_transaction(build_batch_tx, priv_key)
                    if submit_receipt is None or submit_receipt.status != 1:
                        Logger.error(f" ↪️ [Game {self.batch_count}] Batch failed after retries.")
                        return False

                    gas_info_submit = self.calculate_gas_cost(submit_receipt)
                    Logger.success(f"🧵 [Game {self.batch_count}] {Fore.MAGENTA}Batch Raw Log/txid{Fore.RESET} Sent! HashID -> {Fore.GREEN}{submit_tx_hash.hex()}{Fore.RESET}")
                    Logger.gas_report(f" ⛽ Gas Used for Batch: {gas_info_submit['gas_used']} units | Cost: {Fore.YELLOW}{gas_info_submit['gas_cost_eth']:.8f} 0G{Fore.RESET}")

                    # Parse event BatchMoves
                    move_events = []
                    batch_moves_signature = self.w3.keccak(text="BatchMoves(address,bytes32,uint8[],uint128[])").hex()
                    for log in submit_receipt['logs']:
                        if len(log['topics']) > 0 and log['topics'][0].hex() == batch_moves_signature:
                            move_events.append(self.contract.events.BatchMoves().process_log(log))
                    if move_events:
                        Logger.info(f" 🧵 Processed {len(move_events[0]['args']['moves'])} moves in 1 transaction!")
                        for i, (move, result_board) in enumerate(zip(move_events[0]['args']['moves'], move_events[0]['args']['resultBoards'])):
                            move_str = ["Up", "Right", "Down", "Left"][move]
                            # Logger.info(f" 🧵 [Game {self.batch_count} Step #{i+1}] Recorded Move: {move_str}, Result Board: {result_board}")  # Dikommentari untuk menyembunyikan log
                    
            # Langkah 5: Cek apakah game benar-benar selesai
            Logger.info(f" 🧵 [Game {self.batch_count}] Checking if game is over...")
            is_game_over = check_game_over(board) or current_step >= self.game_steps or current_step >= 100 or highest_tile >= 8  # Anggap selesai jika mencapai ubin 256 (2^8)
            Logger.info(f" 🧵 [Game {self.batch_count}] {Fore.YELLOW}Game over status: {is_game_over}{Fore.RESET}")
            if not is_game_over:
                Logger.warning(f" 🧵 [Game {self.batch_count}] Game not over yet, continuing...")
                return True

            # Langkah 6: Tandai game over dengan endGame
            Logger.info(f" 🧵 [Game {self.batch_count}] Estimating gas for EndGame transaction...")
            tx_params_for_estimate = tx_params.copy()
            tx_params_for_estimate['gas'] = GAS_LIMIT_RANGE[1]
            # Ambil nonce terbaru sebelum estimasi
            nonce = self.w3.eth.get_transaction_count(player_address, 'pending')
            tx_params_for_estimate['nonce'] = nonce
            estimated_gas = self.contract.functions.endGame(game_id).estimate_gas(tx_params_for_estimate)
            Logger.info(f" 🧵 Estimated gas for EndGame: {estimated_gas} units")

            # Gunakan gas limit lebih besar dari estimasi
            gas_limit = int(estimated_gas * 1.1)  # Margin 10%
            if gas_limit < GAS_LIMIT_RANGE[0]:
                gas_limit = GAS_LIMIT_RANGE[0]
            if gas_limit > GAS_LIMIT_RANGE[1]:
                gas_limit = GAS_LIMIT_RANGE[1]
            tx_params['gas'] = gas_limit

            Logger.info(f" 🧵 [Game {self.batch_count}] Sending EndGame transaction with gas limit {gas_limit}...")
            # Ambil nonce terbaru sebelum transaksi
            nonce = self.w3.eth.get_transaction_count(player_address, 'pending')
            tx_params['nonce'] = nonce
            def build_end_game_tx():
                return self.contract.functions.endGame(game_id).build_transaction(tx_params)
            end_game_tx_hash, end_game_receipt = self.retry_transaction(build_end_game_tx, priv_key)
            if end_game_receipt is None or end_game_receipt.status != 1:
                Logger.error(f" ↪️ [Game {Fore.GREEN}#{self.batch_count}{Fore.RESET}] EndGame failed after retries.")
                return False

            gas_info_end_game = self.calculate_gas_cost(end_game_receipt)
            Logger.success(f" 🧵 [Game {self.batch_count}] {Fore.MAGENTA}EndGame{Fore.RESET} Successful! HashID -> {Fore.GREEN}{end_game_tx_hash.hex()}{Fore.RESET}")
            Logger.gas_report(f" ⛽ Gas Used for EndGame: {gas_info_end_game['gas_used']} units | Cost: {Fore.YELLOW}{gas_info_end_game['gas_cost_eth']:.8f} 0G{Fore.RESET}")

            # Parse event GameOver
            game_over_event = self.contract.events.GameOver().process_receipt(end_game_receipt)
            if game_over_event:
                highest_tile = game_over_event[0]['args']['highestTile']
                moves_count = game_over_event[0]['args']['moves']
                Logger.info(f" 🧵 {Fore.CYAN}Game over! Highest tile: {highest_tile}, Moves: {moves_count}{Fore.RESET}")

            # Langkah 7: Klaim NFT secara otomatis dengan claimNFT
            Logger.info(f" 🧵 [Game {self.batch_count}] Estimating gas for ClaimNFT transaction...")
            tx_params_for_estimate['gas'] = GAS_LIMIT_RANGE[1]
            # Ambil nonce terbaru sebelum estimasi
            nonce = self.w3.eth.get_transaction_count(player_address, 'pending')
            tx_params_for_estimate['nonce'] = nonce
            estimated_gas = self.contract.functions.claimNFT(game_id).estimate_gas(tx_params_for_estimate)
            Logger.info(f" 🧵 Estimated gas for ClaimNFT: {estimated_gas} units")

            # Gunakan gas limit lebih besar dari estimasi
            gas_limit = int(estimated_gas * 1.1)  # Margin 10%
            if gas_limit < GAS_LIMIT_RANGE[0]:
                gas_limit = GAS_LIMIT_RANGE[0]
            if gas_limit > GAS_LIMIT_RANGE[1]:
                gas_limit = GAS_LIMIT_RANGE[1]
            tx_params['gas'] = gas_limit

            Logger.info(f" 🧵 [Game {self.batch_count}] Sending ClaimNFT transaction with gas limit {gas_limit}...")
            # Ambil nonce terbaru sebelum transaksi
            nonce = self.w3.eth.get_transaction_count(player_address, 'pending')
            tx_params['nonce'] = nonce
            def build_claim_nft_tx():
                return self.contract.functions.claimNFT(game_id).build_transaction(tx_params)
            claim_nft_tx_hash, claim_nft_receipt = self.retry_transaction(build_claim_nft_tx, priv_key)
            if claim_nft_receipt is None or claim_nft_receipt.status != 1:
                Logger.error(f" ↪️ [Game {self.batch_count}] {Fore.RED}ClaimNFT failed{Fore.RESET} after retries.")
                return False

            gas_info_claim_nft = self.calculate_gas_cost(claim_nft_receipt)
            Logger.success(f"🧵 [Game {self.batch_count}] {Fore.MAGENTA}ClaimNFT{Fore.RESET} Successful! HashID -> {Fore.GREEN}{claim_nft_tx_hash.hex()}{Fore.RESET}")
            Logger.gas_report(f" ⛽ Gas Used for ClaimNFT: {gas_info_claim_nft['gas_used']} units | Cost: {Fore.YELLOW}{gas_info_claim_nft['gas_cost_eth']:.8f} 0G{Fore.RESET}")

            # Parse event NFTMinted dan PendingNFTCleared
            nft_minted_event = []
            pending_cleared_event = []
            nft_minted_signature = self.w3.keccak(text="NFTMinted(address,bytes32,uint256,uint256)").hex()
            pending_cleared_signature = self.w3.keccak(text="PendingNFTCleared(bytes32)").hex()
            for log in claim_nft_receipt['logs']:
                if len(log['topics']) > 0:
                    if log['topics'][0].hex() == nft_minted_signature:
                        nft_minted_event.append(self.contract.events.NFTMinted().process_log(log))
                    elif log['topics'][0].hex() == pending_cleared_signature:
                        pending_cleared_event.append(self.contract.events.PendingNFTCleared().process_log(log))
            if nft_minted_event:
                token_id = nft_minted_event[0]['args']['tokenId']
                level = nft_minted_event[0]['args']['level']
                description = self.contract.functions.getDescription(level).call()
                uri = self.contract.functions.tokenURI(token_id).call()
                Logger.success(f" 🧩 {Fore.CYAN}Congrats You get NFT 🎉 'GAME 20G8 NFT', Auto Minted!{Fore.RESET} {Fore.YELLOW}Token ID: {token_id}, Level: {level}{Fore.RESET}")
                Logger.info(f" 🧩 {Fore.CYAN}NFT Description:{Fore.RESET} {description}")
                Logger.info(f"🧩 {Fore.CYAN}NFT Detail URI:{Fore.RESET} {uri}")
            if pending_cleared_event:
                Logger.info(f" 🧵 [Game {self.batch_count}] Pending NFT cleared for gameID: {pending_cleared_event[0]['args']['gameId'].hex()}")
            
            # Cek poin dan leaderboard
            points = self.contract.functions.getPlayerPoints(player_address).call()
            Logger.info(f"🧩 {Fore.CYAN}Point (XP) Player:{Fore.RESET} {points}")
            leaderboard = self.contract.functions.getLeaderboard().call()
            Logger.info(f"🧩 {Fore.CYAN}Leaderboard Player:{Fore.RESET} IS HIDDEN LOG")
            # Hidden : Logger.info(f"{Fore.GREEN}Leaderboard Player:{Fore.RESET} {leaderboard}")

            return True

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
                Logger.info(f" 🔎 Starting {Fore.MAGENTA}2048 Game {self.batch_count}{Fore.RESET} with random step -> {Fore.YELLOW}#{self.game_steps} moving steps...{Fore.RESET}")
                
                success = self.execute_game_interaction()
                if success:
                    Logger.warning(f" ✅ [GAME {Fore.GREEN}{self.batch_count}{Fore.RESET}] for wallet {Fore.GREEN}#{self.current_key_index + 1}{Fore.RESET} completed successfully")
                else:
                    Logger.warning(f" ❌ [GAME {Fore.RED}{self.batch_count}{Fore.RESET}] for wallet {Fore.RED}#{self.current_key_index + 1}{Fore.RESET} failed")

                cycle_completed = self.switch_wallet()
                self.batch_count += 1
                self.game_steps = random.randint(*GAME_STEPS_RANGE)
                
                if cycle_completed:
                    game_delay = random.randint(*GAME_CYCLE_DELAY_RANGE)
                    minutes, seconds = divmod(game_delay, 60)
                    Logger.warning(f" ✅ Cycle Completed!! Next game in {Fore.GREEN}{minutes} mins {seconds} secs{Fore.RESET}")
                    Logger.gas_report(f" 💲 Total gas used so far: {Fore.YELLOW}{self.total_gas_used:.8f} 0G{Fore.RESET}")
                    time.sleep(game_delay)
                else:
                    Logger.warning(f" 🔁 Moving to next wallet")

            except KeyboardInterrupt:
                Logger.info(f" ❌ {Fore.YELLOW}🎮 2048 Game stopped manually. Consider running with PM2 or Screen.{Fore.RESET}")
                break
            except Exception as e:
                Logger.error(f" ⭕️ Unexpected error in run loop: {str(e)}")
                time.sleep(60)

if __name__ == "__main__":
    print_banner()
    try:
        bot = Game2048()
        bot.run()
    except Exception as e:
        Logger.error(f"Fatal error: {str(e)}")