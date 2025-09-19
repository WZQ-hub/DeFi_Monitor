from web3 import Web3

# Connect to the Ethereum network
w3 = Web3(Web3.HTTPProvider('https://eth-mainnet.g.alchemy.com/v2/JEJmfRm0uQhy2nfe-Ff0-'))

a = w3.eth.get_block('latest')
# 4. 检查是否连接成功
if w3.is_connected():
    print("🎉 Successfully connected to the Ethereum network!")
    print(a)
else:
    print("❌ Failed to connect to the Ethereum network.")
    exit() # 如果连接失败，则退出脚本

# 5. 获取最新区块号
try:
    latest_block_number = w3.eth.block_number
    print(f"✅ The latest block number on Ethereum is: {latest_block_number}")

except Exception as e:
    print(f"An error occurred: {e}")