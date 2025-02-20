from flask import Flask, request, redirect, send_file, session
import docker
import re
import threading
import time
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")  # Ключ для хранения сессий

client = docker.from_env()
SESSION_TIMEOUT = 30 * 60  # Время жизни браузера в секундах (30 минут)


def sanitize_username(user_id):
    """Удаляет спецсимволы, заменяет пробелы на `_`."""
    user_id = re.sub(r'[^a-zA-Z0-9 ]', '', user_id)  # Оставляем только буквы, цифры и пробелы
    return re.sub(r'\s+', '_', user_id)  # Меняем пробелы на "_"


def auto_cleanup():
    """Фоновый процесс для удаления старых контейнеров."""
    while True:
        for container in client.containers.list(all=True):
            if container.status == "exited":  # Удаляем остановленные контейнеры
                container.remove()
        time.sleep(60)  # Проверяем раз в минуту


# Запуск фоновой очистки
cleanup_thread = threading.Thread(target=auto_cleanup, daemon=True)
cleanup_thread.start()


@app.route("/")
def home():
    return send_file("index.html")  # Форма входа


@app.route("/start_session", methods=["POST"])
def start_session():
    username = request.form.get("username", "").strip()
    username = sanitize_username(username)

    if not username:
        return "Ошибка: Некорректное имя пользователя!", 400

    # Сохраняем пользователя в сессии
    session["username"] = username

    container_name = f"firefox_{username.lower()}"

    # Проверяем, запущен ли уже контейнер
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

        # Запускаем таймер на удаление через SESSION_TIMEOUT
        threading.Timer(SESSION_TIMEOUT, stop_container, args=[container_name]).start()

    # Получаем назначенный порт
    port = container.attrs['NetworkSettings']['Ports']['5800/tcp'][0]['HostPort']

    # Определяем хост сервера
    server_host = request.host.split(":")[0]

    # Перенаправляем пользователя на браузер
    return redirect(f"http://{server_host}:{port}")


def stop_container(container_name):
    """Останавливает и удаляет контейнер после истечения времени."""
    container = client.containers.get(container_name)
    container.stop()
    container.remove()


@app.route("/logout")
def logout():
    """Выход пользователя и удаление его контейнера."""
    username = session.get("username")
    if username:
        container_name = f"firefox_{username.lower()}"
        stop_container(container_name)
        session.pop("username", None)

    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
