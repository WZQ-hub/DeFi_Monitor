import web3
from web3 import Web3
import time

URL = "https://eth-mainnet.g.alchemy.com/v2/JEJmfRm0uQhy2nfe-Ff0-"
w3 = Web3(Web3.HTTPProvider(URL))


def get_block(block_number):
    block = w3.eth.get_block(block_number)
    print(f"区块 {block_number} 的交易数量: {len(block['transactions'])}")


def main():
    if not w3.is_connected():
        print("连接失败")
        return

    latest_block_number = w3.eth.get_block_number()
    target_blocks = [latest_block_number - i for i in range(5)]

    print("--- 开始同步串行获取 ---")
    start_time = time.perf_counter()

    # 只能用 for 循环一个一个获取
    for n in target_blocks:
        get_block(n)

    end_time = time.perf_counter()
    print(f"--- 同步串行总耗时: {end_time - start_time:.4f} 秒 ---")


if __name__ == "__main__":
    main()