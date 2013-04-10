import webnotes, json
import webnotes.utils

def execute():
	modules = webnotes.get_config().modules
	
	ml = json.loads(webnotes.conn.get_global("modules_list") or "[]")
	
	if ml:
		webnotes.conn.set_global("hidden_modules", 
			json.dumps(list(set(modules.keys()).difference(set(ml)))))
	