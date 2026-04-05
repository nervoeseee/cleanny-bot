from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from database.models import User, Order, Service, WorkSlot, InventoryItem, Review, UserRole, OrderStatus


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int):
    # noinspection PyTypeChecker
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, telegram_id: int, full_name: str = None, phone: str = None):
    user = User(telegram_id=telegram_id, full_name=full_name, phone=phone)
    session.add(user)
    await session.commit()
    return user


async def update_user_role(session: AsyncSession, telegram_id: int, role: UserRole):
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        user.role = role
        await session.commit()
    return user


async def set_user_block_status(session: AsyncSession, telegram_id: int, is_blocked: bool):
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        user.is_blocked = is_blocked
        await session.commit()
    return user


async def mark_equipment_returned(session: AsyncSession, user_id: int):
    user = await session.get(User, user_id)
    if user:
        user.has_returned_equipment = True
        user.last_equipment_return = datetime.now()
        await session.commit()


async def get_services(session: AsyncSession, category: str = None):
    # noinspection PyTypeChecker
    query = select(Service).where(Service.is_active == True)
    if category:
        # noinspection PyTypeChecker
        query = query.where(Service.category == category)
    result = await session.execute(query)
    return result.scalars().all()


async def get_service_by_id(session: AsyncSession, service_id: int):
    # noinspection PyTypeChecker
    result = await session.execute(select(Service).where(Service.id == service_id))
    return result.scalar_one_or_none()


async def create_order(session: AsyncSession, client_id: int, service_id: int, address: str, order_date: datetime,
                       total_price: float):
    order = Order(
        client_id=client_id,
        service_id=service_id,
        address=address,
        order_date=order_date,
        total_price=total_price,
        status=OrderStatus.AWAITING
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def get_orders_by_status(session: AsyncSession, status: OrderStatus):
    # noinspection PyTypeChecker
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.service))
        .where(Order.status == status)
    )
    return result.scalars().all()


async def get_orders_for_date(session: AsyncSession, target_date: datetime):
    start = target_date.replace(hour=0, minute=0, second=0)
    end = start + timedelta(days=1)
    # noinspection PyTypeChecker
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.service))
        .where(Order.order_date.between(start, end))
    )
    return result.scalars().all()


async def update_order_status(session: AsyncSession, order_id: int, status: OrderStatus, employee_id: int = None):
    order = await session.get(Order, order_id)
    if order:
        order.status = status
        if employee_id:
            order.employee_id = employee_id
            user = await session.get(User, employee_id)
            if user:
                user.has_returned_equipment = False
        await session.commit()
    return order


async def cancel_order(session: AsyncSession, order_id: int, reason: str):
    order = await session.get(Order, order_id)
    if order:
        order.status = OrderStatus.CANCELLED
        order.cancel_reason = reason
        await session.commit()
    return order


async def create_work_slot(session: AsyncSession, employee_id: int, order_id: int, slot_type: str, start_time: datetime,
                           end_time: datetime):
    slot = WorkSlot(
        employee_id=employee_id,
        order_id=order_id,
        slot_type=slot_type,
        start_time=start_time,
        end_time=end_time
    )
    session.add(slot)
    await session.commit()
    return slot


async def get_employee_daily_hours(session: AsyncSession, employee_id: int, date: datetime):
    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    # noinspection PyTypeChecker
    result = await session.execute(
        select(WorkSlot).where(
            WorkSlot.employee_id == employee_id,
            WorkSlot.start_time >= start_of_day,
            WorkSlot.start_time < end_of_day
        )
    )
    slots = result.scalars().all()
    total_minutes = sum((slot.end_time - slot.start_time).total_seconds() / 60 for slot in slots)
    return total_minutes / 60


async def get_employee_weekly_hours(session: AsyncSession, employee_id: int, date: datetime):
    start_of_week = (date - timedelta(days=date.weekday())).replace(hour=0, minute=0, second=0)
    end_of_week = start_of_week + timedelta(days=7)

    # noinspection PyTypeChecker
    result = await session.execute(
        select(WorkSlot).where(
            WorkSlot.employee_id == employee_id,
            WorkSlot.start_time >= start_of_week,
            WorkSlot.start_time < end_of_week
        )
    )
    slots = result.scalars().all()
    total_minutes = sum((slot.end_time - slot.start_time).total_seconds() / 60 for slot in slots)
    return total_minutes / 60


async def get_inventory_items(session: AsyncSession, item_type: str = None):
    query = select(InventoryItem)
    if item_type:
        # noinspection PyTypeChecker
        query = query.where(InventoryItem.item_type == item_type)
    result = await session.execute(query)
    return result.scalars().all()


async def get_low_stock_items(session: AsyncSession):
    # noinspection PyTypeChecker
    result = await session.execute(
        select(InventoryItem).where(InventoryItem.quantity <= InventoryItem.min_quantity)
    )
    return result.scalars().all()


async def update_inventory_quantity(session: AsyncSession, item_id: int, quantity_change: float):
    item = await session.get(InventoryItem, item_id)
    if item:
        item.quantity += quantity_change
        await session.commit()
    return item


async def create_review(session: AsyncSession, order_id: int, user_id: int, rating: int, text: str):
    is_public = rating >= 4
    review = Review(
        order_id=order_id,
        user_id=user_id,
        rating=rating,
        text=text,
        is_public=is_public
    )
    session.add(review)

    order = await session.get(Order, order_id)
    if order:
        order.rating = rating
        order.review_text = text
        if rating <= 3:
            order.complaint = True

    await session.commit()
    return review, (order.complaint if order else False)


async def get_public_reviews(session: AsyncSession, limit: int = 5):
    from database.models import Order, OrderStatus
    result = await session.execute(
        select(Order)
        .where(Order.rating >= 4)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()