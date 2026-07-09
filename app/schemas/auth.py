from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    nombre: str
    role: str

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    confirmar_password: str

    @field_validator("nombre")
    @classmethod
    def nombre_min_length(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    email: str
    role: str

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
