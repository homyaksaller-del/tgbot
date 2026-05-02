import asyncio
import random
import string
from database import init_db, add_keys, get_issued_keys_stats

# Планы из config
PLANS = {
    "1": {"name": "1 день"},
    "3": {"name": "3 дня"},
    "7": {"name": "7 дней"},
    "14": {"name": "14 дней"},
    "30": {"name": "30 дней"},
    "90": {"name": "90 дней"},
    "0": {"name": "Навсегда"},
}

def generate_random_key():
    """Генерирует случайный ключ в формате XXXXX-XXXXX-XXXXX-XXXXX"""
    parts = []
    for _ in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        parts.append(part)
    return '-'.join(parts)


async def main():
    print("🔑 Инициализирую БД...")
    await init_db()
    
    print("\n📝 Добавляю ключи по планам...\n")
    
    for plan_key, plan_info in PLANS.items():
        # Генерируем 3 случайных ключа на каждый план
        keys = [generate_random_key() for _ in range(3)]
        
        added = await add_keys(keys, plan_key)
        print(f"✅ {plan_info['name']:15} → добавлено {added} ключей")
        for key in keys:
            print(f"   • {key}")
    
    print("\n📊 Статистика ключей:")
    stats = await get_issued_keys_stats()
    print(f"   Всего ключей: {stats['total_keys']}")
    print(f"   Доступных: {stats['available']}")
    print(f"   Выданных: {stats['issued']}")
    print("\n✨ Готово!")


if __name__ == "__main__":
    asyncio.run(main())
