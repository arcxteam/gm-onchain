import os
import time
import random
import string
import json
import asyncio
from web3 import Web3
from web3.middleware import geth_poa_middleware
from solcx import compile_source, install_solc
from dotenv import load_dotenv
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)
load_dotenv()

try:
    install_solc("0.8.17")
except Exception as e:
    print(
        f"{Fore.YELLOW}Warning: Could not install solc 0.8.17, will use available version. Error: {e}{Style.RESET_ALL}"
    )

# ======================== Constants ========================
CONFIG = {
    "RPC_URLS": [
        "https://16600.rpc.thirdweb.com",
        "https://evm-rpc.0g.testnet.node75.org",
        "https://rpc.ankr.com/0g_newton",
        "https://evmrpc-testnet.0g.ai",
        "https://0g-json-rpc-public.originstake.com",
        "https://0g-rpc-evm01.validatorvn.com",
        "https://og-testnet-jsonrpc.itrocket.net",
        "https://0g-evmrpc.zstake.xyz/",
        "https://0g-rpc.murphynode.net",
        "https://0g-api.murphynode.net",
        "https://0g-evm-rpc.murphynode.net",
        "https://evm-0g.winnode.xyz"
    ],
    "GAS_MULTIPLIER": 1.1,
    "MAX_PRIORITY_GWEI": 6.5,
    "GAS_MIN_GWEI": 4.5,
    "GAS_MAX_GWEI": 15.0,
    "GAS_RESET_GWEI": 5.0,
    "RPC_TIMEOUT": 21,  # detik
    "RPC_RETRY_DELAY": 10,  # detik
    "WALLET_SWITCH_DELAY_MIN": 120,  # detik
    "WALLET_SWITCH_DELAY_MAX": 300,  # detik
}

CHAIN_SYMBOLS = {16600: "A0GI"}

# ======================== Helper Functions ========================
def print_info(message):
    print(f"{message}")

def print_success(message):
    print(f"{message}")

def print_error(message):
    print(f"{Fore.RED}{message}{Style.RESET_ALL}")

def print_warning(message):
    print(f"{message}")

def print_debug(message):
    print(f"{message}")

def short_address(address):
    """Format address with : 0x1234...5678"""
    return f"{address[:6]}...{address[-4:]}" if address else "Unknown address"

def sleep_seconds(seconds, message=None):
    """Sleep function with informative messages"""
    if message:
        print(f"⏳ {Fore.MAGENTA}{message} in {seconds} detik...{Style.RESET_ALL}")
        time.sleep(seconds)

def random_sleep(min_secs, max_secs, message=None):
    """Sleep with random durasition """
    seconds = random.randint(min_secs, max_secs)
    sleep_seconds(seconds, message)

def validate_rpc_urls(urls):
    """Validate RPC URLs to ensure the format is correct"""
    valid_urls = []
    for url in urls:
        url = url.strip()
        if url and url.startswith("http"):
            valid_urls.append(url)
        else:
            print_warning(f"RPC URL not valid: {url}")
    
    if not valid_urls:
        print_error("No valid RPC URL found. Using the default.")
        return ["https://16600.rpc.thirdweb.com", "https://evmrpc-testnet.0g.ai"]
    
    return valid_urls

# ================= RPC Connection Management ===================
def connect_to_rpc():
    """Connect to RPC endpoint, with rotation if failed"""
    rpc_urls = validate_rpc_urls(CONFIG["RPC_URLS"])
    random.shuffle(rpc_urls)
    
    for rpc_url in rpc_urls:
        try:
            print_info(f"🔄 Try to connection RPC: {rpc_url}")
            w3 = Web3(Web3.HTTPProvider(rpc_url.strip(), request_kwargs={'timeout': CONFIG["RPC_TIMEOUT"]}))
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            if w3.is_connected():
                chain_id = w3.eth.chain_id
                print_success(f"🌐 Already connect to RPC: {rpc_url}")
                print_info(f"📡 Chain ID: {chain_id} - {CHAIN_SYMBOLS.get(chain_id, 'Unknown')}")
                return w3, rpc_url
        except Exception as e:
            print_warning(f"⚠️ Failed to connect RPC {rpc_url}: {str(e)}")
    
    print_error("❌ Failed to connect to all RPC endpoints.")
    raise ConnectionError("Unable to connect to 0G network. Check RPC URLs.")

