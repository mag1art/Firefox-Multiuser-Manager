from flask import Flask, request, redirect, send_file
import docker
import re

app = Flask(__name__)
client = docker.from_env()

def sanitize_username(user_id):
    """Удаляет спецсимволы, заменяет пробелы на `_`."""
    user_id = re.sub(r'[^a-zA-Z0-9 ]', '', user_id)  # Оставляем только буквы, цифры и пробелы
    return re.sub(r'\s+', '_', user_id)  # Меняем пробелы на "_"

@app.route("/")
def home():
    return send_file("index.html")  # Форма входа

@app.route("/start_session/<user_id>")
def start_session(user_id):
    user_id = sanitize_username(user_id)  # Очищаем имя пользователя

    if not user_id:
        return "Ошибка: Некорректное имя пользователя!", 400

    container_name = f"firefox_{user_id.lower()}"

    # Проверяем, есть ли контейнер
    existing_containers = client.containers.list(all=True, filters={"name": container_name})
    
    if existing_containers:
        container = existing_containers[0]
        if container.status != "running":
            container.start()
    else:
        # Запуск нового контейнера с Firefox
        container = client.containers.run(
            "jlesage/firefox",
            name=container_name,
            detach=True,
            ports={'5800/tcp': None}  # Автоматический выбор порта
        )

    # Получаем порт noVNC
    port = container.attrs['NetworkSettings']['Ports']['5800/tcp'][0]['HostPort']

    # Автоматически подставляем адрес сервера
    server_host = request.host.split(":")[0]  # Убираем порт, если он есть

    # Перенаправляем пользователя на его браузер
    return redirect(f"http://{server_host}:{port}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
