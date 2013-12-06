# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	doctype = webnotes.conn.sql("""select doctype from `tabSingles` 
		where doctype = 'Email Settings'""")
	if not doctype:
		email_settings = webnotes.bean("Email Settings", "Email Settings")
		email_settings.doc.send_print_in_body_and_attachment = 1
		email_settings.save()

	webnotes.conn.sql("""update `tabSingles` set value = 1 
		where doctype = 'Email Settings' and field = 'send_print_in_body_and_attachment' and 
		ifnull(value,'')=''""")