# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("delete from `tabCustomize Form Field`")
	webnotes.conn.sql("""delete from `tabSingles`
		where doctype='Customize Form'""")