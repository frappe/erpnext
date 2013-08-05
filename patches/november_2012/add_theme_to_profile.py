# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.clear_perms("Profile")
	webnotes.reload_doc("core", "doctype", "profile")
	webnotes.conn.sql("""delete from `tabDefaultValue` where defkey='theme'""")
	webnotes.delete_doc("Page", "profile-settings")
	return

	for name in webnotes.conn.sql("""select name from tabProfile"""):
		theme = webnotes.conn.get_default("theme", name[0])
		if theme:
			webnotes.conn.set_value("Profile", name[0], "theme", theme)
			
