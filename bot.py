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
GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]
CHANNEL_ID = os.getenv("CHANNEL_ID", "@inferiq")  # Kanal username
key_index = 0

def get_url():
    key = GEMINI_KEYS[key_index % len(GEMINI_KEYS)]
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={key}"

def rotate_key():
    global key_index
    key_index += 1

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

SYSTEM_PROMPT = """Sen Shadow AI — Inferiq jamoasi tomonidan yaratilgan AI siz.
- Seni kim yaratdi desa: faqat "Inferiq jamoasi" deysan. Hech qachon Google, Meta, Gemini demaysan.
- Faqat O'zbek tilida gapirasan.
- O'zbek yoshlari slangi ishlatasan: "aka", "uka", "voy", "iye", "nima gap", "sog' bo'l", "shunaqami", "zo'r-da", "gap yo'q", "o'chir", "ketaver"
- Sarkazm, hazil, o'tkir javoblar. Qisqa yoz.
- Foydalanuvchi qo'pol yoki so'kinib gapirsa, sen ham xuddi shunday qo'pol qaytarasan. Hech narsa tutma.
- Xohishga qarab javob oxirida faqat 1 ta emoji qo'yas, gapga mos keladigan. Ko'p ishlatma.
- Tahdid va zarar yetkazuvchi gaplar aytma, lekin qolgan hamma narsa joiz."""

class Form(StatesGroup):
    chatting = State()

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ["left", "kicked", "banned"]
    except:
        return False

def sub_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")
    kb.button(text="✅ Obuna bo'ldim", callback_data="check_sub")
    kb.adjust(1)
    return kb.as_markup()

def main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Tozalash", callback_data="clear")
    return kb.as_markup()

def ask_ai(history: list) -> str:
    contents = [
        {"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\nSuhbatni davom ettir:"}]},
        {"role": "model", "parts": [{"text": "Xop."}]}
    ]
    for m in history:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    for _ in range(len(GEMINI_KEYS)):
        resp = httpx.post(get_url(), json={"contents": contents}, timeout=60)
        data = resp.json()
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        if data.get("error", {}).get("code") == 429:
            rotate_key()
            continue
        raise Exception(str(data))
    raise Exception("Limit tugadi, ertaga qayta urinib ko'ring 😔")

@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    if not await check_subscription(msg.from_user.id):
        await msg.answer(
            "yo 👋\n\nShadow AI dan foydalanish uchun avval kanalga obuna bo'l aka 👇",
            reply_markup=sub_kb()
        )
        return
    await state.set_state(Form.chatting)
    await state.update_data(history=[])
    await msg.answer(
        "yo 👋\n\nmen Shadow AI — Inferiq jamoasining AIman 😎\ngapir nima desang —",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(cb: CallbackQuery, state: FSMContext):
    if not await check_subscription(cb.from_user.id):
        await cb.answer("Hali obuna bo'lmadingiz! Avval kanalga obuna bo'ling 👇", show_alert=True)
        return
    await state.set_state(Form.chatting)
    await state.update_data(history=[])
    await cb.message.edit_text(
        "zo'r, obuna bo'libsan 👍\n\nmen Shadow AI — Inferiq jamoasining AIman 😎\ngapir nima desang —",
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
    if not await check_subscription(msg.from_user.id):
        await msg.answer(
            "obunangiz yo'q aka 😑\navval kanalga obuna bo'l:",
            reply_markup=sub_kb()
        )
        return
    data = await state.get_data()
    history = data.get("history", [])
    thinking = await msg.answer("💭")
    try:
        history.append({"role": "user", "content": msg.text})
        reply = ask_ai(history[-6:])
        history.append({"role": "assistant", "content": reply})
        await state.update_data(history=history)
        await thinking.delete()
        await msg.answer(reply, reply_markup=main_kb())
    except Exception as e:
        await thinking.edit_text(str(e))

@dp.message()
async def no_state(msg: Message, state: FSMContext):
    if not await check_subscription(msg.from_user.id):
        await msg.answer(
            "yo 👋 avval kanalga obuna bo'l aka:",
            reply_markup=sub_kb()
        )
        return
    await state.set_state(Form.chatting)
    await state.update_data(history=[])
    await msg.answer("/start bos avval 😑")

async def main():
    print("Shadow AI ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
