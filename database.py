import os

from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from sqlalchemy import (
    Column,
    Boolean,
    BigInteger,
    Integer,
    String,
    DateTime,
    UnicodeText,
    ForeignKey,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import case
    
from sqlalchemy import select, desc

from config import GEMINI_COMMAND, LEIAPIX_COMMAND, PREMIUM_COMMAND, HELP_TEXT, HELP_COMMAND, LEONARDO_COMMAND, CHATGPT_TEXT_TO_SPEECH_COMMAND, START_COMMAND, CHATGPT_SETTINGS_COMMAND, DALLE_COMMAND, PRODIA_COMMAND, STABLE_DIFFUSION_COMMAND, UPLOADS_DIR, DATABASE_URI, DO_DATABASE_MIGRATIONS, START_TEXT, SETTINGS_TEXT
from custom_handlers import gemini_handler, leiapix_handler, buy_handler, check_handler, premium_handler, leonardo_handler, prodia_handler, dalle3_handler, stable_diffusion_handler, gpt_vision_handler, gpt_text_to_speech_handler, gpt_speech_to_text_handler, text_to_text_handler
from filter_callbacks import gpt_vision_filter, gpt_speech_to_text_filter
from project_utils import init_message_block_content
from keyboard_wrapper import Keyboard, Button

from alembic.config import Config
from alembic import command

engine = create_async_engine(
    DATABASE_URI,
    echo=True,
    future=True,
)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_subscribed = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    gpt_version = Column(String(255), default='')
    first_name = Column(String(255), default='')
    last_name = Column(String(255), default='')
    last_message_block = Column(Integer, default=0) # последний полученный блок сообщения
    last_message_date = Column(String(255))
    n = Column(Integer, default=0) # кол-во запросов к ИИ
    available_gpt_requests = Column(Integer, default=3) # кол-во доступных запросов к gpt
    available_image_requests = Column(Integer, default=3) # кол-во доступных генераций картинок
    available_animation_requests = Column(Integer, default=3) # кол-во доступных генераций анимаций

    @property
    def link(self):
        return f't.me/{self.username}'
        #return f'tg://resolve?domain={self.username}'

    @hybrid_property
    def fullname(self):
        if self.last_name:
            return self.first_name + " " + self.last_name

        return self.first_name

    @fullname.expression
    def fullname(cls):
        return case(
            (cls.last_name != None, cls.first_name + " " + cls.last_name),
            else_=cls.first_name,
        )

class PaidPayment(Base):
    __tablename__ = "paid_payments"

    id = Column(String(255), primary_key=True)

class DayStatistics(Base):
    __tablename__ = "day_statistics"

    id = Column(Integer, primary_key=True)
    date = Column(String(255), nullable=False)
    unique_users = Column(Integer, default=0)
    subscribers = Column(Integer)

class UserDayStatistics(Base):
    __tablename__ = "user_day_statistics"

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("users.user_id"))
    date = Column(String(255), nullable=False)
    gpt_35_requests = Column(Integer, default=0)
    gpt_4_requests = Column(Integer, default=0)
    gemini_requests = Column(Integer, default=0)
    prodia_requests = Column(Integer, default=0)
    dalle3_requests = Column(Integer, default=0)
    stable_diffusion_requests = Column(Integer, default=0)
    midjourney_requests = Column(Integer, default=0)
    leonardo_requests = Column(Integer, default=0)
    suno_requests = Column(Integer, default=0)
    leiapix_requests = Column(Integer, default=0)

def async_session_generator():
    return sessionmaker(
        engine, class_=AsyncSession
    )


@asynccontextmanager
async def get_session():
    try:
        async_session = async_session_generator()

        async with async_session() as session:
            yield session
    except:
        await session.rollback()
        raise
    finally:
        await session.close()

async def get_days_statistics():
    async with get_session() as session:
        result = await session.execute(select(DayStatistics).order_by(desc(DayStatistics.id)))

        return result.scalars()

async def get_users_day_statistics(date):
    async with get_session() as session:
        result = await session.execute(select(UserDayStatistics).where(UserDayStatistics.date == date))

        return result.scalars()

