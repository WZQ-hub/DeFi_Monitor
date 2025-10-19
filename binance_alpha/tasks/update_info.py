import logging
import logging.config
from http.client import responses

from Defi_Monitor.settings import LOGGING
import requests
from celery import shared_task
from binance_alpha.models import alpha

logging.config.dictConfig(LOGGING)

URL_KLINE = "https://www.binance.com/bapi/defi/v1/public/alpha-trade/klines"
logger = logging.getLogger(__name__)
REQUEST_PARAMS = {
    "symbol": "",
    "interval": "5m",
    "limit": 5
}


def get_tokenId():
    return list(alpha.objects.values_list("tokenId", flat=True))


def get_5min_info():
    '''
    获取5分钟的K线数据
    '''
    data_dict = {}
    symbols = get_tokenId()
    try:
        for symbol in symbols:
            REQUEST_PARAMS["symbol"] = symbol + "USDT"
            response = requests.get(URL_KLINE, params=REQUEST_PARAMS, timeout=10)
            response.raise_for_status()
            api_data = response.json()
            if api_data.get("code") == "000000" and api_data.get("success") is True:
                data = api_data.get('data') or []
                data_dict[symbol] = api_data.get('data')
                logger.info(f"成功获取到数据！！！ symbol={symbol} data={data}")
            else:
                # 业务错误也进行日志记录
                logger.error(f"API业务返回异常: code={api_data.get('code')} message={api_data.get('message')}")

    except Exception as e:
        logger.error(f"出现错误🙅{e}")


def compute_ATRP(symbol : str):
    '''
    计算 ATRP 指标
    '''
    ATR_PRE = 0.0
    data = DATA_DICT[symbol]
    for i in range(1, len(data)):
        current_high = float(data[i][2])
        current_low = float(data[i][3])
        current_close_price = float(data[i][4])
        TR_i = max((current_high - current_low),
                   abs(current_high - data[i-1][4]),
                   abs(current_low - data[i-1][4])
                    )
        ATR_C = (ATR_PRE * (len(SYMBOLS) - 1) + TR_i) / len(SYMBOLS)
        ATR_PCT = (ATR_C / current_close_price) * 100
        ATR_PRE = ATR_C
        logger.info(f"ATR_PCT={ATR_PCT}")


@shared_task
def get_5min_info_task():
    '''
    异步获取5分钟的K线数据
    '''
    get_5min_info()

@shared_task
def compute_ATRP_task(symbol: str):
    '''
    异步计算 ATRP 指标
    '''
    compute_ATRP(symbol)
