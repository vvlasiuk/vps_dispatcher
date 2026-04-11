# Input Messages Dispatcher

MVP-диспетчер повідомлень як звичайний Python-процес: читає вхідні payload у форматі Telegram з RabbitMQ, зберігає стан workflow у SQLite, маршрутизує повідомлення через LangGraph і публікує результат обробки назад у RabbitMQ.

## Основні можливості

- Вхідні повідомлення з RabbitMQ черги `input.messages.queue`
- Публікація результату обробки у RabbitMQ чергу `output.messages.queue`
- Детермінований роутинг за командою, станом, джерелом, ботом, чатом і типом контенту
- Зберігання стану workflow та журналу подій у SQLite
- Workflow на LangGraph для розпізнавання бланків та приймання інструмента в сервіс
- Структурована черга помилок і циклічний файл логування
- Перевизначення env-файлу через аргумент CLI або `APP_ENV_FILE`

## Швидкий старт

1. Створіть віртуальне середовище та встановіть залежності:

	```bash
	python -m venv .venv
	.venv\Scripts\python -m pip install -U pip
	.venv\Scripts\python -m pip install -e .
	```

2. Переконайтеся, що RabbitMQ запущений локально (або налаштуйте `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_VHOST`).
3. Скопіюйте `.env.example` у ваш runtime env-файл і змініть значення параметрів.
4. Запустіть диспетчер локально:

	```bash
	.venv\Scripts\python src/main.py --env-file .env.example
	```

5. Опублікуйте повідомлення, що відповідає вхідній схемі, у налаштований exchange і routing key.

## Процес

- `dispatcher`: єдиний процес, який читає вхідні повідомлення, обробляє їх і публікує результат у RabbitMQ

### Створення ініціалізаційного файлу

cp src/plugins/clients/sys_registry.example.py src/plugins/clients/sys_registry.py
