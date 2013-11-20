# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
import webnotes.defaults

def execute():
	# sesison expiry missing
	if not webnotes.defaults.get_global_default("session_expiry"):
		gd = webnotes.bean("Global Defaults", "Global Defaults")
		gd.doc.session_expiry = webnotes.conn.get_value('Control Panel', None, 'session_expiry') \
			or '06:00'
		gd.save()
		