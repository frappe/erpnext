# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes, json
import webnotes.utils

def execute():
	modules = webnotes.get_config().modules
	
	ml = json.loads(webnotes.conn.get_global("hidden_modules") or "[]")
	
	if len(ml) == len(modules.keys()):
		webnotes.conn.set_global("hidden_modules", json.dumps([]))