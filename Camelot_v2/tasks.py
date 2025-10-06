import logging.config
import logging
from decimal import Decimal
from typing import Any, Optional, Dict, Tuple, List

from celery import shared_task
from django.db import transaction

from Camelot_v2.models import Camelot
from Defi_Monitor.settings import RPC_URL, LOGGING
from web3 import Web3
from web3.contract import Contract


logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)

FACTORY_ADDRESS = '0x6EcCab422D763aC031210895C81787E87B43A652'
FACTORY_ABI = [
{
        "constant": True,
        "inputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "name": "allPairs",
        "outputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "allPairsLength",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {
                "internalType": "uint112",
                "name": "_reserve0",
                "type": "uint112"
            },
            {
                "internalType": "uint112",
                "name": "_reserve1",
                "type": "uint112"
            },
            {
                "internalType": "uint16",
                "name": "_token0FeePercent",
                "type": "uint16"
            },
            {
                "internalType": "uint16",
                "name": "_token1FeePercent",
                "type": "uint16"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token1",
        "outputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
]

ERC20_ABI = [
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [
            {
                "internalType": "uint8",
                "name": "",
                "type": "uint8"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Token metadata cache (in-process per worker)
_TOKEN_META: Dict[str, Dict[str, Any]] = {}

def get_web3() -> Web3:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise RuntimeError(f'Cannot connect to RPC: {RPC_URL}')
    return w3


def get_factory(w3: Web3) -> Contract:
    checksum_address = w3.to_checksum_address(FACTORY_ADDRESS)
    return w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)


def safe_call(fn, default=None):
    try:
        return fn()
    except Exception as e:
        logger.warning('safe_call fallback: %s', e)
        return default


def fetch_token_meta(w3: Web3, address: str) -> dict[str, Any]:
    address = w3.to_checksum_address(address)
    if address in _TOKEN_META:
        return _TOKEN_META[address]

    contract = w3.eth.contract(address = address, abi = ERC20_ABI)
    symbol = safe_call(lambda: contract.functions.symbol().call(), 'UNKNOWN')
    decimals = safe_call(lambda: contract.functions.decimals().call(), 18)
    meta = {'symbol': symbol, 'decimals': int(decimals)}

    _TOKEN_META[address] = meta
    return meta

def fetch_pair_by_index(w3: Web3, factory: Contract, index: int) -> Optional[Dict[str, Any]]:
    try:
        pair_addr = factory.functions.allPairs(index).call()
    except Exception as e:
        logger.warning('allPairs(%s) failed: %s', index, e)
        return None
    pair_addr = w3.to_checksum_address(pair_addr)
    if len(w3.eth.get_code(pair_addr)) == 0:
        logger.warning('Pair address is zero at index %s', index)
        return None
    pair_contract = w3.eth.contract(address = pair_addr, abi = PAIR_ABI)

    reserve0, reserve1, token0_fee_percent, token1_fee_percent = pair_contract.functions.getReserves().call()
    token0 = pair_contract.functions.token0().call()
    token1 = pair_contract.functions.token1().call()
    pair_symbol = safe_call(lambda: pair_contract.functions.symbol().call(), 'UNKNOWN')
    token0_meta = fetch_token_meta(w3, token0)
    token1_meta = fetch_token_meta(w3, token1)
    return {
        'pair_address': pair_addr,
        'pair_name': pair_symbol,
        'token0_address': token0,
        'token1_address': token1,
        'token0_name': token0_meta['symbol'],
        'token1_name': token1_meta['symbol'],
        'token0_reserve': reserve0,
        'token1_reserve': reserve1,
        'token0FeePercent': token0_fee_percent / 10000,  # Convert to percentage
        'token1FeePercent': token1_fee_percent / 10000,  # Convert to percentage
        'token0_decimals': token0_meta['decimals'],
        'token1_decimals': token1_meta['decimals'],
        'block_timestamp_last': 0
    }


def compute_exchange_rate(token0_reserve: int, token1_reserve: int, d0: int, d1: int) -> Optional[Dict[str, Any]]:
    if token0_reserve == 0 or token1_reserve == 0:
        return None
    adj0 = Decimal(token0_reserve) / (Decimal(10) ** d0)
    adj1 = Decimal(token1_reserve) / (Decimal(10) ** d1)
    if adj0 == 0 or adj1 == 0:
        return None
    price0_in_1 = adj1 / adj0
    price1_in_0 = adj0 / adj1
    def fmt(x: Decimal) -> str:
        return f"{x:.8f}".rstrip('0').rstrip('.') or '0'
    return {
        'numeric': {
            'price_token0_in_token1': fmt(price0_in_1),
            'price_token1_in_token0': fmt(price1_in_0)
        },
        'display': {
            '1 token0': f"{fmt(price0_in_1)} token1",
            '1 token1': f"{fmt(price1_in_0)} token0"
        }
    }

def store_pair(data: Dict[str, Any]) -> Tuple[Camelot, bool]:
    ex = compute_exchange_rate(
        data['token0_reserve'],
        data['token1_reserve'],
        data['token0_decimals'],
        data['token1_decimals']
    )
    with transaction.atomic():
        obj, created = Camelot.objects.select_for_update().get_or_create(
            pair_address = data['pair_address'],
            defaults = {**data, 'exchange_rate': ex}
        )
        if not created:
            changed = False
            for field in [
                'pair_name', 'token0_name', 'token1_name', 'token0_reserve', 'token1_reserve','token0FeePercent', 'token1FeePercent',
                'token0_decimals', 'token1_decimals', 'block_timestamp_last'
            ]:
                if getattr(obj, field) != data[field]:
                    setattr(obj, field, data[field])
                    changed = True
            if ex != obj.exchange_rate:
                obj.exchange_rate = ex
                changed = True
            if changed:
                obj.save()
        return obj, created

@shared_task
def sync_pairs_batch(start_index: int = 0, limit: int = 20) -> Dict[str, Any]:
    w3 = get_web3()
    factory = get_factory(w3)
    try:
        total = factory.functions.allPairsLength().call()
    except Exception as e:
        logger.error('Cannot read allPairsLength: %s', e)
        return {'ok': False, 'error': str(e)}

    end = min(start_index + limit, total)

    processed = 0
    created = 0
    updated = 0
    skipped = 0
    addresses: List[str] = []

    for idx in range(start_index, end):
        pair_data = fetch_pair_by_index(w3, factory, idx)
        if pair_data is None:
            skipped += 1
            continue
        obj, created = store_pair(pair_data)
        addresses.append(obj.pair_address)
        processed += 1
        if created:
            created += 1
        else:
            updated += 1
    summary = {
        'ok': True,
        'factory': FACTORY_ADDRESS,
        'total_pairs': total,
        'range': [start_index, end],
        'attempted': end - start_index,
        'processed': processed,
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'addresses': addresses,
    }
    return summary


@shared_task
def sync_single_pair(index: int) -> Optional[str]:
    """Sync a single pair by its factory index. Returns pair address or None."""
    w3 = get_web3()
    factory = get_factory(w3)
    pdata = fetch_pair_by_index(w3, factory, index)
    if not pdata:
        return None
    obj, _ = store_pair(pdata)
    return obj.pair_address

@shared_task
def sync_first_n_pairs(n: int = 50) -> Dict[str, Any]:
    """Convenience wrapper to sync first n pairs from index 0."""
    return sync_pairs_batch(start_index=0, limit=n)
