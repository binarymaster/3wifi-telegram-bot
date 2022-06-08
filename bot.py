# imports #
import os
import asyncio
import json
import re
from random import sample
import string
import logging
import requests
import wpspin                
import subprocess
from enum import IntEnum
from datetime import datetime 
import flag

# aiogram #
from aiogram import Bot
from aiogram import Dispatcher
from aiogram import types
from aiogram import F
from aiogram.dispatcher.filters.callback_data import CallbackData

# static #
SERVICE_URL = 'https://3wifi.stascorp.com'
USERS_FILE = 'users.json'
CONFIG_FILE = 'config.json'
LANG_DIR = 'languages'
SEPARATOR = '================\n'
BOT_USERNAME = "wifi3_bot"

# status #
class Status(IntEnum):
    UNAUTH = 0
    LOGIN = 1
    PASS = 2
    AUTH = 3
    MAYDAY = 4

# configuration #
class Config:
    def __init__(self, path):
        try:
            self.path = path
            with open(self.path, 'r', encoding = 'utf-8') as c:
                raw = json.load(c)
            self.token = raw['token']
            self.key = raw['key']
            self.mayday = raw['mayday']
            self.codes = raw['codes']
            self.acodes = raw['acodes']
        except FileNotFoundError:
            print('No configuration file. Enter new parameters:')
            self.token = input('Bot token > ')
            self.key = input('Api Key > ')
            self.mayday = input('Mayday (0 or 1) > ')
            self.codes = []
            self.acodes = []
            self.update()
    def update(self):
        with open(self.path, 'w', encoding = 'utf-8') as c:
            json.dump({
                'token': self.token,
                'key': self.key,
                'mayday': self.mayday,
                'codes': self.codes,
                'acodes': self.acodes
                }, c, indent = 4)
    def code(self, t):
        check = []
        for u in users.data:
            if users.data[u]['code'] != ' ':
                check.append(users.data[u]['code'])
            elif users.data[u]['acode'] != ' ':
                check.append(users.data[u]['acode'])
        code = ''.join(sample(string.ascii_letters + string.digits, 16))
        while code in check:
            code = ''.join(sample(string.ascii_letters + string.digits, 16))
        else:
            if t == 'acodes': self.acodes.append(code)
            else: self.codes.append(code)
            self.update()
            return code
    def remcode(self, code, t):
        if t == 'acodes': self.acodes.remove(code)
        else: self.codes.remove(code)
cfg = Config(CONFIG_FILE)

