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

# solidity compiler version
try:
    install_solc('0.8.17')
except Exception as e:
    print(f"Warning: Could not install solc 0.8.17, will use available version. Error: {e}")

load_dotenv()

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

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
"""
}

CONTRACTS = {}
CONTRACTS.update(SIMPLE_CONTRACTS)

def generate_random_name(length=10):
    """Generate a random contract name."""
    adjectives = ["Smart", "Crypto", "Chain", "Block", "Decentralized", "Secure", "Digital", 
                  "Dynamic", "Quantum", "Virtual", "Atomic", "Hyper", "Rapid", "Logic", "Cosmic"]
    
    nouns = ["Vault", "Ledger", "Registry", "Wallet", "Guardian", "Nexus", "Protocol", 
             "Token", "Oracle", "Network", "Hub", "Engine", "Portal", "Matrix", "Core"]
    
    adjective = random.choice(adjectives)
    noun = random.choice(nouns)
    
    digits = ''.join(random.choices(string.digits, k=3))
    
    # Generate a name with AdjNounXXXbang
    return f"{adjective}{noun}{digits}"

def compile_contract(contract_source, contract_name):
    """Compile Solidity contract and return bytecode and ABI."""
    compiled_sol = compile_source(
        contract_source,
        output_values=['abi', 'bin'],
        solc_version='0.8.17'
    )
    
    contract_key = f'<stdin>:{contract_name}'
    contract_interface = compiled_sol[contract_key]
    
    return {
        'abi': contract_interface['abi'],
        'bytecode': contract_interface['bin']
    }

async def deploy_contract(w3, contract_type, contract_name, private_key):
    """Deploy a contract and return its details."""
    print(f"⚙️ {Colors.HEADER} Compiling {Colors.YELLOW}{contract_type}{Colors.HEADER} the contract name is {Colors.YELLOW}{contract_name}{Colors.END}")
    
    contract_source = CONTRACTS[contract_type]
    source_contract_name = contract_type
    
    try:
        contract_data = compile_contract(contract_source, source_contract_name)
    except Exception as e:
        print(f"❌  Compilation {Colors.RED}failed: {str(e)}{Colors.END}")
        return None
    
    print(f"✅ Compilation {Colors.GREEN}successful{Colors.END}")
    
    account = w3.eth.account.from_key(private_key)
    wallet_address = account.address
    
    # Get current balance
    balance = w3.eth.get_balance(wallet_address)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"🤑 Current wallet balance: {Colors.YELLOW}{balance_eth:.6f} MON{Colors.END}")
    
    try:
        gas_price = w3.eth.gas_price
        increased_gas_price = max(int(gas_price * 1.005), w3.to_wei(50, 'gwei'))  
        print(f"💰 Using gas price: {Colors.YELLOW}{w3.from_wei(increased_gas_price, 'gwei')} gwei{Colors.END}")
    except Exception as e:
        print(f"{Colors.HEADER}⚠️ Could not get gas price: {str(e)}{Colors.END}")
        increased_gas_price = w3.to_wei(50, 'gwei')  # edit gwei fallback
        print(f"{Colors.HEADER}💰 Using fallback gas price: 50 gwei{Colors.END}")
    
    contract = w3.eth.contract(abi=contract_data['abi'], bytecode=contract_data['bytecode'])
    
    # Build transaction
    nonce = w3.eth.get_transaction_count(wallet_address)
    
    gas_limit = 150001
    try:
        # Try to estimate gas
        estimated_gas = w3.eth.estimate_gas({
            'from': wallet_address,
            'data': contract_data['bytecode']
        })
        # Add 10% boosting
        gas_limit = int(estimated_gas * 1.005) # edit can
        print(f"⛽ Estimated gas: {Colors.YELLOW}{estimated_gas}{Colors.END} -> Boosting gas 5%...{Colors.YELLOW}{gas_limit}{Colors.END}")
    except Exception as e:
        print(f"{Colors.HEADER}⚠️ Could not estimate gas: {str(e)}{Colors.END}")
        print(f"⛽ Using default gas limit: {Colors.YELLOW}{gas_limit}{Colors.END}")
    
    # Calculate maximum gas cost
    max_gas_cost = gas_limit * increased_gas_price
    max_gas_cost_eth = w3.from_wei(max_gas_cost, 'ether')
    print(f"💲 Maximum gas cost: {Colors.YELLOW}{max_gas_cost_eth:.6f} MON{Colors.END}")
    
    if balance < max_gas_cost:
        print(f"❌ Insufficient balance for gas! isi bang {Colors.RED}{max_gas_cost_eth:.6f}{Colors.END} MON but have {Colors.YELLOW}{balance_eth:.6f} MON{Colors.END}")
        return None
    
    # Build transaction with approc gas seteup
    tx_data = contract.constructor().build_transaction({
        'from': wallet_address,
        'nonce': nonce,
        'gas': gas_limit,
        'gasPrice': increased_gas_price
    })
    
    print(f"{Colors.HEADER}🚀  Deploying contract to blockchain...WAIT...WAIT{Colors.END}")
    
    # Sign transaction
    signed_tx = w3.eth.account.sign_transaction(tx_data, private_key)
    
    try:
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"📨 Transaction explorer TXiD: {Colors.CYAN}{w3.to_hex(tx_hash)}{Colors.END}")
        
        print(f"{Colors.YELLOW}⏳ Waiting for transaction confirmation...{Colors.END}")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=130)
        
        if tx_receipt.status == 1:
            contract_address = tx_receipt.contractAddress
            print(f"✅{Colors.GREEN} Contract deployed successfully!{Colors.END}")
            print(f"📍 Contract Address: {Colors.YELLOW}{contract_address}{Colors.END}")
            print(f"📝 Transaction TXiD/Hash: {Colors.CYAN}{w3.to_hex(tx_hash)}{Colors.END}")
            print(f"⛽ Get gas used: {Colors.CYAN}{tx_receipt.gasUsed}{Colors.END} {Colors.GREEN}{(tx_receipt.gasUsed / gas_limit) * 100:.1f}% no limit bang{Colors.END}")
            
            # Calculate actual gas cost
            actual_gas_cost = tx_receipt.gasUsed * increased_gas_price
            actual_gas_cost_eth = w3.from_wei(actual_gas_cost, 'ether')
            print(f"💲 Actual gas cost: {Colors.YELLOW}{actual_gas_cost_eth:.6f} MON{Colors.END}")
            
            # Save contract details
            deployment_record = {
                'contract_type': contract_type,
                'contract_name': contract_name,
                'address': contract_address,
                'transaction_hash': w3.to_hex(tx_hash),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'gas_used': tx_receipt.gasUsed,
                'gas_price': w3.from_wei(increased_gas_price, 'gwei'),
                'total_cost': w3.from_wei(actual_gas_cost, 'ether'),
                'wallet_address': wallet_address,
                'abi': contract_data['abi']
            }
            
            return deployment_record
        else:
            print(f"❌ Deployment {Colors.RED}failed.{Colors.END} Transaction status: {Colors.RED}{tx_receipt.status}{Colors.END}")
            try:
                tx_info = w3.eth.get_transaction(tx_hash)
                print(f"📊 Transaction details: Gas price {Colors.YELLOW}{w3.from_wei(tx_info['gasPrice'], 'gwei')} gwei, Gas limit {tx_info['gas']}{Colors.END}")
            except:
                pass
            return None
            
    except Exception as e:
        print(f"❌ Error during deployment: {Colors.RED}{str(e)}{Colors.END}")
        return None

def save_deployment_records(deployments):
    """Save deployment records to a JSON file."""
    # Function is disabled to reduce files in directory
    print(f"⚙️ {Colors.HEADER} Deployment record saving is disabled{Colors.END}")
    # To enable the function, remove the line above and uncomment the code below
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # filename = f"deployments_{timestamp}.json"
    # try:
    #     with open(filename, 'w') as f:
    #         json.dump(deployments, f, indent=2)
    #     print(f"{Colors.GREEN} Deployment records saved to {filename}{Colors.END}")
    # except Exception as e:
    #     print(f"{Colors.RED} Failed to save deployment records: {str(e)}{Colors.END}")
    
async def wait_with_progress(hours, message="Waiting"):
    """Wait for specified hours with progress updates."""
    seconds = int(hours * 3600)
    update_interval = 2025  # progress every 33 menit 
    
    print(f"\n{Colors.YELLOW}⏳ {message} for approximately {hours:.1f} hours...{Colors.END}")
    
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
        
        print(f"⌛ Progress: {Colors.YELLOW}{progress_percent:.1f}%{Colors.END} | Elapsed: {Colors.YELLOW}{elapsed_hours:.1f}h{Colors.END} | Remaining: {Colors.YELLOW}{remaining_hours:.1f}h{Colors.END}", end='\r')
        
        # Sleep for update interval
        await asyncio.sleep(min(update_interval, remaining))
    
    print(f"✅ Wait a {Colors.GREEN}completed! bang{Colors.END}")

# Bang welcome banner
def print_welcome_message():
    welcome_banner = f"""
{Colors.YELLOW}
 ██████╗██╗   ██╗ █████╗ ███╗   ██╗███╗   ██╗ ██████╗ ██████╗ ███████╗
