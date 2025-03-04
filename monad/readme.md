# MONAD TESNET AUTO

## Run every skrip with type

- Go to directory file
```
cd gm-onchain/monad
```
- Install processing manager 2 (if not yet)
```bash
npm install -g pm2
```
- Install depedency modul
```
pip3 install -r requirements.txt
```
```diff
> Running first time
- python3 24deploy.py | python3 gmonad.py | python3 uniswap.py | python3 aprio.py | python3 generate.py
+ Note; Every run above you need CMD this for end CTRL+C..next step run at background with manages

> Running second time for background
- pm2 start 24deploy.py --name monad-deploy
- pm2 start gmonad.py --name monad-gm
- pm2 start uniswap.py --name monad-uniswap
- pm2 start aprio.py --name monad-aprio
- pm2 start generate.py --name monad-wallet

> Info logs & status
- pm2 status or pm2 list
- pm2 logs monad-deploy
- pm2 logs monad-gm
- pm2 logs monad-uniswap
- pm2 logs monad-aprio
- pm2 logs monad-wallet
```
