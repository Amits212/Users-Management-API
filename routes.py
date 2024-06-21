from fastapi import APIRouter, HTTPException
from models import User, LoginRequest
from database import get_db_connection
from typing import List

router = APIRouter()

login_attempts = 0
@router.post("/api/login")
async def login(request: LoginRequest):
    global login_attempts
    login_attempts += 1
    if login_attempts > 5:
        raise HTTPException(status_code=429, detail="Login Failed")
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (request.username,))
    user = cursor.fetchone()
    conn.close()
    if not user or user['password'] != request.password:
        raise HTTPException(status_code=401, detail="Login Failed")
    login_attempts = 0

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
