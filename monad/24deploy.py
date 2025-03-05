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

# specific solidity compiler version
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
    
    function withdraw() public {
        require(msg.sender == beneficiary, "Only beneficiary can withdraw");
        payable(beneficiary).transfer(address(this).balance);
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

# Combine with the original contracts
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
    print(f"{Colors.HEADER}⚙️ Compiling {Colors.YELLOW}{contract_type}{Colors.HEADER} contract named {Colors.CYAN}{contract_name}{Colors.END}")
    
    contract_source = CONTRACTS[contract_type]
    source_contract_name = contract_type
    
    try:
        contract_data = compile_contract(contract_source, source_contract_name)
    except Exception as e:
        print(f"{Colors.RED}❌ Compilation failed: {str(e)}{Colors.END}")
        return None
    
    print(f"{Colors.GREEN}✅ Compilation successful{Colors.END}")
    
    # Get transaction account
    account = w3.eth.account.from_key(private_key)
    wallet_address = account.address
    
    # Get current balance
    balance = w3.eth.get_balance(wallet_address)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"{Colors.CYAN}💰 Current wallet balance --> {balance_eth:.6f} MON{Colors.END}")
    
    # Get current gas price and boosting 10%
    try:
        gas_price = w3.eth.gas_price
        increased_gas_price = max(int(gas_price * 1.05), w3.to_wei(50, 'gwei'))  
        print(f"{Colors.BLUE}💰 Using gas price --> {w3.from_wei(increased_gas_price, 'gwei')} gwei{Colors.END}")
    except Exception as e:
        print(f"{Colors.YELLOW}⚠️ Could not get gas price: {str(e)}{Colors.END}")
        increased_gas_price = w3.to_wei(50, 'gwei')  # edit gwei fallback
        print(f"{Colors.BLUE}💰 Using fallback gas price: 50 gwei{Colors.END}")
    
    contract = w3.eth.contract(abi=contract_data['abi'], bytecode=contract_data['bytecode'])
    
    # Build transaction
    nonce = w3.eth.get_transaction_count(wallet_address)
    
    gas_limit = 150000  # Default gas
    try:
        # Try to estimate gas
        estimated_gas = w3.eth.estimate_gas({
            'from': wallet_address,
            'data': contract_data['bytecode']
        })
        # Add 10% boosting
        gas_limit = int(estimated_gas * 1.05) # edit it
        print(f"{Colors.BLUE}⛽ Estimated gas --> {estimated_gas} --> edit... {gas_limit} with 10% boosting bang){Colors.END}")
    except Exception as e:
        print(f"{Colors.YELLOW}⚠️ Could not estimate gas: {str(e)}{Colors.END}")
        print(f"{Colors.BLUE}⛽ Using default gas limit: {gas_limit}{Colors.END}")
    
    # Calculate maximum gas cost
    max_gas_cost = gas_limit * increased_gas_price
    max_gas_cost_eth = w3.from_wei(max_gas_cost, 'ether')
    print(f"{Colors.BLUE}💲 Maximum gas cost --> {max_gas_cost_eth:.6f} MON{Colors.END}")
    
    if balance < max_gas_cost:
        print(f"{Colors.RED}❌ Insufficient balance for gas! Need {max_gas_cost_eth:.6f} MON but have {balance_eth:.6f} MON{Colors.END}")
        return None
    
    # Build transaction with approc gas seteup
    tx_data = contract.constructor().build_transaction({
        'from': wallet_address,
        'nonce': nonce,
        'gas': gas_limit,
        'gasPrice': increased_gas_price
    })
    
    print(f"{Colors.YELLOW}🚀 Deploying contract to blockchain...{Colors.END}")
    
    # Sign transaction
    signed_tx = w3.eth.account.sign_transaction(tx_data, private_key)
    
    try:
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"{Colors.BLUE}📨 Transaction explorer --> {w3.to_hex(tx_hash)}{Colors.END}")
        
        print(f"{Colors.YELLOW}⏳ Waiting for transaction confirmation...{Colors.END}")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        if tx_receipt.status == 1:
            contract_address = tx_receipt.contractAddress
            print(f"{Colors.GREEN}✅ Contract deployed successfully!{Colors.END}")
            print(f"{Colors.CYAN}📍 Contract Address --> {Colors.YELLOW}{contract_address}{Colors.END}")
            print(f"{Colors.CYAN}📝 Transaction TXiD/Hash --> {Colors.YELLOW}{w3.to_hex(tx_hash)}{Colors.END}")
            print(f"{Colors.CYAN}⛽ Gas used --> {tx_receipt.gasUsed} ({(tx_receipt.gasUsed / gas_limit) * 100:.1f}% no limit bang){Colors.END}")
            
            # Calculate actual gas cost
            actual_gas_cost = tx_receipt.gasUsed * increased_gas_price
            actual_gas_cost_eth = w3.from_wei(actual_gas_cost, 'ether')
            print(f"{Colors.CYAN}💲 Actual gas cost --> {actual_gas_cost_eth:.6f} MON{Colors.END}")
            
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
            print(f"{Colors.RED}❌ Deployment failed. Transaction status: {tx_receipt.status}{Colors.END}")
            try:
                tx_info = w3.eth.get_transaction(tx_hash)
                print(f"{Colors.RED}📊 Transaction details: Gas price {w3.from_wei(tx_info['gasPrice'], 'gwei')} gwei, Gas limit {tx_info['gas']}{Colors.END}")
            except:
                pass
            return None
            
    except Exception as e:
        print(f"{Colors.RED}❌ Error during deployment: {str(e)}{Colors.END}")
        return None

