import logging
import logging.config
from http.client import responses

from Defi_Monitor.settings import LOGGING
import requests
from celery import shared_task
from binance_alpha.models import alpha

logging.config.dictConfig(LOGGING)

URL_KLINE = "https://www.binance.com/bapi/defi/v1/public/alpha-trade/klines?interval=1h&limit=2&symbol=ALPHA_175USDT"
logger = logging.getLogger(__name__)
REQUEST_PARAMS = {
    "symbol": "",
    "interval": "5m",
    "limit": 1
}




def get_5min_info():
    '''
    获取5分钟的K线数据
    '''
    try:
        symbols = alpha.objects.values_list("symbol", flat=True)
        for symbol in symbols:
            REQUEST_PARAMS["symbol"] = symbol

            response = requests.get(URL_KLINE, params=REQUEST_PARAMS, timeout=10)
            response.raise_for_status()
            api_data = response.json()
            if api_data.get("code") == "000000" and api_data.get("success") is True:
                data = api_data.get('data') or []
                logger.info(f"成功获取到数据！！！ symbol={symbol} data={data}")
            else:
                # 业务错误也进行日志记录
                logger.error(f"API业务返回异常: code={api_data.get('code')} message={api_data.get('message')}")
