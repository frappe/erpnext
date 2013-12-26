# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

def execute():
	import webnotes
	if not webnotes.conn.sql("""show index from `tabSingles` 
		where Key_name="singles_doctype_field_index" """):
		webnotes.conn.commit()
		webnotes.conn.sql("""alter table `tabSingles` 
			add index singles_doctype_field_index(`doctype`, `field`)""")