# users #
class Users:
    def __init__(self, path):
        try:
            self.path = path
            with open(self.path, 'r', encoding = 'utf-8') as c:
                self.data = json.load(c)
        except FileNotFoundError:
            with open(self.path, 'w', encoding = 'utf-8') as c:
                self.data = {}
                self.update()
    def update(self):
        with open(self.path, 'w', encoding = 'utf-8') as c:
            json.dump(self.data, c, indent = 4)
    def getstatus(self, mess):
        try:
            if self.data[str(mess.from_user.id)]['login'] == ' ':
                return Status.UNAUTH
            elif self.data[str(mess.from_user.id)]['login'] == '///login///':
                return Status.LOGIN
            elif self.data[str(mess.from_user.id)]['pass'] == ' ':
                return Status.PASS
            elif self.data[str(mess.from_user.id)]['key'] == ' ':
                return Status.UNAUTH
            if self.data[str(mess.from_user.id)]['code'] != ' ':
                return Status.MAYDAY
            else:
                return Status.AUTH
        except:
            code = mess.from_user.language_code
            self.mod(mess = mess, login = ' ',
                password = ' ', key = ' ',
                code = ' ', acode = ' ',
                language = 'ua' if code == 'ua' else 'ru' if code == 'ru' else 'us')
            return Status.UNAUTH
    def mod(self, mess = None, user_id = None, login = None, password = None,
        key = None, code = None, acode = None, language = None):
        user_id = str(mess.from_user.id) if user_id == None else user_id
        self.data[user_id] = {
        'login': login if login else self.data[user_id]['login'],
        'pass': password if password else self.data[user_id]['pass'],
        'key': key if key else self.data[user_id]['key'],
        'code': code if code else self.data[user_id]['code'],
        'acode': acode if acode else self.data[user_id]['acode'],
        'language': language if language else self.data[user_id]['language']
        }
        self.update()
    def admin(self, mess):
        if self.data[str(mess.from_user.id)]['acode'] != ' ':
            return True
        elif self.data[str(mess.from_user.id)]['key'] == cfg.key:
            return True
        else: 
            return False
    def super(self, mess):
        if self.data[str(mess.from_user.id)]['key'] == cfg.key:
            return True
        else:
            return False
    def lang(self, mess):
        return self.data[str(mess.from_user.id)]['language']
    def langbyuid(self, uid):
        return self.data[uid]['language']
    def admins(self, mess):
        admins = {}
        for d in self.data:
            if self.data[d]['acode'] != ' ':
                admins[d] = self.data[d]
        return admins
    def maydayusers(self, mess):
        users = {}
        for d in self.data:
            if self.data[d]['code'] != ' ':
                userss[d] = self.data[d]
        return users
    def freecodes(self):
        used = []
        for u in users.data:
            if users.data[u]['code'] in cfg.codes:
                used.append(users.data[u]['code'])
        return list(set(cfg.codes) - set(used)) + list(set(used) - set(cfg.codes))
    def freeacodes(self):
        used = []
        for u in users.data:
            if users.data[u]['acode'] in cfg.acodes:
                used.append(users.data[u]['acode'])
        return list(set(cfg.acodes) - set(used)) + list(set(used) - set(cfg.acodes))
    def security(self, login):
        unsec = []
        for u in users.data:
            if users.data[u]['login'] == login:
                unsec.append(u)
        return unsec
users = Users(USERS_FILE)

# language #
class Languages:
    def __init__(self, path):
        try:
            self.data = {}
            for f in os.listdir(path):
                with open(f'{path}/{f}', 'r', encoding = 'utf-8') as l:
                    self.data[f.replace('.lang', '')] = json.load(l)
        except Exception as ex:
            print(ex)
    def langs(self):
        return [l for l in self.data]
    def getmess(self, mess, what):
        return self.data[users.lang(mess)][what]
    def getmessbyuid(self, uid, what):
        return self.data[users.langbyuid(uid)][what]
lng = Languages(LANG_DIR)

# splitter #
def splitter(mess):
    if len(mess) > 4096:
        splitmess = mess.split(SEPARATOR)
        while '' in splitmess:
            splitmess.remove('')
        mess = []
        app = ''
        for blk in splitmess:
            if len(app + blk) >= 4096:
               mess.append(app)
               app = blk + SEPARATOR
            else:
                app += blk + SEPARATOR
        return mess
    else:
        mess = list().append(mess)
        return mess

# data reactors #
def vuln_reactor(text):
    with open('vuln.data', 'r', encoding = 'utf-8') as vuln:
        vulns = vuln.read().split('\n')
    built = ''
    for v in vulns:
        if text.lower() in v.lower():
            built += f'`{v}`\n'
    return built if len(built) > 0 else None
def cost_code_reactor(text, f, full = None):
    with open(f, 'r', encoding = 'utf-8') as t:
        templates = t.read().split('\n')
    while '' in templates:
        templates.remove('')
    if full:
        fl = ''
        for t in templates:
            fl += f"`{t}`\n"
        return fl
    for t in templates:
        if t.lower() in text.lower():
            return True
    else:
        return False

# data changer #
def changer(text, mode, f):
    with open(f, 'r', encoding = 'utf-8') as data:
        d = data.read().split('\n')
        l1 = len(d)
    try:
        if mode == 0:
            d.remove(text)
        elif mode == 1:
            d.append(text)
        l2 = len(d)
        while '' in d:
            d.remove('')
        with open(f, 'w', encoding = 'utf-8') as data:
            for n in d:
                data.write(f"{n}\n")
        if l1 < l2 or l2 < l1:
            return True
        else:
            return False
    except:
        return False

