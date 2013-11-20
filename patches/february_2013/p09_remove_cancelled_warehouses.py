# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	for w in webnotes.conn.sql("""select name from `tabWarehouse` where docstatus=2"""):
		try:
			webnotes.delete_doc("Warehouse", w[0])
		except webnotes.ValidationError:
			pass
		