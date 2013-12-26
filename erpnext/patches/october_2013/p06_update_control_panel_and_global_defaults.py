# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("setup", "doctype", "global_defaults")

	country = webnotes.conn.sql("""select value from `tabSingles` where 
		field='country' and doctype='Control Panel'""")
	time_zone = webnotes.conn.sql("""select value from `tabSingles` where 
		field='timezone' and doctype='Control Panel'""")

	try:
		gb_bean = webnotes.bean("Global Defaults")
		gb_bean.doc.country = country and country[0][0] or None
		gb_bean.doc.time_zone = time_zone and time_zone[0][0] or None
		gb_bean.save()
	except:
		pass