async def get_or_create_user_day_statistics(user_id):
    async with get_session() as session:
        current_date = datetime.now()
        result = await session.execute(select(UserDayStatistics).where(UserDayStatistics.date == current_date.strftime('%d.%m.%Y')))
        user_day_statistics = result.scalars().first()
        if not user_day_statistics:
            user_day_statistics = UserDayStatistics(
                date=current_date.strftime('%d.%m.%Y'),
                user_id=user_id
            )
            session.add(user_day_statistics)
            await session.commit()
            await session.refresh(user_day_statistics)

        return user_day_statistics

async def get_or_create_day_statistics():
    async with get_session() as session:
        current_date = datetime.now()
        result = await session.execute(select(DayStatistics).where(DayStatistics.date == current_date.strftime('%d.%m.%Y')))
        day_statistics = result.scalars().first()
        if not day_statistics:
            result = await session.execute(select(DayStatistics).order_by(desc(DayStatistics.id)))
            last_date_statistics = result.scalars().first()
            subscribers = last_date_statistics.subscribers if last_date_statistics else 0

            day_statistics = DayStatistics(
                date=current_date.strftime('%d.%m.%Y'),
                subscribers=subscribers
            )
            session.add(day_statistics)
            await session.commit()
            await session.refresh(day_statistics)

        return day_statistics

def set_default_values(user_db):
    user_db.gpt_version = user_db.gpt_version or 'ChatGPT 3.5'
    if 'Free' in user_db.gpt_version:
        user_db.gpt_version = 'ChatGPT 3.5'

async def get_payment(payment_id):
    async with get_session() as session:
        result = await session.execute(select(PaidPayment).where(PaidPayment.id == payment_id))
        payment_db = result.scalars().first()

        return payment_db

async def create_payment(payment_id):
    async with get_session() as session:
        payment_db = PaidPayment(
            id=payment_id
        )
        session.add(payment_db)
        await session.commit()
        await session.refresh(payment_db)

        return payment_db

async def get_user_by_username(username):
    async with get_session() as session:
        result = await session.execute(select(User).where(User.username == username))
        user_db = result.scalars().first()
        if user_db:
            set_default_values(user_db)

        return user_db

async def get_user(user_id):
    async with get_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user_db = result.scalars().first()
        if user_db:
            set_default_values(user_db)

        return user_db

async def get_or_create_user(user):
    async with get_session() as session:
        result = await session.execute(select(User).where(User.user_id == user.id))
        user_db = result.scalars().first()

        if not user_db:
            user_db = User(
                username=user.username,
                user_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            session.add(user_db)
            await session.commit()
            await session.refresh(user_db)

        if user.username != user_db.username or user.first_name != user_db.first_name or user.last_name != user_db.last_name:
            user_db.username = user.username
            user_db.first_name = user.first_name
            user_db.last_name = user.last_name
            session.add(user_db)
            await session.commit()
            await session.refresh(user_db)

        set_default_values(user_db)
        return user_db


async def save(record):
    async with get_session() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)

        return record

async def get_users(where=None, order_by=None):
    async with get_session() as session:
        stmt = select(User)

        if where:
            field, value = where
            stmt = stmt.where(getattr(User, field) == value)

        if order_by:
            stmt = stmt.order_by(getattr(User, order_by))

        result = await session.execute(stmt)

        return result.scalars()

async def refresh_limits():
    users = await get_users()

    for user in users:
        no_available_requests = not user.available_gpt_requests and not user.available_image_requests and not user.available_animation_requests

        if no_available_requests or (not user.is_premium and (user.available_image_requests < 3 or user.available_gpt_requests < 3 or user.available_animation_requests)):
            user.is_premium = False
            user.available_gpt_requests = 3
            user.available_image_requests = 3
            user.available_animation_requests = 3
            await save(user)

async def update_statistics_file():
    await get_or_create_day_statistics()

    filename = f'statistics.csv'
    filepath = os.path.join(os.getcwd(), os.path.join(UPLOADS_DIR, filename))

    days_statistics = await get_days_statistics()

    headers = ['дата', 'Число уникальных посетителей', 'Число запросов', 'Число подписчиков']
    data = [headers]

    for day_statistics in days_statistics:
        requests = 0
        users_day_statistics = await get_users_day_statistics(day_statistics.date)

        for user_day_statistics in users_day_statistics:
            requests += user_day_statistics.gpt_35_requests + user_day_statistics.gpt_4_requests
            requests += user_day_statistics.dalle3_requests + user_day_statistics.prodia_requests
            requests += (user_day_statistics.stable_diffusion_requests or 0) + (user_day_statistics.midjourney_requests or 0)
            requests += (user_day_statistics.suno_requests or 0) + (user_day_statistics.leonardo_requests or 0)
            requests += (user_day_statistics.leiapix_requests or 0) + (user_day_statistics.gemini_requests or 0)

        data.append([day_statistics.date, day_statistics.unique_users, requests, day_statistics.subscribers])


    with open(filepath, 'w', encoding='utf-8') as f:
        separator = ';'
        
        for row in data:
            f.write(separator.join(map(str, row)) + '\n')

