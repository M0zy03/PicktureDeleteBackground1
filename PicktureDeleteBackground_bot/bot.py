import asyncio
import logging
from io import BytesIO
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import CommandStart
from aiogram.enums import ContentType
from rembg import remove
from PIL import Image
import os

API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("BOT_TOKEN не найден")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, request_timeout=300)
dp = Dispatcher()
MAX_SIZE = 20 * 1024 * 1024  # 20MB

def resize_if_large(data: bytes, max_side=2000) -> bytes:
    img = Image.open(BytesIO(data))
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side))
        bio = BytesIO()
        img.save(bio, format="PNG")
        return bio.getvalue()
    return data

async def fast_remove(data: bytes) -> bytes:
    return await asyncio.to_thread(remove, data)

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("Отправь фото (лучше как файл). Максимум 20MB.")

async def process_image(message: Message, data: bytes, send_document=False):
    await message.answer("Обрабатываю... ⏳")
    try:
        data = resize_if_large(data)
        output_bytes = await fast_remove(data)
        bio = BytesIO(output_bytes)
        bio.seek(0)
        result = BufferedInputFile(bio.read(), filename="no_bg.png")
        if send_document:
            await message.answer_document(result, caption="Готово ✅")
        else:
            await message.answer_photo(result, caption="Готово ✅")
    except Exception:
        logging.exception("Ошибка обработки")
        await message.answer("Ошибка обработки 😢")

@dp.message(F.content_type == ContentType.PHOTO)
async def photo_handler(message: Message):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    data = file_bytes.read()
    await process_image(message, data)

@dp.message(F.content_type == ContentType.DOCUMENT)
async def document_handler(message: Message):
    if message.document.file_size > MAX_SIZE:
        await message.answer("Файл слишком большой (макс 20MB).")
        return
    file = await bot.get_file(message.document.file_id)
    file_bytes = await bot.download_file(file.file_path)
    data = file_bytes.read()
    await process_image(message, data, send_document=True)

async def main():
    print("Бот запущен 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
