#!/usr/bin/python3
# -*- coding: utf-8 -*-
import requests
import re
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging

TOKEN = ''
try: TOKEN = open('apikey.txt').read()
except:
    TOKEN = input('telegram token: ')
    outf = open('apikey.txt', 'w')
    outf.write(TOKEN)
    outf.close()

IP = ''
try: IP = open('IP.txt').read()
except:
    IP = input('IP for webhook: ')
    outf = open('IP.txt', 'w')
    outf.write(IP)
    outf.close()

API_KEY = 'MHgONUzVP0KK3FGfV0HVEREHLsS6odc3'
bssid_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def text(bot, update): update.message.reply_text('Команда не найдена! Отправьте /help для получения информации по доступным командам')

def help(bot, update):
    update.message.reply_text(f'''3wifi.stascorp.com бот!
/pw bssid и/или essid - поиск по мак адресу или имени точки (пример: /pw FF:FF:FF:FF:FF:FF или /pw netgear или /pw FF:FF:FF:FF:FF:FF VILTEL)
/wps bssid - поиск wps пина по мак адресу (пример: /wps FF:FF:FF:FF:FF:FF)''')

def pw(bot, update):
    answer='Забыли ввести bssid или essid! Поиск по bssid и/или essid выполняется так: /pw bssid/essid (пример: /pw FF:FF:FF:FF:FF:FF VILTEL или /pw FF:FF:FF:FF:FF:FF или /pw netgear)'
    tmp = update.message.text.split()
    if len(tmp) == 2:
        if re.match(bssid_pattern, tmp[1]) != None:
            results = requests.get(f'https://3wifi.stascorp.com/api/apiquery?key={API_KEY}&bssid={tmp[1]}').json()
            if len(results['data']) == 0: answer='Нет результатов :('
            else:
                answer=''
                values = results['data'][f'{tmp[1]}'.upper()]
                for value in values:
                    answer+=f"""ESSID: `{value['essid']}`
BSSID: `{value['bssid']}`
Password: `{value['key']}`
WPS pin: `{value['wps']}`
Time: {value['time']}
- - - - -
"""
        else:
            results = requests.get(f'https://3wifi.stascorp.com/api/apiquery?key={API_KEY}&bssid=*&essid={tmp[1]}').json()
            if len(results['data']) == 0: answer='Нет результатов :('
            if len(results['data']) == 1:
                values = results['data'][f'*|{tmp[1]}']
                for value in values:
                    answer=f"""ESSID: `{value['essid']}`
BSSID: `{value['bssid']}`
Password: `{value['key']}`
WPS pin: `{value['wps']}`
Time: {value['time']}
- - - - -
"""
    elif len(tmp) == 3:
        if re.match(bssid_pattern, tmp[1]) != None:
            results = requests.get(f'https://3wifi.stascorp.com/api/apiquery?key={API_KEY}&bssid={tmp[1]}&essid={tmp[2]}').json()    
            if len(results['data']) == 0: answer='Нет результатов :('
            if len(results['data']) == 1:
                values = results['data'][f'{tmp[1].upper()}|{tmp[2]}'][0]
                answer=f"""ESSID: `{values['essid']}`
BSSID: `{values['bssid']}`
Password: `{values['key']}`
WPS pin: `{values['wps']}`
Time: {values['time']}
"""
    else: answer='Поиск по bssid и essid выполняется так: /pw bssid essid (пример: /pw FF:FF:FF:FF:FF:FF VILTEL)'
    update.message.reply_text(answer, parse_mode='Markdown')

def wps(bot, update):
    answer='Поиск wps пин кодов выполняется так: /wps bssid (пример: /wps FF:FF:FF:FF:FF:FF)'
    tmp = update.message.text.split()
    if len(tmp) == 2:
        if re.match(bssid_pattern, tmp[1]) != None:
            results = requests.get('https://3wifi.stascorp.com/api/apiwps?key={}&bssid={}'.format(API_KEY, tmp[1])).json()
            if len(results['data']) > 0:
                answer=''
                for result in results['data'][tmp[1].upper()]['scores']:
                    answer+=f"""Name: `{result['name']}`
Pin: `{result['value']}`
Score: {result['score']}
"""
            else: answer = 'Нет результатов :('
    update.message.reply_text(answer, parse_mode='Markdown')

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))



updater = Updater(TOKEN)
updater.start_webhook(listen='0.0.0.0', port=8443, url_path=TOKEN, key='private.key', cert='cert.pem', webhook_url=f'https://{IP}:8443/{TOKEN}')
dp = updater.dispatcher
dp.add_handler(CommandHandler("help", help))
dp.add_handler(CommandHandler("start", help))
dp.add_handler(CommandHandler("wps", wps))
dp.add_handler(CommandHandler("pw", pw))
dp.add_handler(MessageHandler(Filters.text, text))
dp.add_error_handler(error)
#updater.start_polling(poll_interval=.5)