def switch_rpc(current_rpc_url):
    """Switch to another RPC if a problem occurs"""
    rpc_urls = validate_rpc_urls(CONFIG["RPC_URLS"])
    available_rpcs = [url for url in rpc_urls if url != current_rpc_url]
    
    if not available_rpcs:
        print_warning("⚠️ No alternative RPC available.")
        sleep_seconds(CONFIG["RPC_RETRY_DELAY"], "Wait before retrying the same RPC")
        return connect_to_rpc()
    
    new_rpc = random.choice(available_rpcs)
    print_warning(f"🔄 Switch to other RPC {current_rpc_url} ke {new_rpc}")
    
    try:
        w3 = Web3(Web3.HTTPProvider(new_rpc.strip(), request_kwargs={'timeout': CONFIG["RPC_TIMEOUT"]}))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        if w3.is_connected():
            print_success(f"✅ Successful switch to RPC: {new_rpc}")
            return w3, new_rpc
    except Exception as e:
        print_error(f"❌ Failed switch to RPC {new_rpc}: {str(e)}")
        CONFIG["RPC_URLS"] = [url for url in CONFIG["RPC_URLS"] if url != new_rpc]
        return switch_rpc(current_rpc_url)

# ================= Gas Price Management ===================
def check_eip1559_support(w3):
    """Check EIP-1559 support on the network"""
    try:
        latest_block = w3.eth.get_block('latest')
        if 'baseFeePerGas' in latest_block and latest_block['baseFeePerGas']:
            print_success("✅ Network support EIP-1559")
            return True
        
        try:
            fee_history = w3.eth.fee_history(1, 'latest')
            if 'baseFeePerGas' in fee_history and fee_history['baseFeePerGas'] and len(fee_history['baseFeePerGas']) > 0:
                print_success("✅ Network support EIP-1559")
                return True
        except:
            pass
        
        print_warning("⚠️ EIP-1559 not available, using legacy gas")
        return False
    except Exception as e:
        print_warning(f"⚠️ Error checking EIP-1559 support: {str(e)}")
        return False

def get_eip1559_gas_params(w3):
    """Get parameter gas EIP-1559"""
    try:
        if not check_eip1559_support(w3):
            return None

        fee_history = w3.eth.fee_history(1, 'latest')
        base_fee = fee_history['baseFeePerGas'][0]

        max_priority = w3.to_wei(CONFIG["MAX_PRIORITY_GWEI"], 'gwei')
        max_fee = int(base_fee * CONFIG["GAS_MULTIPLIER"]) + max_priority

        base_fee_gwei = w3.from_wei(base_fee, 'gwei')
        max_fee_gwei = w3.from_wei(max_fee, 'gwei')
        max_priority_gwei = w3.from_wei(max_priority, 'gwei')

        print_info(f"⛽ Gas: Base Fee: {base_fee_gwei:.2f} Gwei | Max Fee: {max_fee_gwei:.2f} Gwei | Priority: {max_priority_gwei:.2f} Gwei")

        return {'maxFeePerGas': max_fee, 'maxPriorityFeePerGas': max_priority}
    except Exception as e:
        print_error(f"❌ Estimation EIP-1559 failed: {str(e)}")
        return None

def get_legacy_gas_price(w3):
    """Get legacy gas price with fallback to default value if failed"""
    try:
        # Coba gas dari legacy
        current = w3.eth.gas_price

        if current <= w3.to_wei(0.5, "gwei"):
            print_warning(f"⚠️ Gas price is low ({w3.from_wei(current, 'gwei'):.2f} Gwei), use default bang")
            gas_price = w3.to_wei(CONFIG["GAS_MIN_GWEI"], "gwei")
        else:
            min_gas = w3.to_wei(CONFIG["GAS_MIN_GWEI"], "gwei")
            max_gas = w3.to_wei(CONFIG["GAS_MAX_GWEI"], "gwei")
            
            gas_price = int(current * CONFIG["GAS_MULTIPLIER"])
            
            if gas_price < min_gas:
                gas_price = min_gas
            elif gas_price > max_gas:
                gas_price = max_gas
        
        gas_gwei = w3.from_wei(gas_price, "gwei")
        print_info(f"⛽ Gas price: {gas_gwei:.2f} Gwei (Legacy Mode)")
        
        return gas_price
    except Exception as e:
        print_error(f"❌ Estimasi legacy gas failed: {str(e)}")
        default_gas = w3.to_wei(CONFIG["GAS_MIN_GWEI"], "gwei")
        print_warning(f"⚠️ Used gas price default: {CONFIG['GAS_MIN_GWEI']} Gwei")
        return default_gas

def reset_gas_price(w3, gas_price):
    """Reset gas price to a reasonable starting value after too many retries"""
    if isinstance(gas_price, dict):
        gas_price["maxFeePerGas"] = w3.to_wei(CONFIG["GAS_RESET_GWEI"], "gwei")
        gas_price["maxPriorityFeePerGas"] = w3.to_wei(1, "gwei")
        print_warning("⚠️ Gas price reset to a more reasonable value (EIP-1559)")
    else:
        gas_price = w3.to_wei(CONFIG["GAS_RESET_GWEI"], "gwei")
        print_warning("⚠️ Gas price reset to a more reasonable value (Legacy)")
    return gas_price

