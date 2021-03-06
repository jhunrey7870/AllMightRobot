# Copyright (C) 2018 - 2020 MrYacha. All rights reserved. Source code available under the AGPL.
# Copyright (C) 2019 Aiogram

#
# This file is part of AllMightBot.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import html
import os
import sys
import requests
import ujson

from AllMightRobot import OWNER_ID, OPERATORS, AllMight_VERSION, DEVS
from AllMightRobot.decorator import REGISTRED_COMMANDS, COMMANDS_ALIASES, register
from AllMightRobot.modules import LOADED_MODULES
from AllMightRobot.services.mongo import db, mongodb
from AllMightRobot.services.quart import quart
from AllMightRobot.services.redis import redis
from AllMightRobot.services.telethon import tbot
from .utils.api import html_white_text
from .utils.covert import convert_size
from .utils.language import get_strings_dec
from .utils.message import need_args_dec
from .utils.notes import BUTTONS, get_parsed_note_list, t_unparse_note_item, send_note
from .utils.term import chat_term


@register(cmds='allcommands', is_op=True)
async def all_commands_list(message):
    text = ""
    for cmd in REGISTRED_COMMANDS:
        text += "* /" + cmd + "\n"
    await message.reply(text)


@register(cmds='allcmdsaliases', is_op=True)
async def all_cmds_aliases_list(message):
    text = ""
    text = str(COMMANDS_ALIASES)
    await message.reply(text)


@register(cmds='loadedmodules', is_op=True)
async def all_modules_list(message):
    text = ""
    for module in LOADED_MODULES:
        text += "* " + module.__name__ + "\n"
    await message.reply(text)


@register(cmds='avaiblebtns', is_op=True)
async def all_btns_list(message):
    text = "Avaible message inline btns:\n"
    for module in BUTTONS:
        text += "* " + module + "\n"
    await message.reply(text)


@register(cmds='ip', is_owner=True)
async def get_bot_ip(message):
    await message.reply(requests.get("http://ipinfo.io/ip").text)


@register(cmds="term", is_owner=True)
async def cmd_term(message):
    msg = await message.reply("Running...")
    command = str(message.text.split(" ", 1)[1])
    text = "<b>Shell:</b>\n"
    text += html.escape(await chat_term(message, command), quote=False)
    await msg.edit_text(text)


@register(cmds="sbroadcast", is_owner=True)
@need_args_dec()
async def sbroadcast(message):
    data = await get_parsed_note_list(message, split_args=-1)

    await db.sbroadcast.drop({})

    chats = mongodb.chat_list.distinct('chat_id')

    data['chats_num'] = len(chats)
    data['recived_chats'] = 0
    data['chats'] = chats

    await db.sbroadcast.insert_one(data)
    await message.reply("Smart broadcast planned for <code>{}</code> chats".format(len(chats)))


@register(cmds="stopsbroadcast", is_owner=True)
async def stop_sbroadcast(message):
    old = await db.sbroadcast.find_one({})
    await db.sbroadcast.drop({})
    await message.reply(
        "Smart broadcast stopped."
        "It was sended to <code>%d</code> chats." % old['recived_chats']
    )


# Check on smart broadcast
@register()
async def check_message_for_smartbroadcast(message):
    chat_id = message.chat.id
    if not (db_item := await db.sbroadcast.find_one({'chats': {'$in': [chat_id]}})):
        return

    text, kwargs = await t_unparse_note_item(message, db_item, chat_id)
    kwargs['reply_to'] = message.message_id

    await send_note(chat_id, text, **kwargs)

    await db.sbroadcast.update_one({'_id': db_item['_id']}, {'$pull': {'chats': chat_id}, '$inc': {'recived_chats': 1}})


@register(cmds="purgecache", is_owner=True)
async def purge_caches(message):
    redis.flushdb()
    await message.reply("Redis cache was cleaned.")


@register(cmds="botstop", is_owner=True)
async def bot_stop(message):
    await message.reply("Goodbye...")
    exit(1)


@register(cmds="upload", is_owner=True)
async def upload_file(message):
    input_str = message.get_args()
    if not os.path.exists(input_str):
        await message.reply("File not found!")
        return
    await message.reply("Processing ...")
    caption_rts = os.path.basename(input_str)
    with open(input_str, 'rb') as f:
        await tbot.send_file(
            message.chat.id,
            f,
            caption=caption_rts,
            force_document=False,
            allow_cache=False,
            reply_to=message.message_id
        )


@register(cmds="logs", is_owner=True)
async def upload_logs(message):
    input_str = 'logs/AllMight.log'
    with open(input_str, 'rb') as f:
        await tbot.send_file(message.chat.id, f, reply_to=message.message_id)


@register(cmds="crash", is_owner=True)
async def crash(message):
    test = 2 / 0
    print(test)
    
@register(cmds="restart", is_owner=True, is_dev=True)
async def restart_bot(message):
    await message.reply("Allmight will be restarted.")
    os.system('restart.bat')
    os.execv('start.bat', sys.argv)



@register(cmds="event", is_op=True)
async def get_event(message):
    print(message)
    event = str(ujson.dumps(message, indent=2))
    await message.reply(event)


@register(cmds="stats", is_op=True)
async def stats(message):
    text = f"<b>AllMight {AllMight_VERSION} stats</b>\n"

    for module in [m for m in LOADED_MODULES if hasattr(m, '__stats__')]:
        text += await module.__stats__()

    await message.reply(text)


@quart.route('/stats')
async def api_stats():
    text = f"<b>AllMight {AllMight_VERSION} stats</b>\n"

    for module in [m for m in LOADED_MODULES if hasattr(m, '__stats__')]:
        if txt := await module.__stats__():
            text += txt

    return html_white_text(text)


async def __stats__():
    text = ""
    text += "* Database structure version <code>{}</code>\n".format(
        (await db.db_structure.find_one({}))['db_ver']
    )
    local_db = await db.command("dbstats")
    if 'fsTotalSize' in local_db:
        text += '* Database size is <code>{}</code>, free <code>{}</code>\n'.format(
            convert_size(local_db['dataSize']),
            convert_size(local_db['fsTotalSize'] - local_db['fsUsedSize'])
        )
    else:
        text += '* Database size is <code>{}</code>, free <code>{}</code>\n'.format(
            convert_size(local_db['storageSize']),
            convert_size(536870912 - local_db['storageSize'])
        )

    text += "* <code>{}</code> total keys in Redis database\n".format(len(redis.keys()))
    text += "* <code>{}</code> total commands registred, in <code>{}</code> modules\n".format(
        len(REGISTRED_COMMANDS), len(LOADED_MODULES))
    return text


@get_strings_dec('owner_stuff')
async def __user_info__(message, user_id, strings):
    if user_id == OWNER_ID:
        return strings["father"]
    elif user_id in OPERATORS:
        return strings['sudo_crown']
    elif user_id in DEVS:
        return strings['dev']
