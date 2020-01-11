#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import re
import logging
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

USER_KEYS_DB_FILENAME = 'userkeys.json'

# Initializing settings
try:
    with open('config.json', 'r', encoding='utf-8') as file:
        config = json.load(file)
        TOKEN = config['bot_token']
        IP = config['webhook_ip']
        API_KEY = config['3wifi_apikey']
except FileNotFoundError:
    print('Please provide the following credentials')
    TOKEN = input('Telegram bot API token: ')
    IP = input('IP for webhook: ')
    API_KEY = input('3WiFi API read key: ')
    config = {
        'bot_token': TOKEN,
        'webhook_ip': IP,
        '3wifi_apikey': API_KEY
    }
    with open('config.json', 'w', encoding='utf-8') as outf:
        json.dump(config, outf, indent=4)

# Initializing user API keys database
try:
    with open(USER_KEYS_DB_FILENAME, 'r', encoding='utf-8') as file:
        USER_KEYS = json.load(file)
except FileNotFoundError:
    USER_KEYS = dict()
    with open(USER_KEYS_DB_FILENAME, 'w', encoding='utf-8') as outf:
        json.dump(USER_KEYS, outf, indent=4)

bssid_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)


def unknown(update, context):
    update.message.reply_text('Команда не найдена! Отправьте /help для получения информации по доступным командам')


def help(update, context):
    update.message.reply_text(f'''3wifi.stascorp.com бот!
/pw bssid и/или essid - поиск по мак адресу или имени точки (пример: /pw FF:FF:FF:FF:FF:FF или /pw netgear или /pw FF:FF:FF:FF:FF:FF VILTEL)
/pws - /pw, но с учётом регистра (essid)
/wps bssid - поиск wps пина по мак адресу (пример: /wps FF:FF:FF:FF:FF:FF)
/authorize login:password - авторизоваться с личным аккаунтом 3WiFi для снятия временных ограничений бота''')


def printap(value):
    answer = f"""ESSID: `{value['essid']}`
BSSID: `{value['bssid']}`
Password: `{value['key']}`
WPS pin: `{value['wps']}`
Time: {value['time']}
"""
    if 'lat' in value:
        answer += f"[Точка на карте](http://3wifi.stascorp.com/map?lat={value['lat']}&lon={value['lon']})\n"
    else:
        answer += '- - - - -\n'
    return answer


def printaps(values):
    answer = ''
    for value in values:
        answer += printap(value)
    return answer


def CheckAPresponse(data):
    if data['result'] == 0:
        if data['error'] == 'cooldown':
            return 'Узбагойся и попробуй ещё раз через 10 сек 😜'
        else:
            return 'Что-то пошло не так 😮 error: ' + data['error']
    if len(data['data']) == 0:
        return 'Нет результатов :('
    return ''


def authorize(update, context):
    answer = 'Авторизация выполняется так: /authorize login:password'
    tmp = update.message.text.split()
    if len(tmp) == 2:
        arg = tmp[1]
        tmp = arg.split(':')
        if len(tmp) == 2:
            login, password = tmp
            r = requests.post(f'https://3wifi.stascorp.com/api/apikeys', data={'login': login, 'password': password}).json()
            if r['result']:
                user_id = str(update.message.from_user.id)
                nickname = r['profile']['nick']
                apikey = list(filter(lambda x: x['access'] == 'read', r['data']))[0]['key']
                USER_KEYS[user_id] = apikey
                with open(USER_KEYS_DB_FILENAME, 'w', encoding='utf-8') as outf:
                    json.dump(USER_KEYS, outf, indent=4)
                answer = 'Вы успешно авторизованы как *{}*'.format(nickname)
            elif r['error'] == 'loginfail':
                answer = 'Ошибка - проверьте логин и пароль'
            else:
                answer = 'Что-то пошло не так 😮 error: {}'.format(r['error'])
    update.message.reply_text(answer, parse_mode='Markdown')


def getPersonalAPIkey(user_id):
    user_id = str(user_id)
    if user_id in USER_KEYS:
        return USER_KEYS[user_id]
    else:
        return API_KEY