# bot #
bot = Bot(token = cfg.token)
dp = Dispatcher()

# callbacks #
class WpsCallback(CallbackData, prefix = 'wps'):
    wps: int
class LangCallback(CallbackData, prefix = 'lang'):
    lang: str
class MaydayCallback(CallbackData, prefix = "md"):
    turn: int

# logger #
logform = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format = logform, level = logging.DEBUG)
log = logging.getLogger(__name__)

# filters #
MAC = r'(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})'

# bot body #
@dp.message(commands = ['start'])
async def start_mess(message: types.Message):
    if users.getstatus(message) == Status.AUTH or users.getstatus(message) == Status.MAYDAY:
        await help_mess(message)
    elif users.getstatus(message) == Status.UNAUTH:
        await message.reply(lng.getmess(message, "start").format(url = SERVICE_URL), parse_mode = "Markdown")

@dp.message(commands = ['help'])
async def help_mess(message: types.Message):
    if users.getstatus(message) == Status.AUTH or users.getstatus(message) == Status.MAYDAY:
        if users.admin(message) == True and message.from_user.id == message.chat.id:
            await message.reply(lng.getmess(message, "adm_help") + 
                lng.getmess(message, "help"), parse_mode = "Markdown")
        else:
            await message.reply(lng.getmess(message, "help"), parse_mode = "Markdown")

@dp.message(commands = ['users'])
async def users_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        if users.super(message) == True:
            adm = users.admins(message)
            if adm == {}:
                await message.reply(lng.getmess(message, "adm_noadmins"), parse_mode = "Markdown")
            else:
                mess = lng.getmess(message, "adm_admins") + ': \n'
                for admin in adm:
                    mess += f'{lng.getmess(message, "users_id")} : {admin}\n'
                    mess += f'{lng.getmess(message, "code")} : {adm[admin]["acode"]}\n'
                    mess += f'{lng.getmess(message, "remove")} : /deladmin{user}\n'
                    mess += SEPARATOR
                mess = splitter(mess)
                for m in mess:
                    await message.reply(m, parse_mode = "Markdown")
        mayusers = users.maydayusers(message)
        if mayusers == {}:
            await message.reply(f'{lng.getmess(message, "mayday_state")}: `{lng.getmess(message, "off")}`', parse_mode = "Markdown")
        else:
            mess = lng.getmess(message, "mayday_users")
            for user in mayusers:
                mess += f'{lng.getmess(message, "users_id")} : {user}\n'
                mess += f'{lng.getmess(message, "code")} : {mayusers[user]["code"]}\n'
                mess += f'{lng.getmess(message, "remove")} : /del{user}\n'
                mess += SEPARATOR
            mess = splitter(mess)
            for m in mess:
                await message.reply(m, parse_mode = "Markdown")

@dp.message(commands = ['add'])
async def add_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        await message.reply(f'{lng.getmess(message, "users_code")}: `{cfg.code("codes")}`', parse_mode = "Markdown")

@dp.message(commands = ['addadmin'])
async def add_admin_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        await message.reply(f'{lng.getmess(message, "admin_code")}: `{cfg.code("acodes")}`', parse_mode = "Markdown")

@dp.message(text_startswith = '/del')
async def del_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        user_id = message.text.replace('/del', '').strip()
        users.mod(user_id = user_id, login = ' ', password = ' ',
            key = ' ', code = ' ', acode = ' ')
        cfg.remcode(message.text, "codes")
        await message.reply(lng.getmess(message, "user_del"))

@dp.message(text_startswith = '/deladmin')
async def deladmin_mess(message: types.Message):
    if users.super(message) == True and message.from_user.id == message.chat.id:
        user_id = message.text.replace('/deladmin', '').strip()
        users.mod(user_id = user_id, acode = ' ')
        cfg.remcode(message.text, "acodes")
        await message.reply(lng.getmess(message, "adm_del"))

