# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	webnotes.conn.sql("""update `tabBin` 
		set projected_qty = ifnull(actual_qty, 0) + ifnull(indented_qty, 0) + 
			ifnull(ordered_qty, 0) + ifnull(planned_qty, 0) - ifnull(reserved_qty, 0)""")