# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
def execute():
	webnotes.reload_doc("Setup", "DocType", "Global Defaults")
	
	if webnotes.conn.exists({"doctype": "Item", "email_notify": 1}):
		webnotes.conn.set_value("Global Defaults", None, "reorder_email_notify", 1)