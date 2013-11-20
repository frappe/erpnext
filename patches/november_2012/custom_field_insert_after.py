# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	import re
	regex = re.compile("\s-\s[\d\.]*")
	
	for name, insert_after in webnotes.conn.sql("""select name, insert_after
			from `tabCustom Field`"""):
		if insert_after:
			new_insert_after = regex.sub("", insert_after)
			webnotes.conn.set_value("Custom Field", name, "insert_after", new_insert_after)
		