def update_gas_price(w3):
    """Update gas price with EIP-1559 or legacy"""
    eip1559_params = get_eip1559_gas_params(w3)
    if eip1559_params:
        print_success("✅ Used mode gas EIP-1559")
        return eip1559_params
    else:
        # Fallback ke legacy
        gas_price = get_legacy_gas_price(w3)
        print_success("✅ Used mode gas Legacy")
        return gas_price

def get_safe_nonce(w3, address):
    """Get a secure nonce, by ensuring there are no pending transactions"""
    try:
        pending_nonce = w3.eth.get_transaction_count(address, "pending")
        latest_nonce = w3.eth.get_transaction_count(address, "latest")
    
        if pending_nonce > latest_nonce:
            print_debug(f"🔄 Waiting for pending transactions to complete... (pending nonce: {pending_nonce}, latest nonce: {latest_nonce})")
            time.sleep(5)
            return get_safe_nonce(w3, address)
    
        print_debug(f"🔢 {Fore.MAGENTA}Used nonce: {latest_nonce}{Style.RESET_ALL}")
        return latest_nonce
    except Exception as e:
        print_warning(f"⚠️ Error get nonce: {str(e)}")
        return w3.eth.get_transaction_count(address, "latest")

def reset_pending_transactions(w3, address, private_key):
    """Reset pending transaction! sending a dummy tx in same address & nonce"""
    try:
        pending_nonce = w3.eth.get_transaction_count(address, "pending")
        latest_nonce = w3.eth.get_transaction_count(address, "latest")
        
        if pending_nonce > latest_nonce:
            print_warning(f"⚠️ Detections {pending_nonce - latest_nonce} pending transactions that may be stuck.")
            
            max_reset_tx = 3
            for nonce in range(latest_nonce, min(pending_nonce, latest_nonce + max_reset_tx)):
                print_warning(f"🔄 Trying to reset transaction with nonce {nonce}...")
                tx = {
                    "from": address,
                    "to": address,
                    "value": 0,
                    "gas": 21000,
                    "nonce": nonce,
                    "chainId": w3.eth.chain_id,
                }

                gas_price = update_gas_price(w3)
                if isinstance(gas_price, dict):
                    tx["maxFeePerGas"] = w3.to_wei(10, "gwei")
                    tx["maxPriorityFeePerGas"] = w3.to_wei(2, "gwei")
                else:
                    tx["gasPrice"] = w3.to_wei(10, "gwei")

                try:
                    signed = w3.eth.account.sign_transaction(tx, private_key)
                    receipt = w3.eth.send_raw_transaction(signed.rawTransaction)
                    print_success(f"✅ Transaaction reset for nonce {nonce} success sending: {receipt.hex()}")
                except Exception as e:
                    if "already known" in str(e).lower():
                        print_warning(f"⚠️ Transaction for nonce {nonce} ready on mempool")
                    else:
                        print_error(f"❌ Error reset nonce {nonce}: {str(e)}")
            
        return True
    except Exception as e:
        print_error(f"❌ Error reset transaction pending: {str(e)}")
        return False

def estimate_gas(w3, contract_func, sender):
    """Generic function for gas estimation with fallback to defaults"""
    try:
        gas_estimate = contract_func.estimate_gas({'from': sender})
        return int(gas_estimate * 1.02)  # 10% buffer
    except Exception as e:
        default_gas = 155000
        print_warning(f"⚠️ Estimasi gas failed: {str(e)}. Used default: {default_gas}")
        return default_gas

def wait_for_transaction_completion(w3, tx_hash, timeout=210):
    """Waiting for transactions to complete with better error handling"""
    print_info(f"⏳ Waiting transaction {tx_hash} terconfirmed...")
    start_time = time.time()
    
    last_error_time = 0
    check_interval = 5

    while time.time() - start_time < timeout:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt is not None:
                if receipt.status == 1:
                    print_success(f"✅ Transaction terconfirm: number blok #{receipt.blockNumber}")
                    return receipt
                else:
                    print_error(f"❌ Transaction failed on blockchain")
                    return receipt
        except Exception as e:
            current_time = time.time()
            error_msg = str(e).lower()
            
            if current_time - last_error_time > 5:
                if "not found" not in error_msg:
                    print_warning(f"⚠️ Error checking receipt: {str(e)}")
                    last_error_time = current_time

        time.sleep(check_interval)

    print_warning(f"⏱️ Timeout wait transaction {tx_hash}")
    return None

