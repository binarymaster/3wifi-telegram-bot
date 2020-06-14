#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import re
import logging
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

SERVICE_DOMAIN = '3wifi.stascorp.com'
SERVICE_URL = 'https://' + SERVICE_DOMAIN
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
    answer = '''{} бот!
/pw BSSID и/или ESSID — поиск по MAC-адресу или имени точки (пример: /pw FF:FF:FF:FF:FF:FF или /pw netgear или /pw FF:FF:FF:FF:FF:FF VILTEL)
/pws — то же самое, что /pw, но с учётом регистра (ESSID)
/wps BSSID — поиск WPS пин-кодов по MAC-адресу (пример: /wps FF:FF:FF:FF:FF:FF)'''.format(SERVICE_DOMAIN)
    private_commands = '''\n/login username:password — авторизоваться с личным аккаунтом 3WiFi для снятия ограничений гостевого аккаунта
/logout — выполнить выход из личного аккаунта 3WiFi'''
    if update.message.chat.type == 'private':
        answer += private_commands
    update.message.reply_text(answer)


def printap(data):
    key_labels = {
        'essid': 'ESSID',
        'bssid': 'BSSID',
        'key': 'Password',
        'wps': 'WPS PIN',
        'time': 'Date'
    }
    order = ['essid', 'bssid', 'key', 'wps', 'time']    # Order of values in the answer
    copyable = ['essid', 'bssid', 'key', 'wps']   # Values that can be copied (monospaced font)
    answer = ''
    for element in order:
        if (element in data) and data[element]:   # Check if value is not empty
            key, value = element, data[element]
            if (key in copyable) and (value != '<empty>'):
                answer += f'{key_labels[key]}: `{value}`\n'
            else:
                answer += f'{key_labels[key]}: {value}\n'
    if 'lat' in data:
        answer += f"[Точка на карте]({SERVICE_URL}/map?lat={data['lat']}&lon={data['lon']})\n"
    else:
        answer += '- - - - -\n'
    return answer


def printaps(values):
    answer = ''
    for value in values:
        answer += printap(value)
    return answer


def CheckAPresponse(user_id, data):
    if data['result'] == 0:
        if data['error'] == 'cooldown':
            return 'Узбагойся и попробуй ещё раз через 10 сек 😜'
        elif data['error'] == 'loginfail':
            return 'Ошибка авторизации в 3WiFi. Если вы ранее авторизовывались через /login, попробуйте сделать это снова или выйдите с помощью /logout'
        elif data['error'] == 'lowlevel':
            if user_id in USER_KEYS:
                return 'Недостаточно прав для выполнения команды. Возможно, ваш аккаунт 3WiFi заблокирован'
            else:
                return 'Недостаточно прав для выполнения команды. Вероятно, гостевой аккаунт заблокирован. Купить код приглашения можно тут: https://t.me/routerscan/15931'
        else:
            return 'Что-то пошло не так 😮 error: ' + data['error']
    if len(data['data']) == 0:
        return 'Нет результатов :('
    return ''


