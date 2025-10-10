import logging.config
import logging
import requests
from Defi_Monitor.settings import LOGGING
from binance_alpha.models import alpha
from celery import shared_task



logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)


REQUEST_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
REQUEST_TIMEOUT = 10


def get_binance_alpha_token_list():
    '''
    调用币安API，获取所有可用的Binance Alpha代币列表。
    返回 data 列表；若失败返回 None。
    '''
    try:
        response = requests.request("GET", REQUEST_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        api_data = response.json()

        if api_data.get("code") == "000000" and api_data.get("success") is True:
            data = api_data.get('data') or []
            logger.info("成功获取到数据！！！")
            logger.info(f"总共有{len(data)} 个alpha代币")
            return data
        else:
            # 业务错误也进行日志记录
            logger.error(f"API业务返回异常: code={api_data.get('code')} message={api_data.get('message')}")
            return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP错误: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"请求错误: {e}")
    except ValueError as e:
        # JSON 解析失败
        logger.error(f"解析JSON失败: {e}")
    return None


def _to_number(val, default=0):
    """将值安全转换为数字用于排序。"""
    try:
        if val is None:
            return default
        # 统一转为 float，适配字符串/数字
        return float(val)
    except (ValueError, TypeError):
        return default


def get_top10_and_high_mulPoint():
    '''
    获取前10名且高倍数（按 mulPoint 降序、再按 24h 交易量降序）的代币信息
    '''
    token_list = get_binance_alpha_token_list()
    if not token_list:
        logger.error("未能获取到代币列表，无法继续处理。")
        return None

    # 按照 mulPoint 降序排序，转换为数字更稳健
    sorted_tokens = sorted(token_list, key=lambda x: _to_number(x.get('mulPoint')), reverse=True)
    top10_tokens = sorted_tokens[:10]

    # 再按 24h 交易量降序返回
    top10 = sorted(top10_tokens, key=lambda x: _to_number(x.get('volume24h')), reverse=True)

    return top10


@shared_task(
    bind=True,
    autoretry_for=(requests.exceptions.RequestException, RuntimeError),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_jitter=True,
    acks_late=True,
    soft_time_limit=20,
)
def save_token_info(self):
    '''
    保存代币信息到数据库（Celery 任务）。
    成功返回保存/更新的记录数；失败时抛出异常以触发自动重试。
    '''
    token_info = get_top10_and_high_mulPoint()
    if not token_info:
        # 抛异常以触发自动重试
        raise RuntimeError("未能获取到代币信息，触发重试。")

    saved = 0
    for token in token_info:
        try:
            # 规范化字段值
            token_id = token.get('alphaId')
            chain_name = (token.get('chainName') or '').strip()
            contract_addr = (token.get('contractAddress') or '').lower().strip()
            try:
                mul_point = int(float(token.get('mulPoint') or 0))
            except (TypeError, ValueError):
                mul_point = 0

            obj, created = alpha.objects.update_or_create(
                tokenId=token_id,
                chainName=chain_name,
                contractAddress=contract_addr,
                defaults={
                    'name': token.get('name'),
                    'symbol': token.get('symbol'),
                    'mulPoint': mul_point,
                    'price': str(token.get('price')) if token.get('price') is not None else '',
                    'percentChange24h': str(token.get('percentChange24h')) if token.get('percentChange24h') is not None else '',
                    'volume24h': str(token.get('volume24h')) if token.get('volume24h') is not None else '',
                    'liquidity': str(token.get('liquidity')) if token.get('liquidity') is not None else '',
                },
            )
            saved += 1
            if created:
                logger.info(f"创建新代币记录: {obj.symbol}")
            else:
                logger.info(f"更新代币记录: {obj.symbol}")
        except Exception as e:
            logger.error(f"保存代币信息失败，错误信息：{e}")
    return saved
