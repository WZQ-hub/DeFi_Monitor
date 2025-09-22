import asyncio
import web3
from web3 import AsyncWeb3
import time

URL = "https://eth-mainnet.g.alchemy.com/v2/JEJmfRm0uQhy2nfe-Ff0-"
w3 = web3.AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(URL))


async def get_block(block_number):
    block = await w3.eth.get_block(block_number)
    print(f"区块 {block_number} 的交易数量: {len(block['transactions'])}")


async def main():
    if not await w3.is_connected():
        print("连接失败")
        return

    latest_block_number = await w3.eth.get_block_number()
    target_blocks = [latest_block_number - i for i in range(5)]  # 获取最近的5个区块

    print("--- 开始异步并发获取 ---")
    start_time = time.perf_counter()

    # 并发执行所有 get_block 任务
    await asyncio.gather(*(get_block(n) for n in target_blocks))

    end_time = time.perf_counter()
    print(f"--- 异步并发总耗时: {end_time - start_time:.4f} 秒 ---")


if __name__ == "__main__":
    asyncio.run(main())