██╔════╝██║   ██║██╔══██╗████╗  ██║████╗  ██║██╔═══██╗██╔══██╗██╔════╝
██║     ██║   ██║███████║██╔██╗ ██║██╔██╗ ██║██║   ██║██║  ██║█████╗  
██║     ██║   ██║██╔══██║██║╚██╗██║██║╚██╗██║██║   ██║██║  ██║██╔══╝  
╚██████╗╚██████╔╝██║  ██║██║ ╚████║██║ ╚████║╚██████╔╝██████╔╝███████╗
 ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝
{Colors.END}
{Colors.GREEN}=============================================================={Colors.END}
{Colors.HEADER}    Welcome to MONAD Onchain Testnet & Mainnet Interactive     {Colors.END}
{Colors.YELLOW}     - CUANNODE By Greyscope&Co, Credit By Arcxteam -        {Colors.END}
{Colors.GREEN}=============================================================={Colors.END}
"""
    print(welcome_banner)

def load_private_keys():
    private_keys = []

    # Load from env
    env_private_key = os.getenv("PRIVATE_KEY")
    if env_private_key:
        private_keys.append(env_private_key.strip())

    # Try to load from private_keys.txt
    try:
        with open("private_keys.txt", "r") as file:
            keys = [line.strip() for line in file.readlines() if line.strip() and not line.strip().startswith('#')]
            private_keys.extend(keys)
    except Exception as e:
        print(f" Note: private_keys.txt not found or couldn't be read: {e}")

    if not private_keys:
        raise Exception("No private keys found in .env or private_keys.txt")

    print(f"📸 Loaded {len(private_keys)} EVM wallet {Colors.GREEN}Successfully{Colors.END}")
    
    # Remove duplicates but preserve order
    seen = set()
    unique_keys = []
    for key in private_keys:
        if key not in seen:
            seen.add(key)
            unique_keys.append(key)
    
    return unique_keys

def get_contract_types_for_deployment(num_contracts=3):
    """Get random contract types for deployment"""
    # Get all available contract types
    contract_types = list(CONTRACTS.keys())
    random.shuffle(contract_types)
    selected_types = contract_types[:num_contracts]
    
    print(f"🔍 Selected contract types: {Colors.YELLOW}{', '.join(selected_types)}{Colors.END}")
    
    return selected_types

async def main():
    print_welcome_message()
    
    # Load private keys from env and file
    private_keys = load_private_keys()
    if not private_keys:
        print(f"❌ No private keys found. Please check your .env file or private_keys.txt")
        return
    
    # Try connect to RPC
    RPC_URLS = [
        "https://testnet-rpc.monad.xyz",
        "https://monad-testnet.drpc.org",
        "https://monad-testnet.blockvision.org/v1/2td1EBS890QoVDhdSdd0Q1OlEGw"
    ]
    
    w3 = None
    for rpc_url in RPC_URLS:
        try:
            print(f"🔄 Already to connect RPC {Colors.RED}{rpc_url}{Colors.END}")
            w3_temp = Web3(Web3.HTTPProvider(rpc_url))
            w3_temp.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            if w3_temp.is_connected():
                w3 = w3_temp
                print(f"✅ Successfully connected to RPC {Colors.GREEN}{rpc_url}{Colors.END}")
                break
        except Exception as e:
            print(f"{Colors.RED}❌ Failed to connect to {rpc_url}: {str(e)}{Colors.END}")
    
    if not w3 or not w3.is_connected():
        print(f"{Colors.RED}❌ Could not connect to any RPC endpoint{Colors.END}")
        return
    
    # Check all wallet balances and display info
    valid_wallets = []
    print(f"\n📊{Colors.YELLOW} Checking wallet balances:{Colors.END}")
    
    for idx, private_key in enumerate(private_keys):
        try:
            account = w3.eth.account.from_key(private_key)
            wallet_address = account.address
            
            balance = w3.eth.get_balance(wallet_address)
            balance_eth = w3.from_wei(balance, 'ether')
            
            print(f"   Wallet {idx+1}: {Colors.CYAN}{wallet_address[:6]}...{wallet_address[-4:]}{Colors.END} | Balance: {Colors.YELLOW}{balance_eth:.6f} MON{Colors.END}")
            
            if balance_eth >= 0.05:
                valid_wallets.append(private_key)
            else:
                print(f" ⚠️ Low balance (< 0.05 MON), may not be sufficient for gas")
        except Exception as e:
            print(f"{Colors.RED}   ❌ Error checking wallet {idx+1}: {str(e)}{Colors.END}")
    
    if not valid_wallets:
        print(f" ❌ No wallets with sufficient balance found. Please fund your wallets")
        return
    
    chain_id = w3.eth.chain_id
    print(f"\n📊{Colors.YELLOW} Network Info:{Colors.END}")
    print(f"   Chain ID: {chain_id} {Colors.CYAN}Monad Testnet {Colors.END}")
    print(f"   Connected to RPC: {Colors.CYAN}{w3.provider.endpoint_uri}{Colors.END}")
    
    # Get the total number of contracts to deploy (3 per wallet by default)
    total_contracts_per_wallet = 3
    total_contracts = len(valid_wallets) * total_contracts_per_wallet
    
    # Improved message for efficient wallet rotation
    print(f"🚀{Colors.YELLOW} Will deploy {total_contracts} contracts total ({total_contracts_per_wallet} per wallet){Colors.END}")
    print(f"   Strategy: Deploy contracts sequentially across all wallets first, then wait 12-hour between cycles")
    print(f"   Estimated completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} + 24 hours")
    print(f"   No user interaction will be required during the 24-hour period.")
    print(f"   Deploy results will {Colors.RED}not be saved{Colors.END} in favour of keep the {Colors.GREEN}clean{Colors.END} folder + storage in use.")
    
    # Give user 13 seconds to cancel if needed
    print(f"{Colors.RED}⚠️ Starting in 13 seconds. Press Ctrl+C to cancel...{Colors.END}")
    try:
        for i in range(13, 0, -1):
            print(f"{Colors.YELLOW} Starting in {i} seconds...{Colors.END}", end='\r')
            await asyncio.sleep(1)
        print(f"{Colors.GREEN} Starting now!{Colors.END}")
    except KeyboardInterrupt:
        print(f"{Colors.RED} Deployment cancelled by user.{Colors.END}")
        return
    
    # Deployments array
    deployments = []
    
    # Get random contract types to deploy
    contract_types_per_wallet = {}
    for wallet_key in valid_wallets:
        contract_types_per_wallet[wallet_key] = get_contract_types_for_deployment(total_contracts_per_wallet)
        
    for cycle in range(total_contracts_per_wallet):
        cycle_start_time = datetime.now()
        print(f"\n{Colors.CYAN}======= Starting deployment cycle {cycle+1}/{total_contracts_per_wallet} at {cycle_start_time.strftime('%Y-%m-%d %H:%M:%S')} ======={Colors.END}")
        
        # Deploy one contract for each wallet in this cycle
        for wallet_idx, wallet_key in enumerate(valid_wallets):
            wallet_account = w3.eth.account.from_key(wallet_key)
            wallet_address = wallet_account.address
            
            contract_type = contract_types_per_wallet[wallet_key][cycle]
            contract_name = generate_random_name()
            
            deployment_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\n{Colors.BLUE}══════════════════════════════════════════════════{Colors.END}")
            print(f"{Colors.BOLD}🔨 Wallet {wallet_idx+1}/{len(valid_wallets)} Deployment {cycle+1}/{total_contracts_per_wallet} at {deployment_time}{Colors.END}")
            print(f"{Colors.BOLD}🔨 Using wallet: {Colors.YELLOW}{wallet_address[:6]}...{wallet_address[-4:]}{Colors.END}")
            print(f"{Colors.BOLD}🔨 Deploying: {Colors.YELLOW}{contract_name}{Colors.END} ({Colors.CYAN}{contract_type}{Colors.END})")
            print(f"{Colors.BLUE}══════════════════════════════════════════════════{Colors.END}\n")
            
            # Deploy contract
            deployment = await deploy_contract(w3, contract_type, contract_name, wallet_key)
            
            if deployment:
                deployment['wallet_address'] = wallet_address
                deployments.append(deployment)
                
                # Save current results after each successful deployment
                save_deployment_records(deployments)
                
                # Short wait between wallets within the same cycle (60-90 seconds)
                if wallet_idx < len(valid_wallets) - 1:
                    wait_seconds = random.randint(60, 90)
                    print(f"{Colors.YELLOW}⏳ Short delay wait in {wait_seconds} seconds before, next wallet deployment...{Colors.END}")
                    await asyncio.sleep(wait_seconds)
        
        # But only if this is not the last cycle wait 8 hours
        if cycle < total_contracts_per_wallet - 1:
            # Random wait time between 7-8 hours
            wait_hours = random.uniform(7.0, 8.0)
            await wait_with_progress(wait_hours, f"Completed cycle {cycle+1}/{total_contracts_per_wallet}. Waiting for next cycle")
    
    if deployments:
        save_deployment_records(deployments)
    
    print(f"\n ✅ All deployments completed {Colors.GREEN}successfully{Colors.END} over 24 hours!")
    print(f" ✅ Total contracts deployed: {Colors.YELLOW}{len(deployments)}/{total_contracts}{Colors.END}")
    print(f" ✅ Deployment records saved to JSON file.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.GREEN}Script interrupted by user.{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ An error occurred: {str(e)}{Colors.END}")
