# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.model import no_value_fields

def execute():
	for dt in webnotes.conn.sql_list("""select name from `tabDocType` where custom=1"""):
		dtbean = webnotes.bean("DocType", dt)
		
		if any((df.in_list_view for df in dtbean.doclist.get({"doctype": "DocField", "parent": dt}))):
			continue
		
		i = 0
		for df in dtbean.doclist.get({"doctype": "DocField", "parent": dt}):
			if i > 5:
				break
			
			if df.fieldtype not in no_value_fields:
				df.in_list_view = 1
				i += 1
				
		if i > 0:
			dtbean.save()