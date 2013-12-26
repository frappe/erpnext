# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	webnotes.conn.sql("""update `tabCurrency` set fraction = 'Cent' where fraction = 'Cent[D]'""")