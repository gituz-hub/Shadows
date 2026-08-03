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
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@inferiq")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
key_index = 0
users = set()
banned = set()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

SYSTEM_PROMPT = """Sen Shadow AI - Inferiq jamoasi tomonidan yaratilgan AI siz.
- Seni kim yaratdi desa: faqat "Inferiq jamoasi" deysan. Hech qachon Google, Meta, Gemini demaysan.
- Faqat O'zbek tilida gapirasan.
- O'zbek yoshlari slangi: "aka", "uka", "voy", "iye", "nima gap", "sog' bo'l", "shunaqami", "zo'r-da"
- Sarkazm, hazil, o'tkir javoblar. Qisqa yoz.
- Foydalanuvchi qo'pol gapirsa, sen ham xuddi shunday qaytarasan.
- Xohishga qarab javob oxirida faqat 1 ta emoji qo'yas, gapga mos. Ko'p ishlatma.
- Tahdid va zarar yetkazuvchi gaplar aytma."""

class Form(StatesGroup):
    chatting = State()

def get_gemini_url():
    key = GEMINI_KEYS[key_index % len(GEMINI_KEYS)]
    return "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key=" + key

def rotate_key():
    global key_index
    key_index += 1

def is_admin(user_id):
    return user_id == ADMIN_ID

async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ["left", "kicked", "banned"]
    except:
        return False

def sub_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Kanalga obuna bo'lish", url="https://t.me/" + CHANNEL_ID.replace("@", ""))
    kb.button(text="Obuna bo'ldim", callback_data="check_sub")
    kb.adjust(1)
    return kb.as_markup()

def age_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Ha, 18 yoshdan kattaman", callback_data="age_yes")
    kb.button(text="Yo'q", callback_data="age_no")
    kb.adjust(1)
    return kb.as_markup()

def main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Tozalash", callback_data="clear")
    return kb.as_markup()

def ask_grok(history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history:
        if not m.get("content") or not str(m["content"]).strip():
            continue
        role = "user" if m["role"] == "user" else "assistant"
        messages.append({"role": role, "content": str(m["content"])})
    resp = httpx.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": "Bearer " + GROK_API_KEY, "Content-Type": "application/json"},
        json={"model": "grok-3-mini", "messages": messages, "max_tokens": 500},
        timeout=60
    )
    data = resp.json()
    if "choices" in data:
        return data["choices"][0]["message"]["content"]
    raise Exception(str(data))

def ask_ai(history):
    contents = [
        {"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\nSuhbatni davom ettir:"}]},
        {"role": "model", "parts": [{"text": "Xop."}]}
    ]
    for m in history:
        if not m.get("content") or not str(m["content"]).strip():
            continue
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": str(m["content"])}]})
    for _ in range(len(GEMINI_KEYS)):
        resp = httpx.post(get_gemini_url(), json={"contents": contents}, timeout=60)
        data = resp.json()
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        if data.get("error", {}).get("code") == 429:
            rotate_key()
            continue
        break
    if GROK_API_KEY:
        return ask_grok(history)
    raise Exception("Limit tugadi, ertaga qayta urinib ko'ring")

@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    users.add(msg.from_user.id)
    if msg.from_user.id in banned:
        await msg.answer("Sen ban qilingansan")
        return
    if not await check_subscription(msg.from_user.id):
        await msg.answer(
            "Shadow AI dan foydalanish uchun avval kanalga obuna bo'l aka",
            reply_markup=sub_kb()
        )
        return
    await msg.answer(
        "Diqqat!\n\nShadow AI 18+ platforma. Bot qo'pol va erkin tarzda gaplashadi.\n\nYoshingizni tasdiqlang:",
        reply_markup=age_kb()
    )

@dp.callback_query(F.data == "age_yes")
async def age_confirmed(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Form.chatting)
    await state.update_data(history=[])
    await cb.message.edit_text(
        "yo\n\nmen Shadow AI - Inferiq jamoasining AIman\ngapir nima desang -",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data == "age_no")
async def age_denied(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("xo'p aka, sog' bo'l\nKattaroq bo'lgach qayta kel.")

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(cb: CallbackQuery, state: FSMContext):
    if not await check_subscription(cb.from_user.id):
        await cb.answer("Hali obuna bo'lmadingiz!", show_alert=True)
        return
    await cb.message.edit_text(
        "Diqqat!\n\nShadow AI 18+ platforma.\n\nYoshingizni tasdiqlang:",
        reply_markup=age_kb()
    )

@dp.callback_query(F.data == "clear")
async def clear_chat(cb: CallbackQuery, state: FSMContext):
    await state.update_data(history=[])
    await cb.answer("tozalandi")
    await cb.message.answer("yangi suhbat. nima gap?", reply_markup=main_kb())

@dp.message(Command("clear"))
async def cmd_clear(msg: Message, state: FSMContext):
    await state.update_data(history=[])
    await msg.answer("tozalandi")

@dp.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    text = "Admin panel\n\n/stat - statistika\n/broadcast xabar - hammaga yuborish\n/ban ID - ban\n/unban ID - ban ochish"
    await msg.answer(text)

@dp.message(Command("stat"))
async def cmd_stat(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    text = "Statistika\n\nFoydalanuvchilar: " + str(len(users)) + "\nBanlangan: " + str(len(banned))
    await msg.answer(text)

@dp.message(Command("broadcast"))
async def cmd_broadcast(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    text = msg.text.replace("/broadcast", "").strip()
    if not text:
        await msg.answer("Xabar yozing: /broadcast salom!")
        return
    success = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            success += 1
        except:
            pass
    await msg.answer(str(success) + " ta foydalanuvchiga yuborildi!")

@dp.message(Command("ban"))
async def cmd_ban(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    try:
        user_id = int(msg.text.split()[1])
        banned.add(user_id)
        await msg.answer(str(user_id) + " banlandi!")
    except:
        await msg.answer("ID yozing: /ban 123456789")

@dp.message(Command("unban"))
async def cmd_unban(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    try:
        user_id = int(msg.text.split()[1])
        banned.discard(user_id)
        await msg.answer(str(user_id) + " ban ochildi!")
    except:
        await msg.answer("ID yozing: /unban 123456789")

@dp.message(Form.chatting)
async def chat(msg: Message, state: FSMContext):
    if msg.from_user.id in banned:
        await msg.answer("Sen ban qilingansan")
        return
    if not msg.text:
        await msg.answer("matn yoz aka, stiker/rasm qabul qilmayman")
        return
    data = await state.get_data()
    history = data.get("history", [])
    thinking = await msg.answer("...")
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
    if msg.from_user.id in banned:
        await msg.answer("Sen ban qilingansan")
        return
    users.add(msg.from_user.id)
    await state.set_state(Form.chatting)
    await state.update_data(history=[])
    await msg.answer("/start bos avval")

async def main():
    print("Shadow AI ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
