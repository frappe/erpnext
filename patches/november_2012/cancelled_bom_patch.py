# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	cancelled_boms = webnotes.conn.sql("""select name from `tabBOM`
		where docstatus = 2""")
	
	for bom in cancelled_boms:
		webnotes.conn.sql("""update `tabBOM` set is_default=0, is_active=0
			where name=%s""", (bom[0],))
		
		webnotes.conn.sql("""update `tabItem` set default_bom=null
			where default_bom=%s""", (bom[0],))
		
		