@dp.message(commands = ['mayday'])
async def mayday_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        key_yes = types.InlineKeyboardButton(text = '✅', callback_data = MaydayCallback(turn = 1).pack())
        key_no = types.InlineKeyboardButton(text = '❌', callback_data = MaydayCallback(turn = 0).pack())
        kb = types.InlineKeyboardMarkup(inline_keyboard = [[key_yes, key_no]])
        if cfg.mayday == '0':
            await message.reply(lng.getmess(message, "mayday_question_on"), parse_mode = "Markdown", reply_markup = kb)
        elif cfg.mayday == '1':
            await message.reply(lng.getmess(message, "mayday_question_off"), parse_mode = "Markdown", reply_markup = kb)

@dp.message(commands = ['login'])
async def login_mess(message: types.Message):
    if users.getstatus(message) == Status.UNAUTH and message.from_user.id == message.chat.id:
        users.mod(mess = message, login = '///login///')
        await message.reply(lng.getmess(message, "login_wait"), parse_mode = "Markdown")

@dp.message(commands = ['logout'])
async def logout_mess(message: types.Message):
    if users.getstatus(message) == Status.AUTH and message.from_user.id == message.chat.id:
        users.mod(mess = message, login = ' ', password = ' ',  key = ' ')
        await message.reply(lng.getmess(message, "logout"), parse_mode = "Markdown")
@dp.message(commands = ['lang'])
async def lang_mess(message: types.Message):
    if users.getstatus(message) == Status.AUTH and message.from_user.id == message.chat.id:
        langs = lng.langs()
        keys = []
        kbd = []
        for l in langs:
            if len(keys) < 3:
                keys.append(types.InlineKeyboardButton(text = flag.flag(l), callback_data = LangCallback(lang = l).pack()))
            else:
                kbd.append(keys)
                keys = []
                keys.append(types.InlineKeyboardButton(text = flag.flag(l), callback_data = LangCallback(lang = l).pack()))
        kbd.append(keys)
        kb = types.InlineKeyboardMarkup(inline_keyboard = kbd)
        await message.reply(lng.getmess(message, "lang_choose"), parse_mode = "Markdown", reply_markup = kb)

@dp.message(commands = ['vuln'])
async def vuln_mess(message: types.Message):
    query = message.text.replace('/vuln', '').replace(f'@{BOT_USERNAME}', '').strip()
    if msg := vuln_reactor(query):
        await message.reply(msg, parse_mode = "Markdown")
    else:
        await message.reply(lng.getmess(message, "nothing"), parse_mode = "Markdown")

@dp.message(commands = ['remvuln'])
async def remvuln_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        query = message.text.replace('/remvuln ', '').strip()
        if changer(query, 0, 'vuln.data') == True:
            await message.reply(lng.getmess(message, "removed"), parse_mode = "Markdown")
        else:
            await message.reply(lng.getmess(message, "no_changes"), parse_mode = "Markdown")

@dp.message(commands = ['addvuln'])
async def addvuln_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        query = message.text.replace('/addvuln ', '').strip()
        if changer(query, 1, 'vuln.data') == True:
            await message.reply(lng.getmess(message, "added"), parse_mode = "Markdown")
        else:
            await message.reply(lng.getmess(message, "no_changes"), parse_mode = "Markdown")

@dp.message(commands = ['remcode'])
async def remcode_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        query = message.text.replace('/remcode ', '').strip()
        if changer(query, 0, 'code.data') == True:
            await message.reply(lng.getmess(message, "removed"), parse_mode = "Markdown")
        else:
            await message.reply(lng.getmess(message, "no_changes"), parse_mode = "Markdown")

@dp.message(commands = ['addcode'])
async def addcode_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        query = message.text.replace('/addcode ', '').strip()
        if changer(query, 1, 'code.data') == True:
            await message.reply(lng.getmess(message, "added"), parse_mode = "Markdown")
        else:
            await message.reply(lng.getmess(message, "no_changes"), parse_mode = "Markdown")

@dp.message(commands = ['remcost'])
async def remcost_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        query = message.text.replace('/remcost ', '').strip()
        if changer(query, 0, 'cost.data') == True:
            await message.reply(lng.getmess(message, "removed"), parse_mode = "Markdown")
        else:
            await message.reply(lng.getmess(message, "no_changes"), parse_mode = "Markdown")