def login(update, context):
    if update.message.chat.type != 'private':
        update.message.reply_text('Команда работает только в личных сообщениях (ЛС)')
        return
    answer = 'Авторизация выполняется так: /login username:password'
    tmp = update.message.text.split()
    if len(tmp) == 2:
        arg = tmp[1]
        tmp = arg.split(':')
        if len(tmp) == 2:
            login, password = tmp
            r = requests.post(f'{SERVICE_URL}/api/apikeys', data={'login': login, 'password': password}).json()
            if r['result']:
                if r['profile']['level'] > 0:
                    user_id = str(update.message.from_user.id)
                    nickname = r['profile']['nick']
                    try:
                        apikey = list(filter(lambda x: x['access'] == 'read', r['data']))[0]['key']
                    except IndexError:
                        answer = 'Ошибка — аккаунт *{}* не имеет API ключа на чтение. Получите его на сайте, затем повторите попытку авторизации.'.format(nickname)
                    else:
                        USER_KEYS[user_id] = apikey
                        with open(USER_KEYS_DB_FILENAME, 'w', encoding='utf-8') as outf:
                            json.dump(USER_KEYS, outf, indent=4)
                        answer = 'Вы успешно авторизованы как *{}*. Чтобы выйти, отправьте /logout'.format(nickname)
                        # Send security notification to users with the same token
                        for telegram_id, api_key in USER_KEYS.items():
                            if (apikey == api_key) and (telegram_id != user_id) and (api_key != API_KEY):
                                context.bot.send_message(
                                    chat_id=telegram_id,
                                    text='*Уведомление безопасности*\n[Пользователь](tg://user?id={}) только что авторизовался в боте с вашим аккаунтом 3WiFi.'.format(user_id),
                                    parse_mode='Markdown'
                                    )
                else:
                    answer = 'Ошибка: уровень доступа аккаунта ниже уровня *пользователь*'
            elif r['error'] == 'loginfail':
                answer = 'Ошибка — проверьте логин и пароль'
            else:
                answer = 'Что-то пошло не так 😮 error: {}'.format(r['error'])
    update.message.reply_text(answer, parse_mode='Markdown')


def logout(update, context):
    if update.message.chat.type != 'private':
        update.message.reply_text('Команда работает только в личных сообщениях (ЛС)')
        return
    user_id = str(update.message.from_user.id)
    try:
        USER_KEYS.pop(user_id)
        with open(USER_KEYS_DB_FILENAME, 'w', encoding='utf-8') as outf:
            json.dump(USER_KEYS, outf, indent=4)
    except KeyError:
        answer = 'Ошибка: невозможно выйти из аккаунта 3WiFi, т.к. вы не вошли'
    else:
        answer = 'Выход выполнен, API-ключ вашего аккаунта 3WiFi удалён из базы данных бота. Чтобы авторизоваться снова, воспользуйтесь командой /login'
    update.message.reply_text(answer)


def getPersonalAPIkey(user_id):
    user_id = str(user_id)
    if user_id in USER_KEYS:
        return USER_KEYS[user_id]
    else:
        return API_KEY


def pw(update, context):
    answer = 'Ошибка: не передан BSSID или ESSID.\nПоиск по BSSID и/или ESSID выполняется так: /pw BSSID/ESSID (пример: /pw FF:FF:FF:FF:FF:FF VILTEL или /pw FF:FF:FF:FF:FF:FF или /pw netgear)'
    user_id = str(update.message.from_user.id)
    API_KEY = getPersonalAPIkey(user_id)
    args = context.args
    # Handler for /pw command
    if args is not None:
        if len(args) == 1:
            answer = ''
            if re.match(bssid_pattern, args[0]) is not None:
                results = requests.get(f'{SERVICE_URL}/api/apiquery?key={API_KEY}&bssid={args[0]}').json()
                answer = CheckAPresponse(user_id, results)
                if answer == '':
                    answer = printaps(results['data'][f'{args[0]}'.upper()])
            else:
                results = requests.get(f'{SERVICE_URL}/api/apiquery?key={API_KEY}&bssid=*&essid={args[0]}').json()
                answer = CheckAPresponse(user_id, results)
                if (answer == '') and (len(results['data']) == 1):
                    answer = printaps(results['data'][f'*|{args[0]}'])
        elif len(args) == 2:
            if re.match(bssid_pattern, args[0]) is not None:
                results = requests.get(f'{SERVICE_URL}/api/apiquery?key={API_KEY}&bssid={args[0]}&essid={args[1]}').json()
                answer = CheckAPresponse(user_id, results)
                if (answer == '') and (len(results['data']) == 1):
                    answer = printap(results['data'][f'{args[0].upper()}|{args[1]}'][0])
        else:
            answer = 'Поиск по BSSID и ESSID выполняется так: /pw BSSID ESSID (пример: /pw FF:FF:FF:FF:FF:FF VILTEL)'
    # Handler for BSSID message
    elif context.matches:
        bssid = update.message.text
        results = requests.get(f'{SERVICE_URL}/api/apiquery?key={API_KEY}&bssid={bssid}').json()
        answer = CheckAPresponse(user_id, results)
        if answer == '':
            answer = printaps(results['data'][bssid.upper()])
    update.message.reply_text(answer, parse_mode='Markdown')


