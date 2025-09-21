import pprint
import time

from web3 import Web3

# Connect to the Ethereum network
w3 = Web3(Web3.HTTPProvider('https://eth-mainnet.g.alchemy.com/v2/JEJmfRm0uQhy2nfe-Ff0-'))

a = w3.eth.get_block('latest')
# 5. 获取最新区块号
try:
    latest_block_number = w3.eth.block_number
    print(f"✅ The latest block number on Ethereum is: {latest_block_number}")
    print(w3.eth.get_balance("0x6e22f1FFf4Fd4cCc02430366E93727c9B7641489"))
    print(w3.eth.get_block(latest_block_number, full_transactions=True))

except Exception as e:
    print(f"An error occurred: {e}")
# 4. 检查是否连接成功
if w3.is_connected():
    print("🎉 Successfully connected to the Ethereum network!")
    print(a)
    print(w3.eth.get_block_transaction_count(latest_block_number))

else:
    print("❌ Failed to connect to the Ethereum network.")
    exit() # 如果连接失败，则退出脚本

