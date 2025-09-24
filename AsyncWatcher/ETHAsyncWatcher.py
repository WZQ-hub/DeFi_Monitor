import asyncio
import web3
from web3 import *





URL = "https://eth-mainnet.g.alchemy.com/v2/JEJmfRm0uQhy2nfe-Ff0-"
w3 = web3.AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(URL))

async def fetch_block_and_print_tx_count():
    try:
        latest_block_number = await w3.eth.get_block_number()
        block = await w3.eth.get_block(latest_block_number)
        tx_count = len(block["transactions"])
        print(f"最新区块号: {latest_block_number}, 交易数量: {tx_count}")

    except Exception as e:
        print(e)
        print("❌出错了！！！")

async def main_loop():
    if not await w3.is_connected():
        print("没有连接到ETH！！！")
        return
    else: print("成功连接！！！")

    while True:
        await fetch_block_and_print_tx_count()
        await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(main_loop())