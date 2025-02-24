# A Completed Guides Running GM-Onchain Testnet & Mainnet Interaction

![pict](.png)

## Here We Go...GAS 

**`Is there safe?` ![Confirm](https://img.shields.io/badge/confirm-yes-brightgreen)**

> [!IMPORTANT]
> I am not responsible for any loss or damage caused by this automation interactive (bot). Use it at your own risk are farming network on mode testnet or mainnet tx/id. 

But I assured, that all of this is safe starting from the smart contract has been verified and this is only limited network test to hello to say as familiar GM (good morning) on-chain interactive.

## 🦾 Bot Features
- Note: I am not responsible for any loss or damage caused by this bot. Use it at your own risk are banned.
- Automated Daily Agent Interactions script.
- ~Connection by Proxy (support socks/5 http/s)~

## How to do...?
- Gokite.ai Account, Register here: [https://testnet.gokite.ai](https://testnet.gokite.ai/?r=Y2d9Cgy2)
- EVM Wallet Address, Please register using EVM wallet using `Avalanche Chain` and complete all tasks first
- Get faucet and add rpc here https://faucet.gokite.ai/
- VPS or RDP (OPTIONAL)

## Requirements
- **Python** have 3.7 or latest version and modul
- **npm** have npm installed
- **Pm2** have processing manager 2 installed

---

## Setup Installation

- Python For Windows [Python](https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe)
- Python For (1) Linux and (2) Termux
```bash
apt install python3 python3-pip git -y
```
```bash
pkg install python python-pip git -y
```

**1. Clone this repository**
```bash
git clone https://github.com/arcxteam/kit3ai.git
cd kit3ai
```

**2. Install processing manager 2 (if not yet)**
```bash
npm install -g pm2
```

**3. Fill your address wallet on `.env` or `tokens.txt` w/ command here**
```bash
nano tokens.txt
```
```bash
nano .env
```

**4. Install depedency modul (1) Win/Termux and (2) Linux**
```bash
pip install -r requirements.txt
```
```bash
pip3 install -r requirements.txt
```

**5. Run at first time**
```bash
python3 main.py
```
- So, close the logs with command `CTRL+C`

**6.  Run at second time with PM2**
```bash
pm2 start main.py --name kiteai-bot
```
---

## Usefull Command Logs
- Status logs
```bash
pm2 logs kiteai-bot
```
- Status stop/delete
```bash
pm2 stop kiteai-bot
```

```bash
pm2 delete kiteai-bot
```
- Status monitor
```bash
pm2 monit or list
```

## Notes
- Run this bot, use my referral code if you don't have one.
- You can just run this bot at your own risk, I'm not responsible for any loss or damage caused by this bot.
- This bot is for educational purposes only.
