import gspread
import logging
import asyncio
from google.oauth2.service_account import Credentials
import config

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

class GoogleSheetsService:
    def __init__(self):
        try:
            creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(config.GOOGLE_SHEETS_FILE_ID)
        except Exception as e:
            logging.error(f"GS Critical Error: {e}")

    def get_schedule(self):
        try:
            worksheet = self.sheet.worksheet("График")
            records = worksheet.get_all_records()
            for r in records:
                date_str = str(r.get('Дата', '')).strip()
                if '-' in date_str:
                    parts = date_str.split('-')
                    if len(parts) == 3 and len(parts[0]) == 4:
                        r['Дата'] = f"{parts[2]}.{parts[1]}.{parts[0]}"
            return records
        except Exception as e:
            logging.error(f"Ошибка чтения графика: {e}")
            return []

    def add_new_staff(self, tg_id: int, full_name: str):
        try:
            worksheet = self.sheet.worksheet("График")
            # Добавляем строку: ID, ФИО, остальное пустое
            row = [str(tg_id), full_name, "", "", "", "", "Добавлен через бота"]
            worksheet.append_row(row)
            return True
        except Exception as e:
            logging.error(f"Ошибка записи сотрудника в GS: {e}")
            return False

    def remove_staff(self, tg_id: int):
        try:
            worksheet = self.sheet.worksheet("График")
            cell = worksheet.find(str(tg_id))
            if cell:
                worksheet.delete_rows(cell.row)
                return True
            return False
        except Exception:
            return False

    def get_inventory(self):
        try:
            worksheet = self.sheet.worksheet("Склад")
            records = worksheet.get_all_records()
            for r in records:
                r['Название'] = r.get('Наименование', 'Без названия')
                r['Остаток'] = r.get('Остаток (шт)', 0)
                r['Мин. остаток'] = r.get('Мин.остаток', 5)
                if '(л)' in r.get('Наименование', ''): r['Ед. изм.'] = 'л'
                elif 'Перчатки' in r.get('Наименование', ''): r['Ед. изм.'] = 'пар'
                else: r['Ед. изм.'] = 'шт'
            return records
        except Exception as e:
            logging.error(f"Ошибка чтения склада: {e}")
            return []

    def update_inventory(self, item_name: str, new_quantity: float):
        try:
            worksheet = self.sheet.worksheet("Склад")
            cell = worksheet.find(item_name)
            if cell:
                worksheet.update_cell(int(cell.row), 4, new_quantity)
                return True
            return False
        except Exception as e:
            logging.error(f"Ошибка обновления инвентаря: {e}")
            return False

    def add_order_to_stats(self, order_data: dict):
        try:
            worksheet = self.sheet.worksheet("Статистика")
            row = [
                str(order_data.get('id', '')),
                str(order_data.get('date', '')),
                str(order_data.get('employee_name', '---')),
                str(order_data.get('service', '')),
                float(order_data.get('total_price', 0)),
                "Завершен",
                str(order_data.get('rating', ''))
            ]
            worksheet.append_row(row)
            return True
        except Exception as e:
            logging.error(f"Ошибка записи в статистику: {e}")
            return False

    def get_low_stock_items(self):
        inventory = self.get_inventory()
        return [i for i in inventory if float(i.get('Остаток', 0)) <= float(i.get('Мин. остаток', 0))]

    def consume_disposable_materials(self, service_category: str, rooms_count: int = 1):
        try:
            norms = {
                "Химчистка": {"Микрофибровая тряпка": 3, "Перчатки латексные": 1},
                "Квартиры": {"Моющее средство (л)": 0.2 * rooms_count, "Микрофибровая тряпка": 2},
                "Окна": {"Моющее средство (л)": 0.1 * rooms_count, "Микрофибровая тряпка": 3},
                "После ремонта": {"Моющее средство (л)": 1.5, "Микрофибровая тряпка": 8, "Перчатки латексные": 2}
            }
            needed = norms.get(service_category, {"Микрофибровая тряпка": 1})
            inventory = self.get_inventory()
            for item_name, amount in needed.items():
                for item in inventory:
                    if item.get('Название') == item_name:
                        current = float(item.get('Остаток', 0))
                        self.update_inventory(item_name, max(0.0, current - amount))
                        break
            return True
        except Exception as e:
            logging.error(f"Ошибка списания материалов: {e}")
            return False

google_sheets = GoogleSheetsService()