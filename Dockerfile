# Используем официальный образ Python как базу
FROM python:3.12-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файлы проекта
COPY . /app

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Открываем порт, который будет слушать ваше приложение (обычно 8000)
EXPOSE 8000

# Команда для запуска Gunicorn, аналогично вашему Procfile
CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000", "--log-file", "-"]