@dp.message(commands = ['addcost'])
async def addcost_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        query = message.text.replace('/addcost ', '').strip()
        if changer(query, 1, 'cost.data') == True:
            await message.reply(lng.getmess(message, "added"), parse_mode = "Markdown")
        else:
            await message.reply(lng.getmess(message, "no_changes"), parse_mode = "Markdown")

@dp.message(commands = ['listcode'])
async def listcode_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        await message.reply(cost_code_reactor(message.text.replace('/listcode', '').strip(), 'code.data', full = True), parse_mode = "Markdown")

@dp.message(commands = ['listcost'])
async def listcode_mess(message: types.Message):
    if users.admin(message) == True and message.from_user.id == message.chat.id:
        await message.reply(cost_code_reactor(message.text.replace('/listcost', '').strip(), 'cost.data', full = True), parse_mode = "Markdown")

@dp.message(commands = ['pw', 'pws'])
async def search_mess(message: types.Message):
    if users.getstatus(message) == Status.AUTH or users.getstatus(message) == Status.MAYDAY:
        com = '/pws' if '/pws' in message.text else '/pw'
        query = message.text.replace(com, '').replace(f'@{BOT_USERNAME}', '').strip()
        if query == '':
            await message.reply(lng.getmess(message, "empty"), parse_mode = "Markdown")
        else:
            try:
                macs = [m for m in re.findall(MAC, query)]
                for m in macs:
                    query = query.replace(m, '').strip()
            except:
                query = query.strip()
            finally:
                    p = {'key': users.data[str(message.from_user.id)]['key'] if users.getstatus(message) == Status.AUTH else ADMIN_KEY, 
                        'essid': query if query != [] else '*', 
                        'bssid': [m for m in macs] if macs != [] else '*',
                        'sens': True if com == '/pws' else False
                        }
                    r = requests.post(f'{SERVICE_URL}/api/apiquery', json = p).json()
                    if r['result'] == True and r['data'] != []:
                        order = ['essid', 'bssid', 'key', 'wps', 'time', 'lat', 'lon']
                        prebuilt = {}
                        built = ''
                        result = r['data']
                        for mac in result:
                            for data in result[mac]:
                                for item in order:
                                    try:
                                        if data[item] == '' or data[item] == '<empty>' or data[item] == None: pass
                                        else: prebuilt[item] = data[item]
                                    except: pass
                                for every in prebuilt:
                                    if every == 'time':
                                        built += f'{lng.getmess(message, f"s_{every}") }:  `{datetime.strptime(prebuilt[every], "%Y-%m-%d %H:%M:%S").date()}`\n'
                                    elif every == 'lat':
                                        built += f'{lng.getmess(message, f"s_maps")}: '
                                        built += f'[3WiFi]({SERVICE_URL}/map?lat={prebuilt["lat"]}&lon={prebuilt["lon"]}), '
                                        built += f'[Google](https://www.google.com/maps/search/?api=1&query={prebuilt["lat"]},{prebuilt["lon"]})\n'
                                    elif every == 'lon': pass
                                    else: built += f'{lng.getmess(message, f"s_{every}")}:  `{prebuilt[every]}`\n'
                                prebuilt = {}
                                built += SEPARATOR
                        await message.reply(built,
                            parse_mode = "Markdown", disable_web_page_preview = True)
                    else:
                        button = types.InlineKeyboardButton(text = lng.getmess(message, 'wps_callback_start'), 
                            callback_data = WpsCallback(wps = 1).pack())
                        kbd = types.InlineKeyboardMarkup(inline_keyboard = [[button]])
                        await message.reply(lng.getmess(message, 'nothing'), 
                            parse_mode = "Markdown", reply_markup = kbd if len(macs) > 0 else None)

