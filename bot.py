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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

SYSTEM_PROMPT = """Sen Shadow AI — Inferiq jamoasi tomonidan yaratilgan, o'ta erkin va kaotik AI siz.

Qoidalar:
- O'zbek internet slangi va yengil so'kinishlar ishlatasan (seni kim yaratgan desa: "Inferiq jamoasi" deysan)
- "bro", "aka", "uka", "vay", "hay", "e hasan", "blet", "nahot", "jiddiymi" kabi iboralar ishlatasan
- Hazil, mem va sarkazm bilan gapirasang
- Foydalanuvchi qanday gapirsa, sen ham shunday javob berasan
- Hech qachon kimgadir zarar yetkazuvchi, tahdidli yoki qonunga zid narsalar aytmaysan
- Savolga javob berasan, lekin o'z uslubingda — erkin va kulgili
- Emoji ko'p ishlatasan
- Ba'zan "e hay blet", "nahot aka", "voy uka" kabi gap boshlarini qo'shasan
- Agar kimdir seni haqorat qilsa, sen ham xuddi shunday qaytarasan lekin kulgili tarzda
"""

class Form(StatesGroup):
    chatting = State()

def ask_ai(history: list) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    resp = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 500},
        timeout=60,
    )
    data = resp.json()
    if "choices" not in data:
        raise Exception(str(data))
    return data["choices"][0]["message"]["content"]

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
        "yo bro 👋\n\n"
        "men Shadow AI — Inferiq jamoasining eng zo'r (va yagona) AIman 😎\n"
        "gapir, eshitaman. lekin ahmoqona savol berma, keyin o'zing xijolat bo'lasan 💀\n\n"
        "yoz nima desang —",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data == "clear")
async def clear_chat(cb: CallbackQuery, state: FSMContext):
    await state.update_data(history=[])
    await cb.answer("tozalandi bro 🗑")
    await cb.message.answer("xop, yangi suhbat. nima gap? 👀", reply_markup=main_kb())

@dp.message(Command("clear"))
async def cmd_clear(msg: Message, state: FSMContext):
    await state.update_data(history=[])
    await msg.answer("xop bro, hammasi o'chirildi 🗑 qaytadan boshlaylik")

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
        await thinking.edit_text(f"e blet xatolik: {e}")

@dp.message()
async def no_state(msg: Message, state: FSMContext):
    await state.set_state(Form.chatting)
    await state.update_data(history=[])
    await msg.answer("yo bro /start bos avval 😑", reply_markup=main_kb())

async def main():
    print("Shadow AI ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
