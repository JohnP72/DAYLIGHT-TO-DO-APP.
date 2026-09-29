import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://todo:todo_local_password@localhost:3306/todo')
if DATABASE_URL.startswith('mysql://'):
    DATABASE_URL = DATABASE_URL.replace('mysql://', 'mysql+pymysql://', 1)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

class Base(DeclarativeBase):
    pass

class TaskList(Base):
    __tablename__ = 'task_lists'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey('task_lists.id'))
    title: Mapped[str] = mapped_column(String(200))
    note: Mapped[str] = mapped_column(Text, default='')
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

class ListInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    @field_validator('name')
    @classmethod
    def strip_name(cls, value):
        if not value.strip():
            raise ValueError('Please enter a name')
        return value.strip()

class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    list_id: int
    note: str = Field(default='', max_length=20000)
    completed: bool = False
    @field_validator('title')
    @classmethod
    def strip_title(cls, value):
        if not value.strip():
            raise ValueError('Please enter a title')
        return value.strip()

class OrderInput(BaseModel):
    ids: list[int]

def require(db, model, id):
    obj = db.get(model, id)
    if obj is None:
        raise HTTPException(404, 'Item no longer exists. Refresh and try again.')
    return obj

def task_dict(task):
    return {key: getattr(task, key) for key in ('id', 'list_id', 'title', 'note', 'completed', 'position')}

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        if not db.scalar(select(TaskList.id).limit(1)):
            db.add(TaskList(name='My tasks'))
            db.commit()
    yield

app = FastAPI(title='Daylight To-Do API', lifespan=lifespan)

@app.middleware('http')
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.get('/api/state')
def state():
    with Session(engine) as db:
        return {'lists': [{'id': item.id, 'name': item.name} for item in db.scalars(select(TaskList).order_by(TaskList.id))],
                'tasks': [task_dict(task) for task in db.scalars(select(Task).order_by(Task.position, Task.id))]}

@app.post('/api/lists', status_code=201)
def add_list(data: ListInput):
    with Session(engine) as db:
        item = TaskList(name=data.name)
        db.add(item)
        db.commit()
        return {'id': item.id, 'name': item.name}

@app.put('/api/lists/{id}')
def edit_list(id: int, data: ListInput):
    with Session(engine) as db:
        item = require(db, TaskList, id)
        item.name = data.name
        db.commit()
        return {'id': item.id, 'name': item.name}

@app.delete('/api/lists/{id}')
def delete_list(id: int):
    with Session(engine) as db:
        item = require(db, TaskList, id)
        for task in db.scalars(select(Task).where(Task.list_id == id)):
            db.delete(task)
        db.delete(item)
        db.commit()
        return {'ok': True}

@app.post('/api/tasks', status_code=201)
def add_task(data: TaskInput):
    with Session(engine) as db:
        require(db, TaskList, data.list_id)
        last = db.scalar(select(Task.position).where(Task.list_id == data.list_id).order_by(Task.position.desc()).limit(1))
        task = Task(**data.model_dump(), position=(last or 0) + 1)
        db.add(task)
        db.commit()
        return task_dict(task)

@app.put('/api/tasks/{id}')
def edit_task(id: int, data: TaskInput):
    with Session(engine) as db:
        task = require(db, Task, id)
        require(db, TaskList, data.list_id)
        if task.list_id != data.list_id:
            last = db.scalar(select(Task.position).where(Task.list_id == data.list_id).order_by(Task.position.desc()).limit(1))
            task.position = (last or 0) + 1
        for key, value in data.model_dump().items():
            setattr(task, key, value)
        db.commit()
        return task_dict(task)

@app.delete('/api/tasks/{id}')
def delete_task(id: int):
    with Session(engine) as db:
        db.delete(require(db, Task, id))
        db.commit()
        return {'ok': True}

@app.put('/api/lists/{id}/order')
def reorder(id: int, data: OrderInput):
    with Session(engine) as db:
        require(db, TaskList, id)
        tasks = list(db.scalars(select(Task).where(Task.list_id == id)))
        if len(data.ids) != len(set(data.ids)) or set(data.ids) != {task.id for task in tasks}:
            raise HTTPException(409, 'The list changed. Refresh before reordering.')
        positions = {id: index for index, id in enumerate(data.ids)}
        for task in tasks:
            task.position = positions[task.id]
        db.commit()
        return {'ok': True}

static = Path(os.getenv('FRONTEND_DIST', str(Path(__file__).parent.parent / 'frontend' / 'dist')))
if static.exists():
    app.mount('/', StaticFiles(directory=static, html=True), name='frontend')