def save_deployment_records(deployments):
    """Save deployment records to a JSON file."""
    # Function is disabled to reduce files in directory
    print(f"{Colors.YELLOW} Deployment record saving is disabled{Colors.END}")
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
    update_interval = 1800  # progress every 30 menit 
    
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
        
        print(f"{Colors.YELLOW}⌛ Progress: {progress_percent:.1f}% | Elapsed: {elapsed_hours:.1f}h | Remaining: {remaining_hours:.1f}h{Colors.END}", end='\r')
        
        # Sleep for update interval
        await asyncio.sleep(min(update_interval, remaining))
    
    print(f"{Colors.GREEN}✅ Wait completed!{Colors.END}")

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
{Colors.CYAN}    Welcome to MONAD Onchain Testnet & Mainnet Interactive     {Colors.END}
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
            keys = [line.strip() for line in file.readlines()]
            private_keys.extend(keys)
    except Exception as e:
        print(f"{Colors.YELLOW}Note: private_keys.txt not found or couldn't be read: {e}{Colors.END}")

    if not private_keys:
        raise Exception("No private keys found in .env or private_keys.txt")

    print(f"{Colors.CYAN}📸 Loaded {len(private_keys)} EVM wallet(s) {Colors.GREEN}successfully{Colors.END}")
    
    return list(set(private_keys))

def get_contract_types_for_deployment(num_contracts=3):
    """Get random contract types for deployment"""
    # Get all available contract types
    contract_types = list(CONTRACTS.keys())
    random.shuffle(contract_types)
    selected_types = contract_types[:num_contracts]
    
    print(f"{Colors.CYAN}🔍 Selected contract types: {Colors.YELLOW}{', '.join(selected_types)}{Colors.END}")
    
    return selected_types

