import aiohttp
import logging
from config import CRYPTO_BOT_TOKEN, CRYPTO_API_URL

logger = logging.getLogger(__name__)


def get_headers():
    return {
        "Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN,
        "Content-Type": "application/json"
    }


async def create_invoice(amount: float, currency: str = "USDT", description: str = "", payload: str = "") -> dict | None:
    """
    Create a CryptoBot invoice.
    Returns invoice dict with invoice_id, pay_url, etc.
    """
    # CryptoBot accepts: USDT, TON, BTC, ETH, LTC, BNB, TRX, USDC
    # We'll use USDT as default crypto, amount in USD
    data = {
        "asset": currency,
        "amount": str(round(amount, 2)),
        "description": description,
        "payload": payload,
        "allow_comments": False,
        "allow_anonymous": False,
        "expires_in": 3600  # 1 hour
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CRYPTO_API_URL}/createInvoice",
                json=data,
                headers=get_headers(),
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                result = await resp.json()
                logger.info(f"CryptoBot createInvoice response: {result}")
                
                if result.get("ok"):
                    return result["result"]
                else:
                    logger.error(f"CryptoBot error: {result}")
    except Exception as e:
        logger.error(f"CryptoBot request failed: {e}")
    
    return None


async def get_invoice(invoice_id: int) -> dict | None:
    """Check invoice status."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{CRYPTO_API_URL}/getInvoices",
                params={"invoice_ids": str(invoice_id)},
                headers=get_headers(),
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                result = await resp.json()
                
                if result.get("ok"):
                    items = result["result"].get("items", [])
                    if items:
                        return items[0]
    except Exception as e:
        logger.error(f"CryptoBot getInvoices failed: {e}")
    
    return None


async def check_invoice_paid(invoice_id: int) -> bool:
    """Returns True if invoice is paid."""
    invoice = await get_invoice(invoice_id)
    if invoice:
        return invoice.get("status") == "paid"
    return False
