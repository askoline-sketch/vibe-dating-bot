FROM python:3.11-slim
Устанавливаем рабочую директорию
WORKDIR /app
Копируем файл с зависимостями
COPY requirements.txt .
Устанавливаем зависимости (добавляем таймаут на случай проблем с сетью)
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt
Копируем весь остальной код
COPY . .
Команда для запуска бота
CMD ["python", "src/bot.py"]