# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	webnotes.conn.sql("""drop table if exists `tabDocType Mapper`""")
	webnotes.conn.sql("""drop table if exists `tabTable Mapper Detail`""")
	webnotes.conn.sql("""drop table if exists `tabField Mapper Detail`""")
	webnotes.delete_doc("DocType", "DocType Mapper")
	webnotes.delete_doc("DocType", "Table Mapper Detail")
	webnotes.delete_doc("DocType", "Field Mapper Detail")	