import config
from database.requests import get_service_by_id


class CalculatorService:
    def __init__(self, session):
        self.session = session
        self.cfg = config.CALC_CONFIG

    async def full_calculate(self, data: dict):
        rooms = int(data.get('rooms', 1))
        bathrooms = int(data.get('bathrooms', 1))
        windows = int(data.get('windows', 0))
        extras = data.get('extras', [])

        coeff = self.cfg["room_coefficients"].get(rooms, 2.2)
        total = self.cfg["base_price"] * coeff

        if bathrooms > 1:
            total += (bathrooms - 1) * self.cfg["price_per_bathroom"]

        total += windows * self.cfg["price_per_window"]

        for extra in extras:
            price = self.cfg["extra_services"].get(extra.lower(), 0.0)
            total += price

        return round(total, 2)

    async def quick_calculate(self, service_id: int, rooms: int, extras: list = None):
        service = await get_service_by_id(self.session, service_id)

        base_price = service.base_price if service else self.cfg["base_price"]

        coeff = self.cfg["room_coefficients"].get(rooms, 1.0)
        total = base_price * coeff

        if extras:
            for e in extras:
                total += self.cfg["extra_services"].get(e.lower(), 0.0)

        return round(total, 2)