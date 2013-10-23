# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("setup", "doctype", "global_defaults")

	country = webnotes.conn.sql("""select value from `tabSingles` where 
		field ='country' and doctype='Control Panel'""")
	time_zone = webnotes.conn.sql("""select value from `tabSingles` where 
		field ='timezone' and doctype='Control Panel'""")

	cp_bean = webnotes.bean("Control Panel")
	cp_bean.time_zone = time_zone
	cp_bean.save()

	gb_bean = webnotes.bean("Global Defaults")
	gb_bean.country = country
	gb_bean.time_zone = time_zone
	gb_bean.save()