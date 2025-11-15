# Бот расписания РУЗ для мессенджера МАХ

Бот для просмотра расписания групп и преподавателей Финансового Университета через мессенджер МАХ. 

## Описание

Бот интегрирован с API РУЗ Финансового Университета, с помощью его можно:

- Просмотр расписания учебной группы
- Просмотр расписания преподавателя
- Поиск свободных временных окон в расписании группы
- Взаимодействие через inline-клавиатуры
- Управление диалогом с использованием FSM 

## Системные требования

- Python 3.8 или выше
- Токен бота МАХ 

## Установка и запуск

### Локальный запуск

#### 1. Из GitHub

```bash
pip install git+https://github.com/thirdrom/ruzfamax.git
```

#### 2. Создание виртуального окружения (рекомендуется)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

#### 4. Конфигурация токена

##### Вариант 1: Использование переменных окружения (рекомендуется)

Создайте файл `.env` в корневой директории проекта:

```env
MAX_BOT_TOKEN=your_token_here
```

Модифицируйте `bot.py`:

```python
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv('MAX_BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("MAX_BOT_TOKEN not found in environment variables")
```

##### Вариант 2: Прямая настройка в коде

Откройте `bot.py` и замените:

```python
BOT_TOKEN = 'YOUR_MAX_TOKEN_HERE'
```

**Важно:** При использовании этого варианта не коммитьте файл с токеном в публичный репозиторий.

#### 5. Запуск бота

```bash
python bot.py
```

При успешном запуске в консоли появится сообщение:

```
INFO - Started polling with bot @your_bot_username
INFO - Бот запущен @namebot (ID: 12345678)
```

### Запуск в Docker

#### Сборка образа

```bash
docker build -t ruz-bot-max .
```

#### Запуск контейнера

**С передачей токена через переменную окружения:**

```bash
docker run -e MAX_BOT_TOKEN=your_token_here ruz-bot-max
```

**С использованием файла .env:**

```bash
docker run --env-file .env ruz-bot-max
```

### Запуск через Docker Compose

#### 1. Создайте файл `.env` с токеном:

```env
MAX_BOT_TOKEN=your_token_here
```

#### 2. Запустите сервис:

```bash
docker-compose up -d
```

#### 3. Просмотр логов:

```bash
docker-compose logs -f
```

#### 4. Остановка:

```bash
docker-compose down
```

## Структура проекта

```
bot.py                 Основной файл с логикой бота
api.py                 Модуль для работы с API РУЗ
requirements.txt       Список зависимостей проекта
Dockerfile             Конфигурация Docker
docker-compose.yml     Конфигурация Docker Compose
.env                   Переменные окружения (не включать в VCS)
.gitignore             Файлы, исключаемые из контроля версий
README.md              Документация проекта
```

## Команды бота

- `/start` — Инициализация бота и вывод приветственного сообщения
- `/schedule` — Открытие главного меню расписания
- `/help` — Справочная информация о командах и возможностях
- `/cancel` — Отмена текущей операции и возврат в главное меню

## Функциональные возможности

### Расписание группы
- Просмотр расписания на сегодня
- Просмотр расписания на завтра
- Просмотр расписания на текущую неделю
- Интерактивный поиск группы

### Расписание преподавателя
- Поиск преподавателя по ФИО
- Просмотр расписания с детальной информацией
- Отображение контактной информации (email)

### Поиск свободных окон
- Автоматический расчет временных промежутков между занятиями
- Фильтрация окон длительностью более 45 минут
- Детальная информация о занятиях до и после окна

## Архитектура

Бот построен на следующих принципах:

- **Асинхронная архитектура**: Использование `asyncio` для эффективной обработки запросов
- **FSM (Finite State Machine)**: Управление состоянием диалога с пользователем
- **Модульная структура**: Разделение логики API и логики бота
- **Обработка ошибок**: Graceful degradation при сбоях API

## Диагностика проблем

### Бот не запускается

**Ошибка:** `Invalid access_token`
```
Решение: Проверьте корректность токена. Получите новый токен на https://max.ru/masterbot
```

**Ошибка:** `ModuleNotFoundError: No module named 'aiomax'`
```bash
# Решение: Установите зависимости
pip install -r requirements.txt
```

**Ошибка:** `ModuleNotFoundError: No module named 'api'`
```
Решение: Убедитесь, что файл api.py находится в той же директории, что и bot.py
```

### Бот не отвечает на команды

1. Проверьте статус процесса:
   ```bash
   ps aux | grep bot.py
   ```

2. Проверьте логи на наличие ошибок

3. Убедитесь, что токен бота корректен

4. Проверьте доступность API РУЗ

### Проблемы с API РУЗ

API может быть временно недоступен. В этом случае бот выдаст соответствующее сообщение пользователю. Рекомендуется повторить попытку через несколько минут.

## Развертывание на сервере

### Использование systemd (Linux)

1. Создайте файл сервиса `/etc/systemd/system/ruz-bot.service`:

```ini
[Unit]
Description=RUZ Schedule Bot for MAX Messenger
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ruz-bot-max
Environment="PATH=/opt/ruz-bot-max/venv/bin"
EnvironmentFile=/opt/ruz-bot-max/.env
ExecStart=/opt/ruz-bot-max/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Активируйте и запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ruz-bot
sudo systemctl start ruz-bot
```

3. Проверьте статус:

```bash
sudo systemctl status ruz-bot
```

4. Просмотр логов:

```bash
sudo journalctl -u ruz-bot -f
```

## Мониторинг и логирование

Логирование настроено через стандартный модуль `logging` Python. Уровень логирования по умолчанию: `INFO`.

Для изменения уровня логирования модифицируйте `bot.py`:

```python
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Изменить на DEBUG для детальных логов
)
```

## Безопасность

### Рекомендации

1. **Никогда не коммитьте токен в систему контроля версий**
   - Используйте `.env` файлы
   - Добавьте `.env` в `.gitignore`

2. **Ограничьте права доступа к файлу конфигурации**
   ```bash
   chmod 600 .env
   ```

3. **Регулярно обновляйте зависимости**
   ```bash
   pip list --outdated
   pip install --upgrade -r requirements.txt
   ```

## Технологический стек

- **Python 3.8+** — Язык программирования
- **aiomax 2.12.3** — Библиотека для работы с МАХ API
- **aiohttp 3.9.1** — Асинхронный HTTP клиент
- **aiofiles 23.2.1** — Асинхронная работа с файлами

## Лицензия

MIT License

## Контакты и поддержка

Для сообщения об ошибках и предложений используйте систему Issues в репозитории проекта.

## Дополнительная документация

- [Документация МАХ API](https://platform-api.max.ru/docs)
- [MasterBot - создание ботов](https://max.ru/masterbot)
