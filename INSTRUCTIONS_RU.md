# Пошаговая инструкция (быстрый старт)

Ниже — максимально короткие шаги, чтобы запустить агрегатор ставок по депозитам и получить сравнительную таблицу.

## 1) Клонирование/распаковка
Скачайте архив проекта и распакуйте в удобную папку.

## 2) Установка Python и виртуального окружения
1. Убедитесь, что установлен Python 3.10+.
2. Создайте и активируйте окружение:

**Windows:**
```bat
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

## 3) Установка зависимостей
```bash
pip install -r requirements.txt
```

> Примечание: Playwright нужен только для сайтов с динамической подгрузкой. Если такие источники будете использовать, выполните:
```bash
python -m playwright install chromium
```

## 4) Запуск сбора данных
Запустите основной скрипт:
```bash
python main.py
```
После выполнения в папке `output/` появятся файлы:
- `deposit_rates_YYYYMMDD_HHMMSS.csv` — вся сводная таблица.
- `deposit_rates_YYYYMMDD_HHMMSS.md` — та же таблица в Markdown (разделы по валютам).

## 5) Добавление/правка источников
Все источники задаются в `banks.yaml`:
- `type: json` — для JSON API.
- `type: static_html` — для статических HTML-страниц (указывайте CSS-селекторы, при необходимости `regex`).
- `type: playwright` — для динамических страниц (JS).
- `type: csv` — для локальных CSV (например, ручные выгрузки/сводки).

### Минимальный пример для статического HTML
```yaml
- name: "Some Bank"
  country: "DE"
  currency_hint: ["EUR"]
  type: "static_html"
  url: "https://somebank.de/sparen/festgeld"
  html:
    rows:
      selector: "table.rates tbody tr"
    fields:
      bank_name: { value: "Some Bank" }
      product:   { selector: "td:nth-child(1)" }
      currency:  { value: "EUR" }
      rate_apr:  { selector: "td:nth-child(3)", regex: "(\d+[\.,]?\d*)\s*%" }
      link:      { selector: "a", attr: "href" }
```

## 6) Как сортируются данные
- Внутри каждой валюты (`currency`) строки сортируются по `rate_apr` по убыванию.
- В таблице также есть `bank_name`, `product`, `country`, `link`, `source`, `fetched_at`.

## 7) Частые проблемы
- **Нет данных:** проверьте, что источники в `banks.yaml` доступны; оставьте хотя бы `csv`-источник (демо уже есть).
- **Сайты с динамикой:** установите Playwright и используйте тип `playwright`.
- **Парсинг HTML:** корректно подберите CSS-селекторы и регулярные выражения для выделения цифр.

## 8) Автоматизация
- Запускайте `python main.py` по расписанию (cron/Task Scheduler).
- Экспортируйте CSV в вашу BI-систему, Google Sheets или отправляйте в Telegram-бот (легко добавить в `main.py`).

---
Готово! Если перечислите приоритетные страны/банки, можно быстро пополнить `banks.yaml` конкретными адаптерами.
