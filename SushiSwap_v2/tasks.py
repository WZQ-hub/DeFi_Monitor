from __future__ import annotations

# Celery + Web3 task utilities for SushiSwap V2 pairs
# Factory (SushiSwap V2 on Arbitrum): 0xc35DADB65012eC5796536bD9864eD8773aBc74C4
# Model: SushiSwapV2

import os
import json
import logging
from decimal import Decimal, getcontext
from typing import Optional, Dict, Any, List, Tuple

from celery import shared_task
from django.conf import settings
from django.db import transaction

from web3 import Web3
from web3.contract import Contract
from web3.exceptions import BadFunctionCallOutput

from .models import SushiSwapV2

getcontext().prec = 50
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(name)s: %(message)s')

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FACTORY_ADDRESS = Web3.to_checksum_address('0xc35DADB65012eC5796536bD9864eD8773aBc74C4')
RPC_URL = getattr(settings, 'RPC_URL', os.getenv('RPC_URL'))
if not RPC_URL:

    logger.warning('RPC_URL not found in settings/env; using placeholder (will fail if real call made).')
    RPC_URL = 'https://arb-mainnet.g.alchemy.com/v2/TsCQbiVLIu2jxaD4RL5jN'

# ---------------------------------------------------------------------------
# Minimal ABIs
# ---------------------------------------------------------------------------
FACTORY_ABI = [
    {"name": "allPairsLength", "outputs": [{"type": "uint256", "name": ""}], "inputs": [], "stateMutability": "view", "type": "function"},
    {"name": "allPairs", "outputs": [{"type": "address", "name": ""}], "inputs": [{"type": "uint256", "name": ""}], "stateMutability": "view", "type": "function"},
]

PAIR_ABI = [
    {"name": "getReserves", "outputs": [
        {"type": "uint112", "name": "_reserve0"},
        {"type": "uint112", "name": "_reserve1"},
        {"type": "uint32", "name": "_blockTimestampLast"}
    ], "inputs": [], "stateMutability": "view", "type": "function"},
    {"name": "token0", "outputs": [{"type": "address", "name": ""}], "inputs": [], "stateMutability": "view", "type": "function"},
    {"name": "token1", "outputs": [{"type": "address", "name": ""}], "inputs": [], "stateMutability": "view", "type": "function"},
    {"name": "symbol", "outputs": [{"type": "string", "name": ""}], "inputs": [], "stateMutability": "view", "type": "function"},
]

ERC20_ABI = [
    {"name": "symbol", "outputs": [{"type": "string", "name": ""}], "inputs": [], "stateMutability": "view", "type": "function"},
    {"name": "decimals", "outputs": [{"type": "uint8", "name": ""}], "inputs": [], "stateMutability": "view", "type": "function"},
]

# Token metadata cache (in-process per worker)
_TOKEN_META: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_w3() -> Web3:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():  # type: ignore[attr-defined]
        raise RuntimeError(f'Cannot connect to RPC: {RPC_URL}')
    return w3


def get_factory(w3: Web3) -> Contract:
    code = w3.eth.get_code(FACTORY_ADDRESS)
    if len(code) == 0:
        raise RuntimeError('Factory address has no code on this network.')
    return w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)


def safe_call(fn, default=None):
    try:
        return fn()
    except Exception as e:  # noqa
        logger.debug('safe_call fallback: %s', e)
        return default


def fetch_token_meta(w3: Web3, address: str) -> Dict[str, Any]:
    address = Web3.to_checksum_address(address)
    if address in _TOKEN_META:
        return _TOKEN_META[address]
    c = w3.eth.contract(address=address, abi=ERC20_ABI)
    symbol = safe_call(lambda: c.functions.symbol().call(), 'UNKNOWN') or 'UNKNOWN'
    decimals = safe_call(lambda: c.functions.decimals().call(), 18) or 18
    meta = {'symbol': symbol, 'decimals': int(decimals)}
    _TOKEN_META[address] = meta
    return meta


def fetch_pair_by_index(w3: Web3, factory: Contract, index: int) -> Optional[Dict[str, Any]]:
    try:
        pair_addr = factory.functions.allPairs(index).call()
    except Exception as e:
        logger.warning('allPairs(%s) failed: %s', index, e)
        return None
    pair_addr = Web3.to_checksum_address(pair_addr)
    if len(w3.eth.get_code(pair_addr)) == 0:
        logger.warning('Pair %s has no code (skip)', pair_addr)
        return None
    pair_c = w3.eth.contract(address=pair_addr, abi=PAIR_ABI)
    try:
        reserve0, reserve1, ts = pair_c.functions.getReserves().call()
        token0 = pair_c.functions.token0().call()
        token1 = pair_c.functions.token1().call()
        pair_symbol = safe_call(lambda: pair_c.functions.symbol().call(), '') or ''
    except BadFunctionCallOutput as e:
        logger.warning('Pair %s call revert: %s', pair_addr, e)
        return None
    except Exception as e:
        logger.warning('Pair %s unexpected error: %s', pair_addr, e)
        return None
    meta0 = fetch_token_meta(w3, token0)
    meta1 = fetch_token_meta(w3, token1)
    # Determine pair_name preference: if pair_symbol generic, build from tokens
    generic_symbols = {'', 'SLP', 'UNI-V2'}
    if pair_symbol in generic_symbols:
        pair_name = f"{meta0['symbol']}-{meta1['symbol']}"
    else:
        pair_name = pair_symbol
    return {
        'pair_address': pair_addr,
        'pair_name': pair_name,
        'token0_name': meta0['symbol'],
        'token1_name': meta1['symbol'],
        'token0_reserve': int(reserve0),
        'token1_reserve': int(reserve1),
        'token0_decimals': meta0['decimals'],
        'token1_decimals': meta1['decimals'],
        'block_timestamp_last': int(ts),
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


def store_pair(data: Dict[str, Any]) -> Tuple[SushiSwapV2, bool]:
    # Prepare exchange_rate JSON
    ex = compute_exchange_rate(
        data['token0_reserve'], data['token1_reserve'], data['token0_decimals'], data['token1_decimals']
    )
    with transaction.atomic():
        obj, created = SushiSwapV2.objects.select_for_update().get_or_create(
            pair_address=data['pair_address'],
            defaults={**data, 'exchange_rate': ex}
        )
        if not created:
            changed = False
            for field in [
                'pair_name', 'token0_name', 'token1_name', 'token0_reserve', 'token1_reserve',
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

# ---------------------------------------------------------------------------
# Celery Tasks
# ---------------------------------------------------------------------------

@shared_task
def sync_pairs_batch(start_index: int = 0, limit: int = 20) -> Dict[str, Any]:
    """Sync a batch of pairs from the SushiSwap V2 factory.
    Args:
        start_index: starting pair index
        limit: number of pairs to process
    Returns summary dict
    """
    w3 = get_w3()
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
        pdata = fetch_pair_by_index(w3, factory, idx)
        if not pdata:
            skipped += 1
            continue
        obj, was_created = store_pair(pdata)
        addresses.append(obj.pair_address)
        processed += 1
        if was_created:
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
    logger.info('Batch sync summary %s', summary)
    return summary


@shared_task
def sync_single_pair(index: int) -> Optional[str]:
    """Sync a single pair by its factory index. Returns pair address or None."""
    w3 = get_w3()
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
