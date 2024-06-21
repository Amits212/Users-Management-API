from pydantic import BaseModel
from typing import Optional



class User(BaseModel):
    username: str
    password: str
    name: str
    age: int
    description: Optional[str] = None

    def __str__(self):
        return f"User: {self.name}"


class LoginRequest(BaseModel):
    username: str
    password: str
