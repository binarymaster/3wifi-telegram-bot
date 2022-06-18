import json

with open('config.json', 'r', encoding = 'utf-8') as conf:
	c = json.load(conf)

with open('_config.json', 'r', encoding = 'utf-8') as conf:
	json.dump(c, conf, indent = 4)

n = c.pop('3wifi_apikey')
c['key'] = n
c['mayday'] =  "0"
c['codes'] = []
c['acodes'] = []

with open('config.json', 'w', encoding = 'utf-8') as conf:
	json.dump(c, conf, indent = 4)

with open('userkeys.json', 'r', encoding = 'utf-8') as users:
	u = json.load(users)

new = {}
for e in u:
	new[e] = {'key': u[e], 'code': ' ', 'acode': ' ', 'language': 'ru'} 

with open('users.json', 'w', encoding = 'utf-8') as users:
	json.dump(new, users, indent = 4)
