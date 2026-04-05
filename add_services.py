import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.engine import AsyncSessionLocal, engine, Base
from database.models import Service
from sqlalchemy import select, delete


async def add_services():


    print(" Создание таблиц в базе данных...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(" Таблицы созданы.")

    async with AsyncSessionLocal() as session:
        await session.execute(delete(Service))

        services_data = [
            Service(
                name="Уборка 1-комнатной кв.",
                description="Влажная уборка, чистка полов, пыли и санузла.",
                base_price=85.0,
                duration_minutes=120,
                category="Квартиры",
                is_active=True
            ),
            Service(
                name="Уборка 2-комнатной кв.",
                description="Тщательная уборка всех комнат, кухни и санузла.",
                base_price=120.0,
                duration_minutes=150,
                category="Квартиры",
                is_active=True
            ),
            Service(
                name="Уборка 3-комнатной кв.",
                description="Генеральная уборка большой квартиры 'под ключ'.",
                base_price=155.0,
                duration_minutes=180,
                category="Квартиры",
                is_active=True
            ),

            Service(
                name="Дом до 100 м²",
                description="Комплексная уборка загородного дома или коттеджа.",
                base_price=180.0,
                duration_minutes=210,
                category="Дома",
                is_active=True
            ),
            Service(
                name="Дом 100-200 м²",
                description="Профессиональная уборка больших площадей.",
                base_price=260.0,
                duration_minutes=300,
                category="Дома",
                is_active=True
            ),

            Service(
                name="После ремонта (1-комн)",
                description="Удаление строительной пыли, пятен краски и цемента.",
                base_price=140.0,
                duration_minutes=240,
                category="После ремонта",
                is_active=True
            ),
            Service(
                name="После ремонта (2-комн)",
                description="Глубокая очистка поверхностей после завершения работ.",
                base_price=210.0,
                duration_minutes=320,
                category="После ремонта",
                is_active=True
            ),

            Service(
                name="Химчистка дивана (прямой)",
                description="Удаление пятен и запахов с тканевой обивки.",
                base_price=80.0,
                duration_minutes=90,
                category="Химчистка",
                is_active=True
            ),
            Service(
                name="Химчистка кресла",
                description="Профессиональная экстракторная чистка.",
                base_price=45.0,
                duration_minutes=60,
                category="Химчистка",
                is_active=True
            ),

            Service(
                name="Мойка окон (стандарт)",
                description="Мойка стекол, рам и подоконников с двух сторон.",
                base_price=50.0,
                duration_minutes=60,
                category="Окна",
                is_active=True
            ),
            Service(
                name="Панорамное остекление",
                description="Мойка окон в пол (за 1 пролет).",
                base_price=15.0,
                duration_minutes=30,
                category="Окна",
                is_active=True
            ),
        ]

        session.add_all(services_data)
        await session.commit()

        print(f"В базу данных успешно добавлено {len(services_data)} услуг.")

        result = await session.execute(select(Service))
        all_db_services = result.scalars().all()
        print("\n АКТУАЛЬНЫЙ ПРАЙС-ЛИСТ В БАЗЕ:")
        for s in all_db_services:
            print(f"  [{s.category}] ID:{s.id} | {s.name} | {s.base_price} BYN")


if __name__ == "__main__":
    try:
        asyncio.run(add_services())
    except Exception as e:
        print(f"❌ Ошибка при наполнении базы: {e}")