def track_gas_usage(w3, tx_receipt, gas_price):
    """Track used and gas transaction"""
    gas_used = tx_receipt.gasUsed
    if isinstance(gas_price, dict):
        cost_wei = gas_used * gas_price["maxFeePerGas"]
    else:
        cost_wei = gas_used * gas_price
        
    cost_eth = w3.from_wei(cost_wei, "ether")
    print_info(f"📊 Gas used: {gas_used} | Biaya Cost: {cost_eth:.8f} {CHAIN_SYMBOLS.get(w3.eth.chain_id, 'A0GI')}")

def load_private_keys():
    """Load private keys dari environment variable dan file"""
    private_keys = []

    env_private_key = os.getenv("PRIVATE_KEY")
    if env_private_key and env_private_key.strip():
        if not env_private_key.startswith("0x"):
            env_private_key = "0x" + env_private_key
        private_keys.append(env_private_key.strip())

    try:
        with open("private_keys.txt", "r") as file:
            keys = [
                line.strip()
                for line in file.readlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            for key in keys:
                if not key.startswith("0x"):
                    key = "0x" + key
                private_keys.append(key)
    except Exception as e:
        print(f"{Fore.YELLOW}Note: private_keys.txt not found or couldn't be read: {e}{Style.RESET_ALL}")

    if not private_keys:
        raise Exception("No private keys found in .env or private_keys.txt")

    print_success(f"📸 Loaded {len(private_keys)} EVM wallet successfully")

    seen = set()
    unique_keys = []
    for key in private_keys:
        if key not in seen:
            seen.add(key)
            unique_keys.append(key)

    return unique_keys

# Simple contract templates
SIMPLE_CONTRACTS = {
    "BasicERC20": """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.1;

contract BasicERC20 {
    string public name;
    string public symbol;
    uint8 public decimals = 18;
    uint256 public totalSupply;
    
    mapping(address => uint256) public balanceOf;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    
    constructor() {
        name = "BasicToken";
        symbol = "BASIC";
        totalSupply = 1000000 * 10**uint256(decimals);
        balanceOf[msg.sender] = totalSupply;
    }
    
    function transfer(address to, uint256 value) public returns (bool success) {
        require(balanceOf[msg.sender] >= value);
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        emit Transfer(msg.sender, to, value);
        return true;
    }
}
""",
    "SimpleStore": """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.1;

contract SimpleStore {
    uint256 private value;
    
    function set(uint256 newValue) public {
        value = newValue;
    }
    
    function get() public view returns (uint256) {
        return value;
    }
}
""",
    "NameRegistry": """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.1;

contract NameRegistry {
    mapping(string => address) private registry;
    
    function register(string memory name) public {
        registry[name] = msg.sender;
    }
    
    function getAddress(string memory name) public view returns (address) {
        return registry[name];
    }
    
    function isOwner(string memory name) public view returns (bool) {
        return registry[name] == msg.sender;
    }
}
""",
    "Donation": """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.1;

contract Donation {
    address public beneficiary;
    uint256 public totalDonations;
    mapping(address => uint256) public donations;
    
    constructor() {
        beneficiary = msg.sender;
    }
    
    function donate() public payable {
        require(msg.value > 0, "Donation must be greater than zero");
        donations[msg.sender] += msg.value;
        totalDonations += msg.value;
    }
    
    function getDonationAmount() public view returns (uint256) {
        return donations[msg.sender];
    }
}
""",
    "MessageBoard": """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.1;

contract MessageBoard {
    string private latestMessage;
    address private latestSender;
    
    function postMessage(string memory message) public {
        latestMessage = message;
        latestSender = msg.sender;
    }
    
    function getMessage() public view returns (string memory, address) {
        return (latestMessage, latestSender);
    }
}
""",
    "Counter": """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.1;

contract Counter {
    uint256 private count;
    
    function increment() public {
        count += 1;
    }
    
    function getCount() public view returns (uint256) {
        return count;
    }
}
""",
    "Ownership": """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.1;

contract Ownership {
    address public owner;
    
    constructor() {
        owner = msg.sender;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }
    
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Invalid address");
        owner = newOwner;
    }
}
""",
}

CONTRACTS = {}
CONTRACTS.update(SIMPLE_CONTRACTS)


def generate_random_name(length=10):
    """Generate a random contract name."""
    adjectives = [
        "Smart",
        "Crypto",
        "Chain",
        "Block",
        "Decentralized",
        "Secure",
        "Digital",
        "Dynamic",
        "Quantum",
        "Virtual",
        "Atomic",
        "Hyper",
        "Rapid",
        "Logic",
        "Cosmic",
    ]

    nouns = [
        "Vault",
        "Ledger",
        "Registry",
        "Wallet",
        "Guardian",
        "Nexus",
        "Protocol",
        "Token",
        "Oracle",
        "Network",
        "Hub",
        "Engine",
        "Portal",
        "Matrix",
        "Core",
    ]

    adjective = random.choice(adjectives)
    noun = random.choice(nouns)

    digits = "".join(random.choices(string.digits, k=3))

    return f"{adjective}{noun}{digits}"


def compile_contract(contract_source, contract_name):
    """Compile Solidity contract and return bytecode and ABI."""
    compiled_sol = compile_source(
        contract_source, output_values=["abi", "bin"], solc_version="0.8.17")

    contract_key = f"<stdin>:{contract_name}"
    contract_interface = compiled_sol[contract_key]

    return {"abi": contract_interface["abi"], "bytecode": contract_interface["bin"]}


async def deploy_contract(w3, current_rpc, contract_type, contract_name, private_key):
    """Deploy a contract and return its details."""
    print_info(f"⚙️ {Fore.MAGENTA} Compiling {Fore.GREEN}{contract_type}{Fore.MAGENTA} the contract name is {Fore.GREEN}{contract_name}{Style.RESET_ALL}")

    contract_source = CONTRACTS[contract_type]
    source_contract_name = contract_type

    try:
        contract_data = compile_contract(contract_source, source_contract_name)
    except Exception as e:
        print_error(f"❌ Compilation failed: {str(e)}")
        return None

    print_success(f"✅ Compilation successful")

    account = w3.eth.account.from_key(private_key)
    wallet_address = account.address

    reset_pending_transactions(w3, wallet_address, private_key)

    # Get current balance
    balance = w3.eth.get_balance(wallet_address)
    balance_eth = w3.from_wei(balance, "ether")
    print_info(f"🤑 Current wallet balance: {Fore.YELLOW}{balance_eth:.6f} A0GI{Style.RESET_ALL}")

    # Get gas price
    gas_price = update_gas_price(w3)
    
    if isinstance(gas_price, dict):
        gas_price_info = f"{w3.from_wei(gas_price['maxFeePerGas'], 'gwei')} gwei (max fee)"
    else:
        gas_price_info = f"{w3.from_wei(gas_price, 'gwei')} gwei"
        
    print_info(f"💰 Using gas price: {Fore.YELLOW}{gas_price_info}{Style.RESET_ALL}")

    contract = w3.eth.contract(abi=contract_data["abi"], bytecode=contract_data["bytecode"])

    nonce = get_safe_nonce(w3, wallet_address)

    # Estimasi gas Default
    gas_limit = 155000
    try:
        estimated_gas = w3.eth.estimate_gas({"from": wallet_address, "data": contract_data["bytecode"]})
        gas_limit = int(estimated_gas * 1.02)  # 10% buffer
        print_info(f"⛽ Estimated gas: {Fore.YELLOW}{estimated_gas}{Style.RESET_ALL} -> Add 5-10% boosting -> final {Fore.YELLOW}gas is {gas_limit}{Style.RESET_ALL}")
    except Exception as e:
        print_warning(f"⚠️ Could not estimate gas: {str(e)}")
        print_info(f"⛽ Using default gas limit: {Fore.YELLOW}{gas_limit}{Style.RESET_ALL}")

    # Calculate maximum gas cost
    if isinstance(gas_price, dict):
        max_gas_cost = gas_limit * gas_price["maxFeePerGas"]
    else:
        max_gas_cost = gas_limit * gas_price
        
    max_gas_cost_eth = w3.from_wei(max_gas_cost, "ether")
    print_info(f"💲 Maximum gas cost: {Fore.YELLOW}{max_gas_cost_eth:.6f} A0GI{Style.RESET_ALL}")

    if balance < max_gas_cost:
        print_error(f"❌ Insufficient balance for gas! Need {Fore.RED}{max_gas_cost_eth:.6f}{Style.RESET_ALL} A0GI but have {Fore.YELLOW}{balance_eth:.6f} A0GI{Style.RESET_ALL}")
        return None
    tx_data = {}
    
    try:
        if isinstance(gas_price, dict):
            tx_data = contract.constructor().build_transaction(
                {
                    "from": wallet_address,
                    "nonce": nonce,
                    "gas": gas_limit,
                    "maxFeePerGas": gas_price["maxFeePerGas"],
                    "maxPriorityFeePerGas": gas_price["maxPriorityFeePerGas"]
                }
            )
        else:
            tx_data = contract.constructor().build_transaction(
                {
                    "from": wallet_address,
                    "nonce": nonce,
                    "gas": gas_limit,
                    "gasPrice": gas_price,
                }
            )
    except Exception as e:
        print_error(f"❌ Error building transaction: {str(e)}")
        if "429" in str(e) or "too many requests" in str(e) or "server error" in str(e):
            print_warning(f"⚠️ RPC problem, try switching to other RPC...")
            w3, current_rpc = switch_rpc(current_rpc)
            return await deploy_contract(w3, current_rpc, contract_type, contract_name, private_key)
        return None

    print_info(f"{Fore.MAGENTA}🚀 Deploying contract to blockchain...WAIT...WAIT{Style.RESET_ALL}")
    signed_tx = w3.eth.account.sign_transaction(tx_data, private_key)

    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print_info(f"📨 Transaction explorer TXiD: {Fore.CYAN}{w3.to_hex(tx_hash)}{Style.RESET_ALL}")

        print_warning(f"⏳ Waiting for transaction confirmation...")
        tx_receipt = wait_for_transaction_completion(w3, tx_hash, timeout=210)

        if tx_receipt and tx_receipt.status == 1:
            contract_address = tx_receipt.contractAddress
            print_success(f"✅ Contract deployed successfully!")
            print_info(f"📍 Contract Address: {Fore.YELLOW}{contract_address}{Style.RESET_ALL}")
            print_info(f"📝 Transaction TXiD/Hash: {Fore.CYAN}{w3.to_hex(tx_hash)}{Style.RESET_ALL}")
            print_info(f"⛽ Gas used: {Fore.YELLOW}{tx_receipt.gasUsed}{Style.RESET_ALL} {Fore.GREEN}{(tx_receipt.gasUsed / gas_limit) * 100:.1f}% of limit{Style.RESET_ALL}")

            # Calculate actual gas cost
            if isinstance(gas_price, dict):
                actual_gas_cost = tx_receipt.gasUsed * gas_price["maxFeePerGas"]
            else:
                actual_gas_cost = tx_receipt.gasUsed * gas_price
                
            actual_gas_cost_eth = w3.from_wei(actual_gas_cost, "ether")
            print_info(f"💲 Actual gas cost: {Fore.YELLOW}{actual_gas_cost_eth:.6f} A0GI{Style.RESET_ALL}")
            
            track_gas_usage(w3, tx_receipt, gas_price)

            deployment_record = {
                "contract_type": contract_type,
                "contract_name": contract_name,
                "address": contract_address,
                "transaction_hash": w3.to_hex(tx_hash),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "gas_used": tx_receipt.gasUsed,
                "gas_price": gas_price_info,
                "total_cost": float(actual_gas_cost_eth),
                "wallet_address": wallet_address,
                "abi": contract_data["abi"],
            }

            return deployment_record
        else:
            print_error(f"❌ Deployment failed. Transaction status: {Fore.RED}{tx_receipt.status if tx_receipt else 'Unknown'}{Style.RESET_ALL}")
            try:
                tx_info = w3.eth.get_transaction(tx_hash)
                if isinstance(gas_price, dict):
                    print_info(f"📊 Transaction details: Max fee {Fore.YELLOW}{w3.from_wei(tx_info.get('maxFeePerGas', 0), 'gwei')} gwei, Gas limit {tx_info.get('gas', 0)}{Style.RESET_ALL}")
                else:
                    print_info(f"📊 Transaction details: Gas price {Fore.YELLOW}{w3.from_wei(tx_info.get('gasPrice', 0), 'gwei')} gwei, Gas limit {tx_info.get('gas', 0)}{Style.RESET_ALL}")
            except Exception as tx_error:
                print_warning(f"⚠️ Could not fetch transaction details: {str(tx_error)}")
                
            return None

    except Exception as e:
        print_error(f"❌ Error during deployment: {Fore.RED}{str(e)}{Style.RESET_ALL}")

        if "429" in str(e) or "too many requests" in str(e) or "server error" in str(e):
            print_warning(f"⚠️ RPC problem, try switching to other RPC...")
            w3, current_rpc = switch_rpc(current_rpc)
            return await deploy_contract(w3, current_rpc, contract_type, contract_name, private_key)
            
        return None


def save_deployment_records(deployments):
    """Save deployment records to a JSON file."""
    # Function is disabled to reduce files in directory
    print(f"⚙️ {Fore.MAGENTA} Deployment record saving is disabled{Style.RESET_ALL}")
    # To enable the function, remove the line above and uncomment the code below
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # filename = f"deployments_{timestamp}.json"
    # try:
    #     with open(filename, 'w') as f:
    #         json.dump(deployments, f, indent=2)
    #     print(f"{Fore.GREEN} Deployment records saved to {filename}{Style.RESET_ALL}")
    # except Exception as e:
    #     print(f"{Fore.RED} Failed to save deployment records: {str(e)}{Style.RESET_ALL}")


async def wait_with_progress(hours, message="Waiting"):
    """Wait for specified hours with progress updates."""
    seconds = int(hours * 3600)
    update_interval = 2025  # progress every 33 menit

    print(f"\n{Fore.YELLOW}⏳ {message} for approximately {hours:.1f} hours...{Style.RESET_ALL}")

    start_time = time.time()
    end_time = start_time + seconds

    while time.time() < end_time:
        elapsed = time.time() - start_time
        remaining = end_time - time.time()

        if remaining <= 0:
            break

        elapsed_hours = elapsed / 3600
        remaining_hours = remaining / 3600
        progress_percent = (elapsed / seconds) * 100

        print(f"⌛ Progress: {Fore.YELLOW}{progress_percent:.1f}%{Style.RESET_ALL} | Elapsed: {Fore.YELLOW}{elapsed_hours:.1f}h{Style.RESET_ALL} | Remaining: {Fore.YELLOW}{remaining_hours:.1f}h{Style.RESET_ALL}",end="\r",)

        await asyncio.sleep(min(update_interval, remaining))

    print(f"✅ Wait {Fore.GREEN}completed! bang{Style.RESET_ALL}")


# Bang welcome banner
def print_welcome_message():
    welcome_banner = f"""
{Fore.YELLOW}
 ██████╗██╗   ██╗ █████╗ ███╗   ██╗███╗   ██╗ ██████╗ ██████╗ ███████╗
██╔════╝██║   ██║██╔══██╗████╗  ██║████╗  ██║██╔═══██╗██╔══██╗██╔════╝
██║     ██║   ██║███████║██╔██╗ ██║██╔██╗ ██║██║   ██║██║  ██║█████╗  
██║     ██║   ██║██╔══██║██║╚██╗██║██║╚██╗██║██║   ██║██║  ██║██╔══╝  
╚██████╗╚██████╔╝██║  ██║██║ ╚████║██║ ╚████║╚██████╔╝██████╔╝███████╗
 ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝
{Style.RESET_ALL}
{Fore.CYAN}=============================================================={Style.RESET_ALL}
{Fore.MAGENTA}    Welcome to Footprint Onchain Testnet & Mainnet Interactive {Style.RESET_ALL}
{Fore.YELLOW}        - CUANNODE By Greyscope&Co, Credit By Arcxteam -        {Style.RESET_ALL}
{Fore.CYAN}=============================================================={Style.RESET_ALL}
"""
    print(welcome_banner)

def get_contract_types_for_deployment(num_contracts=3):
    """Get random contract types for deployment"""
    contract_types = list(CONTRACTS.keys())
    random.shuffle(contract_types)
    selected_types = contract_types[:num_contracts]

    print(f"🔍 Selected contract types: {Fore.YELLOW}{', '.join(selected_types)}{Style.RESET_ALL}")
    return selected_types


async def main():
    print_welcome_message()

    private_keys = load_private_keys()
    if not private_keys:
        print_error(f"❌ No private keys found. Please check your .env file or private_keys.txt")
        return

    try:
        w3, current_rpc = connect_to_rpc()
    except ConnectionError as e:
        print_error(f"❌ {str(e)}")
        return

    valid_wallets = []
    print(f"\n📊{Fore.YELLOW} Checking wallet balances:{Style.RESET_ALL}")

    for idx, private_key in enumerate(private_keys):
        try:
            account = w3.eth.account.from_key(private_key)
            wallet_address = account.address

            balance = w3.eth.get_balance(wallet_address)
            balance_eth = w3.from_wei(balance, "ether")

            print(f"   Wallet {idx+1}: {Fore.CYAN}{short_address(wallet_address)}{Style.RESET_ALL} | Balance: {Fore.YELLOW}{balance_eth:.6f} A0GI{Style.RESET_ALL}")

            if balance_eth >= 0.05:
                valid_wallets.append(private_key)
            else:
                print_warning(f"   ⚠️ Low balance (< 0.05 0G) for wallet {short_address(wallet_address)}, may not be sufficient for gas")
        except Exception as e:
            print_error(f"   ❌ Error checking wallet {idx+1}: {str(e)}")

    if not valid_wallets:
        print_error(f"❌ No wallets with sufficient balance found. Please fund your wallets")
        return

    chain_id = w3.eth.chain_id
    print(f"\n📊{Fore.YELLOW} Network Info:{Style.RESET_ALL}")
    print(f"   Chain ID: {chain_id} {Fore.MAGENTA}0G-Newton-Testnet {Style.RESET_ALL}")
    print(f"   Connected to RPC: {Fore.GREEN}{w3.provider.endpoint_uri}{Style.RESET_ALL}")

    # Get the total number of contracts to deploy 2
    total_contracts_per_wallet = 2
    total_contracts = len(valid_wallets) * total_contracts_per_wallet

    print(f"🚀{Fore.YELLOW} Will deploy {total_contracts} contracts total ({total_contracts_per_wallet} per wallet){Style.RESET_ALL}")
    print(f"   Strategy: Deploy contracts sequentially across all wallets first, then wait 7-8 hours between cycles")
    print(f"   Estimated completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} + 24 hours")
    print(f"   No user interaction will be required during the 24-hour period.")
    print(f"   Deploy results will {Fore.RED}not be saved{Style.RESET_ALL} in favour of keeping the {Fore.GREEN}folder clean{Style.RESET_ALL}")
    print(f"   Wallet rotation will occur with {Fore.CYAN}2-5 minute{Style.RESET_ALL} delays between wallets")

    print(f"{Fore.MAGENTA}⚠️ Starting in 13 seconds. Press Ctrl+C to cancel...{Style.RESET_ALL}")
    try:
        for i in range(13, 0, -1):
            print(f"{Fore.YELLOW} Starting in {i} seconds...{Style.RESET_ALL}", end="\r")
            await asyncio.sleep(1)
        print(f"{Fore.GREEN} Starting now!{Style.RESET_ALL}")
    except KeyboardInterrupt:
        print_error(f"Deployment cancelled by user.")
        return

    deployments = []

    contract_types_per_wallet = {}
    for wallet_key in valid_wallets:
        contract_types_per_wallet[wallet_key] = get_contract_types_for_deployment(
            total_contracts_per_wallet)

    for cycle in range(total_contracts_per_wallet):
        cycle_start_time = datetime.now()
        print(f"\n{Fore.CYAN}== Starting deployment cycle {cycle+1}/{total_contracts_per_wallet} at {cycle_start_time.strftime('%Y-%m-%d %H:%M:%S')} =={Style.RESET_ALL}")

        for wallet_idx, wallet_key in enumerate(valid_wallets):
            wallet_account = w3.eth.account.from_key(wallet_key)
            wallet_address = wallet_account.address

            contract_type = contract_types_per_wallet[wallet_key][cycle]
            contract_name = generate_random_name()

            deployment_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"\n{Fore.BLUE}══════════════════════════════════════════════════{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{Style.BRIGHT}🔨 Wallet {wallet_idx+1}/{len(valid_wallets)} Deployment {cycle+1}/{total_contracts_per_wallet} at {deployment_time}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{Style.BRIGHT}🔨 Using wallet: {Fore.YELLOW}{short_address(wallet_address)}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}🔨 Deploying: {Fore.YELLOW}{contract_name}{Style.RESET_ALL} ({Fore.CYAN}{contract_type}{Style.RESET_ALL})")
            print(f"{Fore.BLUE}══════════════════════════════════════════════════{Style.RESET_ALL}\n")

            if not w3.is_connected():
                print_warning("⚠️ RPC connection lost, attempting to reconnect...")
                try:
                    w3, current_rpc = switch_rpc(current_rpc)
                except:
                    try:
                        w3, current_rpc = connect_to_rpc()
                    except Exception as e:
                        print_error(f"❌ Failed to reconnect: {str(e)}")
                        continue

            deployment = await deploy_contract(
                w3, current_rpc, contract_type, contract_name, wallet_key)

            if deployment:
                deployment["wallet_address"] = wallet_address
                deployments.append(deployment)
                save_deployment_records(deployments)

                # Rotasi wallet dengan jeda random 2-5 menit
                if wallet_idx < len(valid_wallets) - 1:
                    wait_seconds = random.randint(CONFIG["WALLET_SWITCH_DELAY_MIN"], CONFIG["WALLET_SWITCH_DELAY_MAX"])
                    print_warning(f"⏳ Moving on to the next wallet in {wait_seconds} second (~{wait_seconds//60} minutes)")
                    await asyncio.sleep(wait_seconds)
            else:
                print_error(f"❌ Deployment failed for wallet {short_address(wallet_address)}. Moving to next wallet.")
                if wallet_idx < len(valid_wallets) - 1:
                    wait_seconds = random.randint(60, 120)  # 1-2 menit
                    print_warning(f"⏳ Moving on to the next wallet in {wait_seconds} detik if failed")
                    await asyncio.sleep(wait_seconds)

        if cycle < total_contracts_per_wallet - 1:
            # Random wait time between 7-8 hours
            wait_hours = random.uniform(7.0, 8.0)
            await wait_with_progress(wait_hours,f"Completed cycle {cycle+1}/{total_contracts_per_wallet}. Waiting for next cycle",)

    if deployments:
        save_deployment_records(deployments)

    print(f"\n✅ All deployments completed {Fore.GREEN}successfully{Style.RESET_ALL} over 24 hours!")
    print(f"✅ Total contracts deployed: {Fore.YELLOW}{len(deployments)}/{total_contracts}{Style.RESET_ALL}")
    print(f"✅ Deployment records not saved to JSON file.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}Script interrupted by user.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ An error occurred: {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
