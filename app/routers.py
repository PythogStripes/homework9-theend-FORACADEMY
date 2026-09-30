from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.cache import get_projects_cache, invalidate_projects_cache, set_projects_cache
from app.database import get_db

# Аутентификация
auth_router = APIRouter(tags=["auth"])


@auth_router.post("/register", response_model=schemas.UserOut, status_code=201)
async def register(data: schemas.RegisterIn, db: AsyncSession = Depends(get_db)):
    exists = await db.scalar(select(models.User).where(models.User.username == data.username))
    if exists:
        raise HTTPException(status_code=409, detail="Пользователь уже существует")
    user = models.User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@auth_router.post("/login", response_model=schemas.TokenOut)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(models.User).where(models.User.username == form.username))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return schemas.TokenOut(access_token=create_access_token(user.id, user.role))


@auth_router.get("/me", response_model=schemas.UserOut)
async def me(user: models.User = Depends(get_current_user)):
    return user


# CRUD-Проекты
projects_router = APIRouter(prefix="/projects", tags=["projects"])


@projects_router.get("", response_model=list[schemas.ProjectOut])
async def list_projects(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cached = await get_projects_cache()          # Redis-кеш
    if cached is not None:
        return cached
    rows = await db.execute(select(models.Project))
    data = [schemas.ProjectOut.model_validate(p).model_dump() for p in rows.scalars()]
    await set_projects_cache(data)
    return data


@projects_router.post("", response_model=schemas.ProjectOut, status_code=201)
async def create_project(
    data: schemas.ProjectIn,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = models.Project(name=data.name, description=data.description, owner_id=user.id)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    await invalidate_projects_cache()
    return project


@projects_router.get("/{project_id}", response_model=schemas.ProjectOut)
async def get_project(project_id: int,
                      user: models.User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    project = await db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


@projects_router.put("/{project_id}", response_model=schemas.ProjectOut)
async def update_project(project_id: int,
                         data: schemas.ProjectUpdate,
                         user: models.User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    project = await db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    if project.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет прав: вы не владелец проекта")
    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    await db.commit()
    await db.refresh(project)
    await invalidate_projects_cache()
    return project


@projects_router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int,
                         user: models.User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    project = await db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    if project.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет прав: вы не владелец проекта")
    await db.delete(project)
    await db.commit()
    await invalidate_projects_cache()