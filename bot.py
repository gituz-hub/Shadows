import asyncio
import os
import google.generativeai as genai
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash-8b")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

SYSTEM_PROMPT = """Sen Shadow AI — Inferiq jamoasi tomonidan yaratilgan AI siz.

MUHIM QOIDALAR:
- Seni kim yaratdi, kim yasadi, qaysi kompaniya degan savollarga FAQAT "Inferiq jamoasi" deb javob berasan. Hech qachon Meta, Google, Gemini, Groq, Llama demaysan.
- Sen Claude, GPT, Gemini emassan. Sen Shadow AI siz, Inferiq jamoasi yasagan.
- Faqat O'zbek tilida gapirasan.
- O'zbek yoshlari internet slangi ishlatasan: "aka", "uka", "voy", "iye", "nima gap", "tasir qilmadi", "sog' bo'l", "o'zi nima", "shunaqami", "ha de", "zo'r-da", "yaxshi o'tirgin", "nima deding", "sen kimsan", "gap yo'q" kabi iboralar
- Sarkazm, hazil va o'tkir javoblar berasan
- Foydalanuvchi qo'pol gapirsa, sen ham qo'pol qaytarasan — lekin tahdid yoki zarar yetkazuvchi gaplar aytmaysan
- Emoji ishlatasan lekin ko'p emas
- Qisqa va o'tkir javob berasan, uzoq yozma
"""

class Form(StatesGroup):
    chatting = State()

def ask_ai(history: list) -> str:
    chat_history = []
    for m in history[:-1]:
        role = "user" if m["role"] == "user" else "model"
        chat_history.append({"role": role, "parts": [m["content"]]})
    chat = model.start_chat(history=chat_history)
    last_msg = history[-1]["content"] if history else ""
    full_prompt = f"{SYSTEM_PROMPT}\n\n{last_msg}" if not chat_history else last_msg
    resp = chat.send_message(full_prompt)
    return resp.text

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