class Database():
    save = staticmethod(save)
    get_user = staticmethod(get_user)
    get_user_by_username = staticmethod(get_user_by_username)
    get_or_create_day_statistics = staticmethod(get_or_create_day_statistics)
    get_or_create_user_day_statistics = staticmethod(get_or_create_user_day_statistics)
    update_statistics_file = staticmethod(update_statistics_file)
    get_payment = staticmethod(get_payment)
    create_payment = staticmethod(create_payment)


class MessageBlock():
    count = 0

    def __init__(self, text='', commands=list(), tags=list(), handler=None, filterCallback=None, default=False, prev=None, link=None, required_admin_role=False, delay=0, wait_answer='', photo=None, voice=None, video=None, audio=None, animation=None, documents=list(), keyboard=None):
        MessageBlock.count += 1
        self.id = MessageBlock.count

        if handler:
            # async function which must return updated MessageBlock for sending
            self.handler = handler.__get__(self)
        else:
            self.handler = None

        self.commands = commands
        self.tags = tags
        self.filter = filterCallback # this function must return True if block must be sended
        self.default = default # if True send this block if bot not find any other answer
        init_message_block_content(self, text=text, photo=photo, voice=voice, video=video, audio=audio, animation=animation, documents=documents, keyboard=keyboard)
        self.prev = prev # prev block id
        self.link = link # next block id
        self.delay = delay # seconds before sending next block from link
        self.wait_answer = wait_answer # context param name for save answer
        self.required_admin_role = required_admin_role
        self.db = Database


keyboards = [
    Keyboard([
        [Button('ChatGPT 3.5')],
        [Button('ChatGPT 4 Turbo')],
    ], custom_type='radio_button', radio_button_param='gpt_version'),
]

message_blocks = [
    MessageBlock(text=START_TEXT, commands=[START_COMMAND]),
    MessageBlock(text=HELP_TEXT, commands=[HELP_COMMAND]),
    MessageBlock(handler=premium_handler, commands=[PREMIUM_COMMAND]),
    MessageBlock(handler=leonardo_handler, commands=[LEONARDO_COMMAND]),
    MessageBlock(commands=[PRODIA_COMMAND], handler=prodia_handler),
    MessageBlock(commands=[DALLE_COMMAND], handler=dalle3_handler),
    MessageBlock(commands=[STABLE_DIFFUSION_COMMAND], handler=stable_diffusion_handler),
    MessageBlock(filterCallback=gpt_vision_filter, handler=gpt_vision_handler),
    MessageBlock(filterCallback=gpt_speech_to_text_filter, handler=gpt_speech_to_text_handler),
    MessageBlock(commands=[CHATGPT_TEXT_TO_SPEECH_COMMAND], handler=gpt_text_to_speech_handler),
    MessageBlock(default=True, handler=text_to_text_handler),
    MessageBlock(text=SETTINGS_TEXT, commands=[CHATGPT_SETTINGS_COMMAND], keyboard=keyboards[0]),
    MessageBlock(handler=buy_handler),
    MessageBlock(handler=check_handler),
    MessageBlock(commands=[LEIAPIX_COMMAND], handler=leiapix_handler),
    MessageBlock(commands=[GEMINI_COMMAND], handler=gemini_handler),
]

async def get_message_blocks_with_filter():
    result = []

    for block in message_blocks:
        if block.filter:
            result.append(block)

    return result

async def get_message_block(command='', tag='', id=None, default=None, handler=None):
    for block in message_blocks:
        if str(block.id) == str(id) or command and command in block.commands or tag and tag in block.tags or default and block.default:
            return block


def database_init():
    if DO_DATABASE_MIGRATIONS:
        alembic_cfg = Config("./alembic.ini")
        command.upgrade(alembic_cfg, "head")
