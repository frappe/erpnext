# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	pos_view_users = webnotes.conn.sql_list("""select user from `tabPOS Setting`""")
	for user in pos_view_users:
		if user:
			webnotes.defaults.set_user_default("is_pos", 1, user)
		else:
			webnotes.defaults.set_global_default("is_pos", 1)