def pw(update, context):
    answer = 'Забыли ввести bssid или essid! Поиск по bssid и/или essid выполняется так: /pw bssid/essid (пример: /pw FF:FF:FF:FF:FF:FF VILTEL или /pw FF:FF:FF:FF:FF:FF или /pw netgear)'
    API_KEY = getPersonalAPIkey(update.message.from_user.id)
    tmp = update.message.text.split()
    if len(tmp) == 2:
        answer = ''
        if re.match(bssid_pattern, tmp[1]) is not None:
            results = requests.get(f'https://3wifi.stascorp.com/api/apiquery?key={API_KEY}&bssid={tmp[1]}').json()
            answer = CheckAPresponse(results)
            if answer == '':
                answer = printaps(results['data'][f'{tmp[1]}'.upper()])
        else:
            results = requests.get(f'https://3wifi.stascorp.com/api/apiquery?key={API_KEY}&bssid=*&essid={tmp[1]}').json()
            answer = CheckAPresponse(results)
            if answer == '' and len(results['data']) == 1:
                answer = printaps(results['data'][f'*|{tmp[1]}'])
    elif len(tmp) == 3:
        if re.match(bssid_pattern, tmp[1]) is not None:
            results = requests.get(f'https://3wifi.stascorp.com/api/apiquery?key={API_KEY}&bssid={tmp[1]}&essid={tmp[2]}').json()
            answer = CheckAPresponse(results)
            if answer == '' and len(results['data']) == 1:
                answer = printap(results['data'][f'{tmp[1].upper()}|{tmp[2]}'][0])
    else:
        answer = 'Поиск по bssid и essid выполняется так: /pw bssid essid (пример: /pw FF:FF:FF:FF:FF:FF VILTEL)'
    update.message.reply_text(answer, parse_mode='Markdown')


def pws(update, context):
    answer = 'Забыли ввести bssid или essid! Поиск по bssid и/или essid выполняется так: /pws bssid/essid (пример: /pws FF:FF:FF:FF:FF:FF VILTEL или /pws FF:FF:FF:FF:FF:FF или /pws netgear)'
    API_KEY = getPersonalAPIkey(update.message.from_user.id)
    tmp = update.message.text.split()
    if len(tmp) == 2:
        answer = ''
        if re.match(bssid_pattern, tmp[1]) is not None:
            results = requests.get(f'https://3wifi.stascorp.com/api/apiquery?key={API_KEY}&bssid={tmp[1]}').json()
            answer = CheckAPresponse(results)
            if answer == '':
                answer = printaps(results['data'][f'{tmp[1]}'.upper()])
        else:
            results = requests.get(f'https://3wifi.stascorp.com/api/apiquery?key={API_KEY}&bssid=*&essid={tmp[1]}&sens=true').json()
            answer = CheckAPresponse(results)
            if answer == '':
                answer = printaps(results['data'][f'*|{tmp[1]}'])
    elif len(tmp) == 3:
        if re.match(bssid_pattern, tmp[1]) is not None:
            results = requests.get(f'https://3wifi.stascorp.com/api/apiquery?key={API_KEY}&bssid={tmp[1]}&essid={tmp[2]}&sens=true').json()
            answer = CheckAPresponse(results)
            if answer == '' and len(results['data']) == 1:
                answer = printap(results['data'][f'{tmp[1].upper()}|{tmp[2]}'][0])
    else:
        answer = 'Поиск по bssid и essid выполняется так: /pws bssid essid (пример: /pws FF:FF:FF:FF:FF:FF VILTEL)'
    update.message.reply_text(answer, parse_mode='Markdown')


def wps(update, context):
    answer = 'Поиск wps пин кодов выполняется так: /wps bssid (пример: /wps FF:FF:FF:FF:FF:FF)'
    API_KEY = getPersonalAPIkey(update.message.from_user.id)
    tmp = update.message.text.split()
    if len(tmp) == 2:
        if re.match(bssid_pattern, tmp[1]) is not None:
            results = requests.get('https://3wifi.stascorp.com/api/apiwps?key={}&bssid={}'.format(API_KEY, tmp[1])).json()
            if len(results['data']) > 0:
                answer = ''
                for result in results['data'][tmp[1].upper()]['scores']:
                    result['score'] *= 100
                    if result['score'] < 1:
                        score = "{0:.2f}".format(result['score'])
                    elif result['score'] < 10:
                        score = "{0:.1f}".format(result['score'])
                    else:
                        score = str(round(result['score']))
                    answer += f"""Name: `{result['name']}`
Pin: `{result['value']}`
Score: {score}%
- - - - -
"""
            else:
                answer = 'Нет результатов :('
    if len(answer) > 3900:
        update.message.reply_text(answer[:3900] + '\nСписок слишком большой, смотри дальше на 3wifi.stascorp.com', parse_mode='Markdown')
    else:
        update.message.reply_text(answer, parse_mode='Markdown')


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("help", help))
dp.add_handler(CommandHandler("start", help))
dp.add_handler(CommandHandler("authorize", authorize))
dp.add_handler(CommandHandler("wps", wps))
dp.add_handler(CommandHandler("pw", pw))
dp.add_handler(CommandHandler("pws", pws))
dp.add_handler(MessageHandler(Filters.text | Filters.command, unknown))
dp.add_error_handler(error)
if IP == 'no':
    updater.start_polling(poll_interval=.5)
else:
    updater.start_webhook(listen='0.0.0.0', port=8443, url_path=TOKEN, key='private.key', cert='cert.pem', webhook_url=f'https://{IP}:8443/{TOKEN}')
