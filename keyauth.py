import logging
from database import get_available_key, mark_key_issued

logger = logging.getLogger(__name__)


async def generate_key(plan_key: str, user_id: int) -> str | None:
    """
    Get an available license key from the database and mark it as issued.
    """
    try:
        license_key = await get_available_key(plan_key)
        
        if not license_key:
            logger.error(f"No available keys for plan {plan_key}")
            return None
        
        await mark_key_issued(license_key, user_id)
        logger.info(f"Key issued to user {user_id}: {license_key}")
        return license_key
    except Exception as e:
        logger.error(f"Failed to get key for plan {plan_key}: {e}")
    
    return None
