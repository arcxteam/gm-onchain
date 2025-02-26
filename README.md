# A Completed Guides Running GM-Onchain EVM-Wallet for Testnet & Mainnet Interaction

![pict](.png)

**`Is there safe?` ![rating](https://img.shields.io/badge/-★★★★★-brightgreen)**

> [!IMPORTANT]
> I am not responsible for any loss or damage caused by this automation. Use it at your own risk, but I'm assured that it's safe since the smart contract has been verified and it's only limited to farming tx/id on testnet or mainnet. Let's start with a simple greeting, like **Good Morning**
## 🦾 Script Features
- Fecthing call gwei/gas direct to API-RPC w/ implement `EIP-1559` or `Legacy mode` for low fees-cost
- Automated single call `gM` or `gMTo` every minutes/hours/daily
- Support `Testnet & Mainnet`
- Support multi account w/ `private_keys.txt`
- Support Windows/Linux/Termux
- Running on PM2 `(procesess management)`
- 

## Structure of directory files

```diff
 📂 root/gm-onchain
 ┣ 📂 monad
 ┃ ┣ 📜 .env
 ┃ ┣ 📜 gmonad.py
 ┃ ┣ 📜 monswap.py
 ┃ ┣ 📜 private_keys.txt
 ┃ ┣ 📜 requirements.txt
+┣ 📂 ink
+┃ ┣ 📜 gmink.py
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

---

## Setup Installation

- Install Python For Windows [Python](https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe)
- Install Python For `(1)` Linux and `(2)` Termux
```bash
apt install python3 python3-pip git -y
```
```bash
pkg install python python-pip git -y
```

**1. Clone this repository**
```bash
git clone https://github.com/arcxteam/gm-onchain.git
cd gm-onchain
```
```diff
> this example go to each directory
- cd gm-onchain/monad
- cd gm-onchain/soneium
- cd gm-onchain/ink
```

**2. Install processing manager 2 (if not yet)**
```bash
npm install -g pm2
```

**3. Input your private keys wallet address chosee one `.env` or `private_keys.txt`**
```bash
nano private_keys.txt
```
```bash
nano .env
```

**4. Install depedency modul (1) Windows/Termux and (2) Linux**
```bash
pip install -r requirements.txt
```
```bash
pip3 install -r requirements.txt
```

**5. Run at first time**
```bash
python3 gmonad.py
```
```bash
python3 gmink.py
```
- This example for runnig `py` and go to each folders
- So, close the logs with command `CTRL+C`

**6.  Run at second time with PM2**
```bash
pm2 start gmonad.py --name gm-monad
```
```bash
pm2 start gmnexus.py --name gm-ink
```
---

## Example Usefull Command Logs
- Status logs `pm2 logs gm-monad`
- Status stop/delete `pm2 stop gm-monad` `pm2 delete gm-monad`
- Status monitor `pm2 status` `pm2 monit` `pm2 list`
