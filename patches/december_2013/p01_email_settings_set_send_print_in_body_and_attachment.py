# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.conn.sql("""update `tabSingles` set value = 1 
		where doctype = 'Email Settings' and field = 'send_print_in_body_and_attachment' and 
		ifnull(value,'')=''""")