@dp.message(commands = ['wps'])
async def wps_mess(message: types.Message, inline = None):
    if users.getstatus(message if message else inline['message']) == Status.AUTH or users.getstatus(message if message else inline['message']) == Status.MAYDAY:
        if inline:
            query = inline['query']
        else: 
            query = message.text.replace('/wps', '').replace(f'@{BOT_USERNAME}', '').strip()
        if query == '':
            await message.reply(lng.getmess(message, "empty"), parse_mode = "Markdown")
        else:
            try:
                macs = [m.upper().replace('-', ':') for m in re.findall(MAC, query)]
            finally:
                uid = str(message.from_user.id) if message else str(inline['message'].from_user.id)
                p = {'key': users.data[uid]['key'] if users.getstatus(message if message else inline['message']) == Status.AUTH else ADMIN_KEY, 
                    'bssid': [m for m in macs]}
                r = requests.post(f'{SERVICE_URL}/api/apiwps', json = p).json()
                if r['result'] == True and r['data'] != []:
                    built = ''
                    maxi = 10
                    limiter = 0
                    for every in r['data']:
                        built += f'`{every}`\n'
                        built += SEPARATOR
                        for line in r['data'][every]:
                            for data in r['data'][every][line]:
                                if limiter < maxi:
                                    limiter += 1
                                else: break
                                for attr in data:
                                    if attr == 'fromdb': pass
                                    elif attr == 'score':
                                        built += f'{lng.getmess(message if message else inline["message"], f"w_{attr}")}: `{float(data[attr]) * 100:.2f}%`\n'
                                    else:
                                        built += f'{lng.getmess(message if message else inline["message"], f"w_{attr}")}: `{data[attr]}`\n'
                                built += SEPARATOR
                    if inline == None:
                        await message.reply(built, parse_mode = "Markdown", disable_web_page_preview = True)
                    else:
                        return built
                elif inline == None:
                    await message.reply(lng.getmess(message, 'nothing'), parse_mode = "Markdown")
                else:
                    return lng.getmess(message, 'nothing_wps')

@dp.message(commands = ['wpsg'])
async def wpsg_mess(message: types.Message):
    if users.getstatus(message) == Status.AUTH or users.getstatus(message) == Status.MAYDAY:
        query = message.text.replace('/wps', '').replace(f'@{BOT_USERNAME}', '').strip()
        if query == '':
            await message.reply(lng.getmess(message, 'empty'), parse_mode = "Markdown")
        else:
            try:
                mac = [m.upper().replace('-', ':') for m in re.findall(MAC, query)][0]
            finally:
                gen = wpspin.WPSpin()
                gen = gen.getAll(mac)
                built = f'<code>{mac}</code>\n'
                built += SEPARATOR
                for pin in gen:
                    built += f'<code>{pin["name"]}</code>\n{lng.getmess(message, "w_value")}: <code>{pin["pin"]}</code>\n'
                    built += SEPARATOR
                await message.reply(built, parse_mode = "HTML")

"""
@dp.message(commands = ['whatis'])
async def who_mess(message: types.Message):
    if users.getstatus(message) == Status.AUTH or users.getstatus(message) == Status.MAYDAY:
        query = message.text.replace('/whatis ', '').replace(f'@{BOT_USERNAME}', '').strip()
        if query == '':
            await message.reply(lang.get(ulang(uid), 'empty'), parse_mode = "Markdown")
        else:
            try:
                mac = [m.upper().replace('-', ':') for m in re.findall(MAC, query)][0]
            finally:
                s = requests.Session()
                s.post(f'{SERVICE_URL}/user.php?a=login', 
                    data = {'login': users.data[str(message.from_user.id)]['login'], 
                        'password': users.data[str(message.from_user.id)]['pass']})
                get = s.post(f'{SERVICE_URL}/3wifi.php?a=devicemac', data = {'bssid': mac}).json()
                s.get(f'{SERVICE_URL}/user.php?a=logout6{s.get(f"{SERVICE_URL}/user.php?a=token").json()["token"]}')
                if get['result'] == True:
                    mess = f'`{mac}` {lng.getmess(message, "who")}:\n'
                    mess += SEPARATOR
                    maxi = 10
                    limiter = 0
                    for s in get['scores']:
                        if limiter < maxi:
                            limiter += 1
                            mess += f'`{s["name"]}`\n{lng.getmess(message, "w_score")}: `{s["score"] * 100:.2f}%`\n'
                            mess += SEPARATOR
                    await message.reply(mess, parse_mode = "Markdown")
                else:
                    await message.reply(lng.getmess(message, 'nothing'), parse_mode = "Markdown")
"""

