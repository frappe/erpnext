# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
def execute():
	webnotes.conn.sql("""update `tabDocPerm` set cancel=1
		where parent='Profile' and role in ('System Manager', 'Administrator') and permlevel=0""")