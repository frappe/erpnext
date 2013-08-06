# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("""\
		update `tabDocPerm` set `match`=NULL
		where parent='Event' and role='All' and permlevel=0""")