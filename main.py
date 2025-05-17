import asyncio
import logging
import random
import sys
from os import getenv

import psycopg2
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

dp = Dispatcher(storage=MemoryStorage())

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname='testing',
            user='postgres',
            password='123',
            host='localhost',
            port='5433'
        )
        self.curr = self.conn.cursor()

    def get_chat_id(self):
        self.curr.execute("SELECT chat_id FROM users")
        return self.curr.fetchall()

    def insert_user(self, data):
        full_name = data.get('fullname')
        phone = data.get('phone')
        address = data.get('address')
        chat_id = int(data.get('chat_id'))

        self.curr.execute(
            """
            INSERT INTO users (fullname, phone, address, chat_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chat_id) DO NOTHING
            """,
            (full_name, phone, address, chat_id)
        )
        self.conn.commit()
        return self.curr.rowcount

    def get_numbers_of_followers(self):
        self.curr.execute("SELECT COUNT(*) FROM users")
        result = self.curr.fetchone()
        return result[0]


class Registration(StatesGroup):
    fullname = State()
    phone = State()
    address = State()

class GameState(StatesGroup):
    guess_number = State()



@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    user_chat_ids = {row[0] for row in Database().get_chat_id()}
    if message.chat.id in user_chat_ids:
        guess_number = random.randint(1, 100)
        await state.set_state(GameState.guess_number)
        await state.update_data(guess_number=guess_number, attempt=0)
        await message.answer('Men 1 dan 100 oralig`ida bir son o`yladim.\nUni toping: ?')
    else:
        await state.set_state(Registration.fullname)
        await message.answer('Ismingizni kiriting:')

@dp.message(Registration.fullname)
async def registration_fullname(message: Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    await message.answer('Telefon raqamingizni kiriting:')
    await state.set_state(Registration.phone)

@dp.message(Registration.phone)
async def registration_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer('Manzilingizni kiriting:')
    await state.set_state(Registration.address)

@dp.message(Registration.address)
async def registration_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    data = await state.get_data()
    chat_id = message.chat.id
    user_data = {
        'fullname': data.get('fullname'),
        'phone': data.get('phone'),
        'address': data.get('address'),
        'chat_id': chat_id
    }

    Database().insert_user(user_data)

    await message.answer("Registratsiyadan o‘tdingiz! 🎉")
    guess_number = random.randint(1, 100)
    await state.set_state(GameState.guess_number)
    await state.update_data(guess_number=guess_number, attempt=0)
    await message.answer('Men 1 dan 100 oralig`ida bir son o`yladim.\nUni toping: ?')

@dp.message(GameState.guess_number)
async def loop_state(message: Message, state: FSMContext):
    state_data = await state.get_data()
    guess_number = state_data.get('guess_number')
    text = message.text

    if text == 'help':
        await message.answer(f"Men {guess_number} sonini o'ylagandim 😊")
        await state.clear()
        return

    if not text.isdigit():
        await message.answer('Faqat 1 dan 100 gacha oraliqda son kiriting: ')
        return

    user_guess = int(text)
    attempt = state_data.get('attempt', 0) + 1

    if user_guess > guess_number:
        await state.update_data(attempt=attempt)
        await message.answer(f'Men o`ylagan son {text} dan kichikroq.')
    elif user_guess < guess_number:
        await state.update_data(attempt=attempt)
        await message.answer(f'Men o`ylagan son {text} dan kattaroq.')
    else:
        await message.answer(f'Tabriklaymiz! Siz {attempt} urinishda topdingiz! 🎉')

        await state.clear()


@dp.message(Command("followers"))
async def count_followers(message: Message):
    count = Database().get_numbers_of_followers()
    await message.answer(f"Botda {count} ta foydalanuvchi ro'yxatdan o'tgan.")

@dp.message()
async def echo(message: Message):
    await message.send_copy(chat_id=message.chat.id)

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
