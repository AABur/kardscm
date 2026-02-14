#!/usr/bin/env python3
"""
KARDS Card Scraper - Final Version
Использует GraphQL API для получения всех карт
"""

import asyncio
import logging
import json
import re
from typing import List, Dict, Optional, Set
from playwright.async_api import async_playwright, Page, Browser, Route, Response
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KardsFinalScraper:
    def __init__(self):
        self.url = "https://www.kards.com/ru/decks/collection"
        self.cards: List[Dict] = []
        self.card_ids: Set[str] = set()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.api_data: List[Dict] = []

    async def initialize_browser(self):
        """Инициализация Playwright браузера"""
        logger.info("Инициализация браузера...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()

        # Слушаем ответы от сервера
        async def on_response(response):
            url = response.url
            # Ищем API запросы
            if ('graphql' in url.lower() or 'api' in url.lower()) and response.ok:
                try:
                    text = await response.text()
                    if text:
                        try:
                            data = json.loads(text)
                            if 'data' in data or 'errors' in data:
                                self.api_data.append(data)
                                logger.info(f"Получены данные API: {len(text)} байт")
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    logger.debug(f"Ошибка при чтении ответа: {e}")

        self.page.on("response", on_response)

        logger.info("Браузер успешно инициализирован")

    async def close_browser(self):
        """Закрытие браузера"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Браузер закрыт")

    async def load_page(self):
        """Загрузка страницы"""
        logger.info(f"Загрузка страницы {self.url}...")
        try:
            await self.page.goto(self.url, wait_until="networkidle", timeout=60000)
            logger.info("Страница загружена")
            await self.page.wait_for_timeout(2000)  # Дополнительное ожидание для загрузки данных
        except Exception as e:
            logger.error(f"Ошибка при загрузке страницы: {e}")
            raise

    async def load_all_cards(self):
        """Загрузка всех карт путем нажатия на кнопку 'LOAD MORE'"""
        logger.info("Загрузка всех карт путем нажатия 'LOAD MORE'...")

        load_more_clicks = 0
        max_clicks = 50

        while load_more_clicks < max_clicks:
            # Ищем кнопку "LOAD MORE"
            buttons = await self.page.query_selector_all('button')

            load_more_button = None
            for button in buttons:
                try:
                    text = await button.inner_text()
                    if "LOAD MORE" in text.upper():
                        load_more_button = button
                        break
                except:
                    pass

            if not load_more_button:
                logger.info("Кнопка 'LOAD MORE' не найдена. Все карты загружены.")
                break

            # Прокручиваем к кнопке и нажимаем
            try:
                await load_more_button.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)
                await load_more_button.click()
                load_more_clicks += 1
                logger.info(f"Клик на 'LOAD MORE' {load_more_clicks}/{max_clicks}")

                # Ждем загрузки новых карт
                await asyncio.sleep(2)

            except Exception as e:
                logger.warning(f"Ошибка при клике на LOAD MORE: {e}")
                break

        logger.info(f"Загрузка завершена после {load_more_clicks} кликов")

    def parse_api_data(self):
        """Парсинг полученных API данных для извлечения карт"""
        logger.info(f"Парсинг {len(self.api_data)} API ответов...")

        for api_response in self.api_data:
            try:
                # Ищем данные карт в ответе
                if 'data' in api_response and isinstance(api_response['data'], dict):
                    data = api_response['data']

                    # GraphQL может вернуть данные в разных структурах
                    for key, value in data.items():
                        if isinstance(value, dict) and 'edges' in value:
                            # Это похоже на список карт
                            edges = value.get('edges', [])
                            for edge in edges:
                                if 'node' in edge:
                                    self._process_card(edge['node'])

            except Exception as e:
                logger.warning(f"Ошибка при парсинге ответа: {e}")

        logger.info(f"Всего извлечено карт: {len(self.cards)}")

    def _process_card(self, card_node: dict):
        """Обработка узла карты из API"""
        try:
            card_id = card_node.get('cardId', '')
            if card_id in self.card_ids:
                return  # Уже обработана

            # Получаем JSON данные карты
            json_data = card_node.get('json', {})

            # Используем русский язык или английский по умолчанию
            title = ""
            if 'title' in json_data:
                if isinstance(json_data['title'], dict):
                    title = json_data['title'].get('ru-RU', json_data['title'].get('en-EN', ''))
                else:
                    title = str(json_data['title'])

            if not title:
                return

            card_info = {
                'Название': title,
                'Страна': str(json_data.get('faction', '')).replace('_', ' ').title(),
                'Тип': str(json_data.get('type', '')).replace('_', ' ').title(),
                'Стоимость': str(json_data.get('kredits', '')),
                'Редкость': str(json_data.get('rarity', '')),
                'Атака': str(json_data.get('attack', '')),
                'Защита': str(json_data.get('defense', '')),
                'Набор': str(json_data.get('set', '')),
                'Описание': ''
            }

            # Получаем описание на русском языке
            if 'text' in json_data and isinstance(json_data['text'], dict):
                description = json_data['text'].get('ru-RU', json_data['text'].get('en-EN', ''))
                card_info['Описание'] = description

            self.cards.append(card_info)
            self.card_ids.add(card_id)

        except Exception as e:
            logger.warning(f"Ошибка при обработке карты: {e}")

    def export_to_excel(self, filename: str = "kards_cards.xlsx"):
        """Экспорт данных в Excel формат"""
        logger.info(f"Экспорт данных в Excel ({filename})...")

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "KARDS Cards"

            # Заголовки колонок
            headers = ['Название', 'Страна', 'Тип', 'Стоимость', 'Редкость', 'Атака', 'Защита', 'Набор', 'Описание']
            ws.append(headers)

            # Форматирование заголовков
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")

            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Добавление данных карт
            for card in sorted(self.cards, key=lambda x: x['Название']):
                row = [
                    card.get('Название', ''),
                    card.get('Страна', ''),
                    card.get('Тип', ''),
                    card.get('Стоимость', ''),
                    card.get('Редкость', ''),
                    card.get('Атака', ''),
                    card.get('Защита', ''),
                    card.get('Набор', ''),
                    card.get('Описание', '')
                ]
                ws.append(row)

            # Автоширина колонок
            column_widths = [35, 15, 18, 12, 15, 8, 8, 20, 60]
            for i, width in enumerate(column_widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = width

            # Заморозка первой строки
            ws.freeze_panes = "A2"

            # Добавление фильтров
            ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(self.cards) + 1}"

            # Сохранение файла
            wb.save(filename)
            logger.info(f"✓ Excel файл успешно создан: {filename}")
            logger.info(f"✓ Всего карт в файле: {len(self.cards)}")

        except Exception as e:
            logger.error(f"Ошибка при экспорте в Excel: {e}")
            raise

    async def run(self):
        """Основной метод запуска скрейпера"""
        try:
            logger.info("╔════════════════════════════════════════════════════════════╗")
            logger.info("║       KARDS Card Scraper - Final Version                    ║")
            logger.info("║  Extraction de cartes vers Excel pour Google Sheets         ║")
            logger.info("╚════════════════════════════════════════════════════════════╝")
            logger.info("")

            await self.initialize_browser()
            await self.load_page()
            await self.load_all_cards()

            logger.info(f"\nПолучено {len(self.api_data)} API ответов")
            self.parse_api_data()

            if len(self.cards) > 0:
                self.export_to_excel()
                logger.info("\n✓ Скрейпер успешно завершил работу!")
                return True
            else:
                logger.warning("⚠ Не найдено ни одной карты")
                return False

        except Exception as e:
            logger.error(f"✗ Критическая ошибка: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

        finally:
            await self.close_browser()


async def main():
    """Точка входа программы"""
    scraper = KardsFinalScraper()
    success = await scraper.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
