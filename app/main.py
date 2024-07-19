import asyncio
import aiohttp
import aiofiles
import xml.etree.ElementTree as ET
import logging
import sys
from os import getenv
import redis
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime 


TOKEN = getenv("BOT_TOKEN")
dp = Dispatcher()
r = redis.Redis(host='redis', port=6379)

@dp.message(CommandStart())
async def command_start_handler(message: Message, command: CommandObject) -> None:
    await message.answer("Команды:\n" +
                         "/exchange - Отображает стоимость одной валюты в другой\n" + 
                         "/rates - Актуальные курсы валют")

@dp.message(Command("exchange"))
async def command_exchange_handler(message: Message, command: CommandObject) -> None:
    nom1, nom2, amount = command.args.split()
    rate1 = float(r.get(nom1).decode("utf-8"))
    rate2 = float(r.get(nom2).decode("utf-8"))
    exchange = rate1 / rate2 * float(amount)
    await message.answer(str(exchange))

@dp.message(Command("rates"))
async def command_rates_handler(message: Message) -> None:
    ans = [f"{key.decode('utf-8')}\t{r.get(key).decode('utf-8')}" 
           for key in r.keys() if key.decode('utf-8') != "RUB"]
    await message.answer("Сегодняшние курсы валют:\n" + "\n".join(ans))

async def parse():
    async with aiohttp.ClientSession() as session:
        url = "https://cbr.ru/scripts/XML_daily.asp"
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open('app/rates.xml', mode='wb')
                await f.write(await resp.read())
                await f.close()
    tree = ET.parse('app/rates.xml')
    root = tree.getroot()
    for child in root:
        r.set(child[1].text, child[4].text.replace(",", "."))
    r.set("RUB", "1")

async def main() -> None:
    scheduler = AsyncIOScheduler()  
    scheduler.add_job(parse, 'interval', days=1, next_run_time=datetime.now())
    scheduler.start()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())