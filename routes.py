from fastapi import APIRouter, HTTPException ,Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from models import User, LoginRequest
from database import get_db_connection
from typing import List, Dict
import pika
import aio_pika
from datetime import datetime
import logging
import os
import asyncio


router = APIRouter()

templates = Jinja2Templates(directory="templates")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "failed_logins")
login_attempts: Dict[str, int] = {}


def send_to_rabbitmq(message: str):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        channel.basic_publish(exchange='', routing_key=RABBITMQ_QUEUE, body=message)
        connection.close()
        logging.info(f"Message sent to RabbitMQ: {message}")
    except Exception as e:
        logging.error(f"Failed to publish message: {e}")

def increment_login_attempts(username: str):
    if username in login_attempts:
        login_attempts[username] += 1
    else:
        login_attempts[username] = 1
    return login_attempts[username]

def reset_login_attempts(username: str):
    if username in login_attempts:
        del login_attempts[username]

@router.post("/api/login")
async def login(request: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = ?"
    username = request.username
    cursor.execute(query, (username,))
    user = cursor.fetchone()
    conn.close()

    if not user or user['password'] != request.password:
        attempts = increment_login_attempts(username)
        if attempts > 3:
            message = f"{username},{datetime.utcnow()}"
            print(f'{message=}')
            send_to_rabbitmq(message)
        raise HTTPException(status_code=401, detail="Login Failed")
    reset_login_attempts(username)
    return {"Login: login successful"}

@router.post("/api/users/")
def create_user(user: User):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO users (username, password, name, age, description) VALUES ("
                   f"'{user.username}', '{user.password}', '{user.name}', '{user.age}', '{user.description}')")
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return {**user.model_dump(), "id": user_id}

@router.get("/api/users/")
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()
    return [dict(user) for user in users]

@router.get("/api/users/{name}")
def get_user(name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE name = '{name}'"
    print(query)
    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(user)

@router.put("/api/users/{user_id}")
def update_user(user_id: int, user: User):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'UPDATE users SET username = {user.username}, password = {user.password} WHERE id = {user_id}')
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    conn.close()
    return {**user.model_dump(), "id": user_id}

@router.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'DELETE FROM users WHERE id = {user_id}')
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    conn.close()
    return {"detail": "User deleted"}


@router.get("/api/messages", response_class=JSONResponse)
async def get_queue_messages():
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT
    )
    queue_messages = []

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    queue_messages.append(message.body.decode())
                    if len(queue_messages) >= 10:
                        break

    return {"messages": queue_messages}
