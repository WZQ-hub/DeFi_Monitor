from web3 import Web3

# Connect to the Ethereum network
w3 = Web3(Web3.HTTPProvider('https://eth-mainnet.g.alchemy.com/v2/JEJmfRm0uQhy2nfe-Ff0-'))

# 1. 导入 Web3 库
import os

# 2. 从 Alchemy 获取你的 API URL
# 最佳实践：建议使用环境变量来存储你的API URL，而不是直接写在代码里。
# 这里为了方便初学者，我们先直接写入。
# 替换成你自己的 Alchemy HTTPS URL

# 4. 检查是否连接成功
if w3.is_connected():
    print("🎉 Successfully connected to the Ethereum network!")
else:
    print("❌ Failed to connect to the Ethereum network.")
    exit() # 如果连接失败，则退出脚本

# 5. 获取最新区块号
try:
    latest_block_number = w3.eth.block_number
    print(f"✅ The latest block number on Ethereum is: {latest_block_number}")

except Exception as e:
    print(f"An error occurred: {e}")