@dp.message(commands = ['where'])
async def where_mess(message: types.Message):
    if users.getstatus(message) == Status.AUTH or users.getstatus(message) == Status.MAYDAY:
        query = message.text.replace('/where ', '').replace(f'@{BOT_USERNAME}', '').strip()
        if query == '':
            await message.reply(lang.get(ulang(uid), 'empty'), parse_mode = "Markdown")
        else:
            try:
                mac = [m.upper().replace('-', ':') for m in re.findall(MAC, query)][0]
            finally:
                out = subprocess.check_output(['geomac', mac]).decode('utf-8').split('\n')
                if out[1] == 'no results':
                    await message.reply(lang.get(ulang(uid), 'nothing'), parse_mode = "Markdown")
                else:
                    splitter = out[1].split('|')[1].split(',')
                    lat = splitter[0].strip()
                    lon = splitter[1].strip()
                    data = {'mac': mac, 'lat': lat, 'lon': lon}
                    built = f'{data["mac"]}\n`{data["lon"]}, {data["lat"]}`\n{lng.getmess(message, "s_maps")}: '
                    built += f'[3WiFi]({SERVICE_URL}/map?lat={data["lat"]}&lon={data["lon"]}), '
                    built += f'[Google](https://www.google.com/maps/search/?api=1&query={data["lon"]},{data["lat"]})\n'
                    await message.reply(built, parse_mode = "Markdown", disable_web_page_preview = True)
                    await bot.send_location(message.chat.id, longitude = lon, latitude = lat, reply_to_message_id = message.message_id)

@dp.message(F.func(lambda F: users.getstatus(F) == Status.LOGIN) & (F.from_user.id == F.chat.id))
async def login_handler(message: types.Message):
    users.mod(mess = message, login = message.text)
    await message.reply(lng.getmess(message, "password_wait"), parse_mode = "Markdown")

@dp.message((F.func(lambda F: users.getstatus(F) == Status.PASS)) & (F.from_user.id == F.chat.id))
async def password_handler(message: types.Message):
    users.mod(mess = message, password = message.text)
    try:
        r = requests.post(f"{SERVICE_URL}/api/apikeys", json = {
            'login': users.data[str(message.from_user.id)]['login'],
            'password': users.data[str(message.from_user.id)]['pass'],
            'genread': True}).json()
        if r['result']:
            if r['profile']['level'] > 0:
                nick = r['profile']['nick']
                for k in r['data']:
                    if k['access'] == 'read':
                        key = k['key']
                        break
                users.mod(message, key = key)
                await message.reply(lng.getmess(message, "logged_in"), parse_mode = "Markdown")
                for user in users.security(users.data[str(message.from_user.id)]['login']):
                    if user != str(message.from_user.id):
                        await bot.send_message(user, lng.getmessbyuid(user, "security").format(
                            name = f'{message.from_user.first_name if message.from_user.first_name else ""} {message.from_user.last_name if message.from_user.last_name else ""}',
                            uid = f'`{message.from_user.id}`',
                            username = f"@{message.from_user.username}" if message.from_user.username else ""), parse_mode = "Markdown")
        elif r['error'] == 'loginfail':
            users.mod(message, login = ' ', password = ' ', key = ' ')
            await message.reply(lng.getmess(message, "bad_cred"))
        elif r['error'] == 'lowlevel':
            users.mod(message, login = ' ', password = ' ', key = ' ')
            await message.reply(lng.getmess(message, "banned"))
    except:
        pass