def pws(update, context):
    answer = 'Ошибка: не передан BSSID или ESSID.\nПоиск по BSSID и/или ESSID выполняется так: /pws BSSID/ESSID (пример: /pws FF:FF:FF:FF:FF:FF VILTEL или /pws FF:FF:FF:FF:FF:FF или /pws netgear)'
    user_id = str(update.message.from_user.id)
    API_KEY = getPersonalAPIkey(user_id)
    args = context.args
    if len(args) == 1:
        answer = ''
        if re.match(bssid_pattern, args[0]) is not None:
            results = requests.get(f'{SERVICE_URL}/api/apiquery?key={API_KEY}&bssid={args[0]}').json()
            answer = CheckAPresponse(user_id, results)
            if answer == '':
                answer = printaps(results['data'][f'{args[0]}'.upper()])
        else:
            results = requests.get(f'{SERVICE_URL}/api/apiquery?key={API_KEY}&bssid=*&essid={args[0]}&sens=true').json()
            answer = CheckAPresponse(user_id, results)
            if answer == '':
                answer = printaps(results['data'][f'*|{args[0]}'])
    elif len(args) == 2:
        if re.match(bssid_pattern, args[0]) is not None:
            results = requests.get(f'{SERVICE_URL}/api/apiquery?key={API_KEY}&bssid={args[0]}&essid={args[1]}&sens=true').json()
            answer = CheckAPresponse(user_id, results)
            if answer == '' and len(results['data']) == 1:
                answer = printap(results['data'][f'{args[0].upper()}|{args[1]}'][0])
    else:
        answer = 'Поиск по BSSID и ESSID выполняется так: /pws BSSID ESSID (пример: /pws FF:FF:FF:FF:FF:FF VILTEL)'
    update.message.reply_text(answer, parse_mode='Markdown')


def wps(update, context):
    answer = 'Поиск WPS пин-кодов выполняется так: /wps BSSID (пример: /wps FF:FF:FF:FF:FF:FF)'
    user_id = str(update.message.from_user.id)
    API_KEY = getPersonalAPIkey(user_id)
    args = context.args
    if (len(args) == 1) and (re.match(bssid_pattern, args[0]) is not None):
        answer = ''
        results = requests.get('{}/api/apiwps?key={}&bssid={}'.format(SERVICE_URL, API_KEY, args[0])).json()
        answer = CheckAPresponse(user_id, results)
        if answer == '':
            for result in results['data'][args[0].upper()]['scores']:
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
    if len(answer) > 3900:
        update.message.reply_text(answer[:3900] + '\nСписок слишком большой — смотрите полностью на {}/wpspin'.format(SERVICE_URL), parse_mode='Markdown')
    else:
        update.message.reply_text(answer, parse_mode='Markdown')


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("help", help))
dp.add_handler(CommandHandler("start", help))
dp.add_handler(CommandHandler("login", login, pass_args=True))
dp.add_handler(CommandHandler("logout", logout))
dp.add_handler(CommandHandler("wps", wps, pass_args=True))
dp.add_handler(CommandHandler("pw", pw, pass_args=True))
dp.add_handler(CommandHandler("pws", pws, pass_args=True))
dp.add_handler(MessageHandler(Filters.regex(bssid_pattern) & Filters.private, pw))
dp.add_handler(MessageHandler((Filters.text | Filters.command) & Filters.private, unknown))
dp.add_error_handler(error)
if IP == 'no':
    updater.start_polling(poll_interval=.5)
else:
    updater.start_webhook(listen='0.0.0.0', port=8443, url_path=TOKEN, key='private.key', cert='cert.pem', webhook_url=f'https://{IP}:8443/{TOKEN}')
