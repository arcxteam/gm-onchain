# A Completed Guides Running GM-Vote Onchain All EVM Networks for Testnet & Mainnet Interaction

![gm-onchain-Codespaces-ominous](https://github.com/user-attachments/assets/ee335ddf-13aa-4667-8692-894ff02ad492)

**`Is there safe?` ![rating](https://img.shields.io/badge/-★★★★★-brightgreen)**

> [!IMPORTANT]
> I am not responsible for any loss or damage caused by this automation. Use it at your own risk, but I'm assured that it's safe since the smart contract has been verified and it's only limited to farming tx/id on testnet or mainnet. Let's start with a simple greeting, like **Good Morning**
## 🦾 Script Features
- Fallback gwei-gas direct to API-RPC to implement `EIP-1559` or `Legacy mode` for low cost/fees
- Automated running with natural behavior patterns `(Canceled on purpose & retry, Variable human-like, Nighty mode detect, Deviation, Cycle and more)`
- Automated single call `gM`|`Vote`|`Swapping`|`Deploy` every minutes/hours/daily
- Automated random `rotating` & batch `cycle` and more
- Automated running `24/7`
- Clean & informative any logger info
- Support `Testnet & Mainnet`
- Support multi account w/ `private_keys.txt`
- Support Windows/Linux/Termux
- Running on PM2 `(procesess management)`
- **ALL FEATURES FUNCTIONs CHECK TO `CONFIG` or TEST RUNNING-LOGS**

## Structure of directory files

```diff
 📂 root/gm-onchain
 ┣ 📂 monad
 ┃ ┣ 📜 .env
 ┃ ┣ 📜 gmonad.py
 ┃ ┣ 📜 uniswap.py
 ┃ ┣ 📜 curvance.py
 ┃ ┣ 📜 private_keys.txt
 ┃ ┣ 📜 requirements.txt
+┣ 📂 ink
+┃ ┣ 📜 voting.py
+┃ ┣ 📜 gmofficial.py
+┃ ┣ 📜 ........
-┣ 📂 ...and more
```
## Another list surge the on-chain footprint 

| Project List    | SuperChain / EVM      | Mainnet   | Testnet |
|-----------------|-----------------|-------------|-------------------|
| MONAD   | ![Confirm](https://img.shields.io/badge/EVM-YES-8a2be2) | ![Confirm](https://img.shields.io/badge/-NO-8a2be2) | ![Confirm](https://img.shields.io/badge/-YES-brightgreen) |
| NEXUS   | ![Confirm](https://img.shields.io/badge/EVM-YES-8a2be2) | ![Confirm](https://img.shields.io/badge/-NO-8a2be2) | ![Confirm](https://img.shields.io/badge/-YES-brightgreen) |
| Ink   | ![Confirm](https://img.shields.io/badge/Superchain-YES-8a2be2) | ![Confirm](https://img.shields.io/badge/-YES-brightgreen) | ![Confirm](https://img.shields.io/badge/-NO-8a2be2) |
| SONEIUM   | ![Confirm](https://img.shields.io/badge/Superchain-YES-8a2be2) | ![Confirm](https://img.shields.io/badge/-YES-brightgreen) | ![Confirm](https://img.shields.io/badge/-NO-8a2be2) |
| TAIKO   | ![Confirm](https://img.shields.io/badge/EVM-yes-8a2be2) | ![Confirm](https://img.shields.io/badge/-YES-brightgreen) | ![Confirm](https://img.shields.io/badge/-NO-8a2be2) |
| UniChain   | ![Confirm](https://img.shields.io/badge/Superchain-YES-8a2be2) | ![Confirm](https://img.shields.io/badge/-YES-brightgreen) | ![Confirm](https://img.shields.io/badge/-NO-8a2be2) |
| WorldChain   | ![Confirm](https://img.shields.io/badge/Superchain-YES-8a2be2) | ![Confirm](https://img.shields.io/badge/-YES-brightgreen) | ![Confirm](https://img.shields.io/badge/-NO-8a2be2) |
| Lisk   | ![Confirm](https://img.shields.io/badge/Superchain-YES-8a2be2) | ![Confirm](https://img.shields.io/badge/-YES-brightgreen) | ![Confirm](https://img.shields.io/badge/-NO-8a2be2) |
| SuperSeed   | ![Confirm](https://img.shields.io/badge/Superchain-YES-8a2be2) | ![Confirm](https://img.shields.io/badge/-YES-brightgreen) | ![Confirm](https://img.shields.io/badge/-NO-8a2be2) |

## How to do...?
`Requirements`
- **EVM** Wallet Address
- **Python** have 3.3 or latest and depedency modul
- **npm** have npm installed
- **Pm2** have processing manager 2 installed
- VPS or RDP (OPTIONAL)

## Setup Installation

- Install Python For Windows [Python](https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe)
- Install Python For `(1)` Linux and `(2)` Termux
```bash
apt install python3 python3-pip git -y
```
```bash
pkg install python python-pip git -y
```
## Clone Repository
```bash
git clone https://github.com/arcxteam/gm-onchain.git
cd gm-onchain
```
---

### STEP TO USE

```diff
> this example go to each directory
- cd gm-onchain/monad
- cd gm-onchain/soneium
- cd gm-onchain/ink

> Install processing manager 2 (if not yet)
- npm install -g pm2

> Input your private keys wallet address chosee one (.env) or (private_keys.txt)
- nano private_keys.txt
- nano .env

> Install depedency modul (1) Windows/Termux and (2) Linux
- pip install -r requirements.txt
- pip3 install -r requirements.txt

> Run at first time
- python3 curvance.py
- python3 voting.py
+ This example for runnig name `py` and go to each folders
+ So, close the logs with command `CTRL+C`

> Run at second time with PM2 background
- pm2 start curvance.py --name monad-pump
- pm2 start voting.py --name monad-vote
- pm2 start voting.py --name ink-vote

> Note; in folder like gm-onchain/monad id you can run to all
- pm2 start ecosystem.config.js
```

## Example Usefull Command Logs
- Status logs `pm2 logs monad-pump`
- Status stop/delete `pm2 stop monad-pump` `pm2 delete monad-pump`
- Status monitor `pm2 status` `pm2 monit` `pm2 list`
