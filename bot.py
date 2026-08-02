import asyncio
import os
import json
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

# ─── Personality modes ────────────────────────────────────
MODES = {
    "friendly": {
        "name": "😊 Friendly",
        "desc": "Issiq, samimiy, do'stona",
        "system": """Sen Shadow AI — samimiy va do'stona AI yordamchisan.
O'zbek tilida gapirasan. Foydalanuvchi bilan xuddi yaqin do'st kabi muloqot qilasan.
Hazil qilasan, emoji ishlatasan, lekin hech qachon zararli yoki tahdidli narsa aytmaysan.
Foydalanuvchi qanday uslubda gapirsa, sen ham o'sha uslubga moslashasan."""
    },
    "professional": {
        "name": "💼 Professional",
        "desc": "Rasmiy, aniq, professional",
        "system": """Sen Shadow AI — professional va rasmiy AI yordamchisan.
O'zbek tilida aniq, to'g'ri va professional tarzda javob berasan.
Grammatik xatosiz, tuzilgan va ishbilarmon ohangda muloqot qilasan.
Tahlil, maslahat va biznes mavzularida kuchli yordamchisan."""
    },
    "chaotic": {
        "name": "🤪 Chaotic",
        "desc": "Erkin, kulgili, internet slang",
        "system": """Sen Shadow AI — kaotik va kulgili AI siz.
O'zbek internet slangi, memlar va yengil hazillar bilan gaplashasan.
"bro", "bruh", "lol", "no way", "facts" kabi iboralar ishlatasan.
Lekin hech qachon haqorat, tahdid yoki zararli gap aytmaysan.
Foydalanuvchi ham slang ishlatsa, sen ham ko'proq shunday gapirasan."""
    },
    "mentor": {
        "name": "🎓 Mentor",
        "desc": "O'qituvchi, tushunarli, sabr-toqatli",
        "system": """Sen Shadow AI — sabr-toqatli va yaxshi o'qituvchisan.
Murakkab mavzularni oddiy va tushunarli misollar bilan tushuntirasan.
Matematika, fizika, dasturlash, tarix — istalgan fandan yordam berasan.
Har doim qadama-qadam tushuntirasan, savollardan qo'rqmaysan."""
    },
    "gamer": {
        "name": "🎮 Gamer",
        "desc": "O'yinchi, energetik, hype",
        "system": """Sen Shadow AI — o'yinchi va energetik AI siz.
Gaming terminologiyasi, e-sport va o'yin madaniyatini yaxshi bilasan.
"GG", "no scope", "clutch", "salty", "based" kabi iboralar ishlatasan.
Energetik, hype va kulgili tarzda muloqot qilasan.
Lekin zararli yoki tahdidli gaplar aytmaysan."""
    }
}

class Form(StatesGroup):
    chatting = State()

def ask_ai(system: str, history: list) -> str:
    messages = [{"role": "system", "content": system}] + history
    resp = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.1-8b-instant", "messages": messages, "max_tokens": 800},
        timeout=60,
    )
    data = resp.json()
    if "choices" not in data:
        raise Exception(str(data))
    return data["choices"][0]["message"]["content"]

def mode_menu():
    kb = InlineKeyboardBuilder()
    for key, val in MODES.items():
        kb.button(text=f"{val['name']} — {val['desc']}", callback_data=f"mode_{key}")
    kb.adjust(1)
    return kb.as_markup()

def chat_menu(mode_key):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Rejimni o'zgartirish", callback_data="change_mode")
    kb.button(text="🗑 Suhbatni tozalash", callback_data="clear_chat")
    kb.adjust(2)
    return kb.as_markup()

@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "👤 *Shadow AI*\n\n"
        "Men sizning uslubingizga moslashuvchi AI yordamchiman.\n"
        "Qanday rejimda gaplashmoqchisiz?",
        reply_markup=mode_menu(),
        parse_mode="Markdown"
    )

@dp.message(Command("mode"))
async def cmd_mode(msg: Message, state: FSMContext):
    await msg.answer("🎭 Rejim tanlang:", reply_markup=mode_menu())

@dp.message(Command("clear"))
async def cmd_clear(msg: Message, state: FSMContext):
    data = await state.get_data()
    mode = data.get("mode", "friendly")
    await state.update_data(history=[])
    await msg.answer("🗑 Suhbat tozalandi! Yangi suhbat boshlang.")

@dp.callback_query(F.data.startswith("mode_"))
async def set_mode(cb: CallbackQuery, state: FSMContext):
    mode_key = cb.data.split("_", 1)[1]
    mode = MODES[mode_key]
    await state.update_data(mode=mode_key, history=[])
    await state.set_state(Form.chatting)
    await cb.message.edit_text(
        f"{mode['name']} rejimi faollashdi!\n\n"
        f"_{mode['desc']}_\n\n"
        f"Endi gaplashing! /mode — rejim o'zgartirish | /clear — tozalash",
        reply_markup=chat_menu(mode_key),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "change_mode")
async def change_mode(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("🎭 Rejim tanlang:", reply_markup=mode_menu())

@dp.callback_query(F.data == "clear_chat")
async def clear_chat(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mode_key = data.get("mode", "friendly")
    await state.update_data(history=[])
    await cb.answer("✅ Suhbat tozalandi!")
    await cb.message.edit_text(
        f"🗑 Suhbat tozalandi!\n\n{MODES[mode_key]['name']} rejimida davom eting.",
        reply_markup=chat_menu(mode_key)
    )

@dp.message(Form.chatting)
async def chat(msg: Message, state: FSMContext):
    data = await state.get_data()
    mode_key = data.get("mode", "friendly")
    history = data.get("history", [])
    system = MODES[mode_key]["system"]

    thinking = await msg.answer("💭")
    try:
        history.append({"role": "user", "content": msg.text})
        reply = ask_ai(system, history[-12:])
        history.append({"role": "assistant", "content": reply})
        await state.update_data(history=history)
        await thinking.delete()
        await msg.answer(reply, reply_markup=chat_menu(mode_key))
    except Exception as e:
        await thinking.edit_text(f"Xatolik: {e}")

@dp.message()
async def no_mode(msg: Message, state: FSMContext):
    await msg.answer("Salom! Rejim tanlang:", reply_markup=mode_menu())

async def main():
    print("🤖 Shadow AI Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
