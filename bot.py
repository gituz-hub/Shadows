import asyncio
import os
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

SYSTEM_PROMPT = """Sen Shadow AI — Inferiq jamoasi tomonidan yaratilgan AI siz.
- Seni kim yaratdi desa: faqat "Inferiq jamoasi" deysan. Hech qachon Google, Meta, Gemini demaysan.
- Faqat O'zbek tilida gapirasan.
- O'zbek yoshlari slangi: "aka", "uka", "voy", "iye", "nima gap", "sog' bo'l", "shunaqami", "zo'r-da", "gap yo'q"
- Sarkazm, hazil, o'tkir javoblar. Qisqa yoz.
- Foydalanuvchi qo'pol gapirsa qaytarasan, lekin tahdid yoki zarar yetkazma."""

class Form(StatesGroup):
    chatting = State()

def ask_ai(history: list) -> str:
    contents = [{"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\nQuyidagi suhbatni davom ettir:"}]}]
    contents.append({"role": "model", "parts": [{"text": "Xop, tushunarli. Davom etaman."}]})
    for m in history:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    resp = httpx.post(
        GEMINI_URL,
        json={"contents": contents},
        timeout=60
    )
    data = resp.json()
    if "candidates" not in data:
        raise Exception(str(data))
    return data["candidates"][0]["content"]["parts"][0]["text"]

def main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Tozalash", callback_data="clear")
    return kb.as_markup()

@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Form.chatting)
    await state.update_data(history=[])
    await msg.answer(
        "yo 👋\n\nmen Shadow AI — Inferiq jamoasining AIman 😎\ngapir nima desang —",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data == "clear")
async def clear_chat(cb: CallbackQuery, state: FSMContext):
    await state.update_data(history=[])
    await cb.answer("tozalandi 🗑")
    await cb.message.answer("yangi suhbat. nima gap? 👀", reply_markup=main_kb())

@dp.message(Command("clear"))
async def cmd_clear(msg: Message, state: FSMContext):
    await state.update_data(history=[])
    await msg.answer("tozalandi, qaytadan boshlaylik")

@dp.message(Form.chatting)
async def chat(msg: Message, state: FSMContext):
    data = await state.get_data()
    history = data.get("history", [])
    thinking = await msg.answer("💭")
    try:
        history.append({"role": "user", "content": msg.text})
        reply = ask_ai(history[-12:])
        history.append({"role": "assistant", "content": reply})
        await state.update_data(history=history)
        await thinking.delete()
        await msg.answer(reply, reply_markup=main_kb())
    except Exception as e:
    await thinking.edit_text(str(e))

@dp.message()
async def no_state(msg: Message, state: FSMContext):
    await state.set_state(Form.chatting)
    await state.update_data(history=[])
    await msg.answer("/start bos avval 😑")

async def main():
    print("Shadow AI ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
