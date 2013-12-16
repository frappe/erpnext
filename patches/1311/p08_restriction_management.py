# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	# add role "Restriction Manager"
	if not webnotes.conn.exists("Role", "Restriction Manager"):
		webnotes.bean({"doctype": "Role", "role_name": "Restriction Manager"}).insert()

	# reset Page perms
	from core.page.permission_manager.permission_manager import reset
	reset("Page")