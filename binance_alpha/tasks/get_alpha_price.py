import requests
import logging
import logging.config
from Defi_Monitor.settings import LOGGING
import redis
from binance_alpha.models import alpha
from celery import shared_task
import json


logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)
URL = "https://www.binance.com/bapi/defi/v1/public/alpha-trade/agg-trades"

r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

@shared_task
def get_alpha_params():
    '''
    获取 ALPHA 代币的请求参数。
    '''
    try:
        tokenId = alpha.objects.get(id = 3).tokenId
        params = {
            "symbol": tokenId,
            "limit": 5  # 限制返回结果数量为1 (默认为500，最大1000)
        }
        response = requests.get(url = URL, params = params)
        response.raise_for_status()
        data = response.json()
        if len(data) > 0:
            r.set(tokenId, json.dumps(data))
            logger.info(f"成功获取到 {tokenId} 的最新价格信息，并存储到 Redis 中。")
    except Exception as e:
        logger.error(f"获取 {tokenId} 价格信息失败，错误信息：{e}")
