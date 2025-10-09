import logging.config
import logging
import requests
from Defi_Monitor.settings import LOGGING
from binance_alpha.models import alpha



logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)


REQUEST_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"


def get_binance_alpha_token_list():
    '''
    调用币安API，获取所有可用的Binance Alpha代币列表。
    '''
    try:
        response = requests.request("GET", REQUEST_URL)
        response.raise_for_status()
        api_data = response.json()

        if api_data.get("code") == "000000" and api_data.get("success") == True:
            logger.info("成功获取到数据！！！")
            logger.info(f"总共有{len(api_data.get('data'))} 个alpha代币")

            return api_data.get("data")
    except Exception as e:

        logger.error(f"请求数据失败，错误信息：{e}")


def get_top10_and_high_mulPoint():
    '''
    获取前10名和高倍数的代币信息
    '''
    token_list = get_binance_alpha_token_list()
    if not token_list:
        logger.error("未能获取到代币列表，无法继续处理。")
        return

    # 按照mulPoint降序排序
    sorted_tokens = sorted(token_list, key = lambda x: x.get('mulPoint'), reverse = True)
    top10_tokens = sorted_tokens[:10]

    # 按交易量返回
    top10 = sorted(top10_tokens, key = lambda x: x.get('volume24h'), reverse = True)

    return top10

def save_token_info():
    '''
    保存代币信息到数据库
    '''
    token_info = get_top10_and_high_mulPoint()
    if not token_info:
        logger.error("未能获取到代币信息，无法保存。")
        return

    for token in token_info:
        try:
            obj, created = alpha.objects.update_or_create(
                tokenId = token.get('alphaId'),
                chainName = token.get('chainName'),
                contractAddress = token.get('contractAddress'),
                name = token.get('name'),
                symbol = token.get('symbol'),
                mulPoint = token.get('mulPoint'),
                price = token.get('price'),
                percentChange24h = token.get('percentChange24h'),
                volume24h = token.get('volume24h'),
                liquidity = token.get('liquidity')
            )
            if created:
                logger.info(f"创建新代币记录: {obj.symbol}")
            else:
                logger.info(f"更新代币记录: {obj.symbol}")
        except Exception as e:
            logger.error(f"保存代币信息失败，错误信息：{e}")