@dp.message((F.text.in_(users.freecodes())) & (F.from_user.id == F.chat.id) | (F.text.in_(users.freeacodes())) & (F.from_user.id == F.chat.id))
async def add_admin_add_user_hanler(message: types.Message):
    if users.admin(message) == False:
        if message.text in users.freecodes() and cfg.mayday == '1':
            users.mod(mess = message , code = message.text)
            await message.reply(lng.getmess(message, "bot_active"))
        elif message.text in users.freeacodes():
            users.mod(mess = message , acode = message.text)
            await message.reply(lng.getmess(message, "admin_added"))

@dp.message(F.from_user.id == F.chat.id)
async def others_inside(message: types.Message):
    if users.getstatus(message) == Status.UNAUTH:
        await message.reply(lng.getmess(message, "auth_req"))
    elif users.getstatus(message) == Status.AUTH:
        mtl = message.text.lower()
        if 'героям слава' in mtl or 'хейт лисички' in mtl or 'my name is jhon cina' in mtl:
            await message.reply(lng.getmess(message, "egg"))

@dp.message()
async def others_outside(message: types.Message):
    if users.getstatus(message) == Status.UNAUTH:
        if cost_code_reactor(message.text, 'cost.data'):
            await message.reply('Стоимость инвайта = 5$\nInvite price = 5$')
        elif cost_code_reactor(message.text, 'code.data'):
            await message.reply('[# Информация о покупке #](https://t.me/routerscan/145429)\n[# Purchase Information #](https://t.me/routerscan/145429)', parse_mode = "Markdown", disable_web_page_preview = True)

@dp.callback_query(LangCallback.filter(F.lang.in_(lng.langs())))
async def language_handler(query: types.CallbackQuery, callback_data: LangCallback):
    to_edit_id = query.message.message_id
    chat_id = query.message.chat.id
    if query.message.reply_to_message.from_user.id == query.from_user.id:
        users.mod(query, language = callback_data.lang)
        await bot.edit_message_text(lng.getmess(query, "lang_chosen"), chat_id = chat_id, message_id = to_edit_id)

@dp.callback_query(MaydayCallback.filter(F.turn.in_([0, 1])))
async def mayday_handler(query: types.CallbackQuery, callback_data: MaydayCallback):
    to_edit_id = query.message.message_id
    chat_id = query.message.chat.id
    if query.message.reply_to_message.from_user.id == query.from_user.id:
        if cfg.mayday == '0':
            if callback_data.turn == 0:
                await bot.edit_message_text(lng.getmess(query, "okay"), 
                    chat_id = chat_id, message_id = to_edit_id)
            elif callback_data.turn == 1:
                cfg.mayday = '1'
                cfg.update()
                await bot.edit_message_text(f'{lng.getmess(query, "mayday_state")}: `{lng.getmess(query, "on")}`', 
                    chat_id = chat_id, message_id = to_edit_id, parse_mode = "Markdown")
        elif cfg.mayday == '1':
            if callback_data.turn == 0:
                await bot.edit_message_text(lng.getmess(query, "okay"), 
                    chat_id = chat_id, message_id = to_edit_id)
            elif callback_data.turn == 1:
                cfg.mayday = '0'
                cfg.update()
                await bot.edit_message_text(f'{lng.getmess(query, "mayday_state")}: `{lng.getmess(query, "off")}`', 
                    chat_id = chat_id, message_id = to_edit_id, parse_mode = "Markdown") 

@dp.callback_query(WpsCallback.filter(F.wps == 1))
async def wps_handler(query: types.CallbackQuery, callback_data: WpsCallback):
    to_edit_id = query.message.message_id
    chat_id = query.message.chat.id
    if query.from_user.id == query.message.reply_to_message.from_user.id:
        inline = {'message':query.message.reply_to_message}
        inline['query'] = query.message.reply_to_message.text.replace('/wps', '').replace(f'@{BOT_USERNAME}', '').strip()
        await bot.edit_message_text(await wps_mess(None, inline = inline), chat_id = chat_id, message_id = to_edit_id, parse_mode = "Markdown", disable_web_page_preview = True)
    else:
        await bot.answer_callback_query(callback_query_id = query.id, text = lng.getmess(message, 'wps_callback_no'), show_alert = True)

if __name__ == '__main__':
    dp.run_polling(bot)