async def main():
    print_welcome_message()
    
    # Load private keys from env and file
    private_keys = load_private_keys()
    if not private_keys:
        print(f"{Colors.RED}❌ No private keys found. Please check your .env file or private_keys.txt{Colors.END}")
        return
    
    # tRY connect to RPC
    RPC_URLS = [
        "https://monad-testnet.g.alchemy.com/v2/G9UmvdH6oFBXk4Z_-fbJKt8m6wrdf6Ai",
        "https://testnet-rpc.monad.xyz",
        "https://monad-testnet.drpc.org"
    ]
    
    w3 = None
    for rpc_url in RPC_URLS:
        try:
            print(f"{Colors.YELLOW}🔄 Attempting to connect to RPC {rpc_url}...{Colors.END}")
            w3_temp = Web3(Web3.HTTPProvider(rpc_url))
            w3_temp.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            if w3_temp.is_connected():
                w3 = w3_temp
                print(f"{Colors.GREEN}✅ Successfully connected to RPC {rpc_url}{Colors.END}")
                break
        except Exception as e:
            print(f"{Colors.RED}❌ Failed to connect to {rpc_url}: {str(e)}{Colors.END}")
    
    if not w3 or not w3.is_connected():
        print(f"{Colors.RED}❌ Could not connect to any RPC endpoint{Colors.END}")
        return
    
    # Check all wallet balances and display info
    valid_wallets = []
    print(f"\n{Colors.BLUE}📊 Checking wallet balances:{Colors.END}")
    
    for idx, private_key in enumerate(private_keys):
        try:
            account = w3.eth.account.from_key(private_key)
            wallet_address = account.address
            
            balance = w3.eth.get_balance(wallet_address)
            balance_eth = w3.from_wei(balance, 'ether')
            
            print(f"{Colors.CYAN}   Wallet {idx+1}: {wallet_address[:6]}...{wallet_address[-4:]} | Balance: {Colors.YELLOW}{balance_eth:.6f} MON{Colors.END}")
            
            if balance_eth >= 0.05:
                valid_wallets.append(private_key)
            else:
                print(f"{Colors.YELLOW}   ⚠️ Low balance (< 0.05 MON), may not be sufficient for gas{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}   ❌ Error checking wallet {idx+1}: {str(e)}{Colors.END}")
    
    if not valid_wallets:
        print(f"{Colors.RED}❌ No wallets with sufficient balance found. Please fund your wallets.{Colors.END}")
        return
    
    chain_id = w3.eth.chain_id
    print(f"\n{Colors.BLUE}📊 Network Info:{Colors.END}")
    print(f"{Colors.CYAN}   Chain ID: {chain_id} Monad Testnet {Colors.END}")
    print(f"{Colors.CYAN}   Connected to RPC: {w3.provider.endpoint_uri}{Colors.END}")
    
    # Number of contracts to deploy
    num_contracts = 3
    
    print(f"{Colors.BLUE}🚀 Will deploy {num_contracts} contracts over 24h/Daily with approximately 8-hour intervals{Colors.END}")
    print(f"{Colors.YELLOW}⏱️  Estimated completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} + 24 hours{Colors.END}")
    print(f"{Colors.YELLOW}📋 No user interaction will be required during the 24-hour period.{Colors.END}")
    print(f"{Colors.YELLOW}📝 Results will be saved to a JSON file when complete.{Colors.END}")
    
    # Give user 13 seconds to cancel if needed
    print(f"{Colors.RED}⚠️ Starting in 13 seconds. Press Ctrl+C to cancel...{Colors.END}")
    try:
        for i in range(13, 0, -1):
            print(f"{Colors.RED}Starting in {i} seconds...{Colors.END}", end='\r')
            await asyncio.sleep(1)
        print(f"{Colors.GREEN}Starting now!{Colors.END}")
    except KeyboardInterrupt:
        print(f"{Colors.RED}Deployment cancelled by user.{Colors.END}")
        return
    
    # Deployments array
    deployments = []
    
    # Get random contract types to deploy
    contract_types = get_contract_types_for_deployment(num_contracts)
    
    # Distribute wallets evenly across deployments
    # If wallets < contracts, some wallets will be used multiple times
    # If wallets >= contracts, each contract gets a unique wallet
    wallet_cycle = valid_wallets.copy()
    random.shuffle(wallet_cycle)
    
    # Deploy contracts over 24 hours & cycling available wallets
    for i, contract_type in enumerate(contract_types):
        deployment_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not wallet_cycle:
            wallet_cycle = valid_wallets.copy()
            random.shuffle(wallet_cycle)
            
        current_private_key = wallet_cycle.pop(0)
        current_account = w3.eth.account.from_key(current_private_key)
        current_address = current_account.address
        
        # Generate random name
        contract_name = generate_random_name()
        
        print(f"\n{Colors.BLUE}══════════════════════════════════════════════════{Colors.END}")
        print(f"{Colors.BOLD}🔨 Contract {i+1}/{len(contract_types)} at {deployment_time}{Colors.END}")
        print(f"{Colors.BOLD}🔨 Using wallet: {Colors.YELLOW}{current_address[:6]}...{current_address[-4:]}{Colors.END}")
        print(f"{Colors.BOLD}🔨 Deploying: {Colors.YELLOW}{contract_name}{Colors.END} ({Colors.CYAN}{contract_type}{Colors.END})")
        print(f"{Colors.BLUE}══════════════════════════════════════════════════{Colors.END}\n")
        
        # Deploy contract
        deployment = await deploy_contract(w3, contract_type, contract_name, current_private_key)
        
        if deployment:
            deployment['wallet_address'] = current_address
            deployments.append(deployment)
            
            # Save current results after each successful deployment
            save_deployment_records(deployments)
            
            # If not the last deployment, wait for ~8 hours
            if i < len(contract_types) - 1:
                # Add some randomness to the wait time (7-9 hours)
                wait_hours = random.uniform(7.0, 9.0)
                await wait_with_progress(wait_hours, f"Waiting for next deployment ({i+2}/{len(contract_types)})")
    
    if deployments:
        save_deployment_records(deployments)
    
    print(f"\n{Colors.GREEN}✅ All deployments completed successfully over 24 hours!{Colors.END}")
    print(f"{Colors.GREEN}✅ Total contracts deployed: {len(deployments)}/{len(contract_types)}{Colors.END}")
    print(f"{Colors.GREEN}✅ Deployment records saved to JSON file.{Colors.END}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Script interrupted by user.{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ An error occurred: {str(e)}{Colors.END}")