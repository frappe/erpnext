# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	for price_list_name in webnotes.conn.sql_list("""select name from `tabPrice List` 
		where ifnull(currency, '')=''"""):
			res = webnotes.conn.sql("""select distinct ref_currency from `tabItem Price`
				where price_list_name=%s""", price_list_name)
			if res and len(res)==1 and res[0][0]:
				webnotes.conn.set_value("Price List", price_list_name, "currency", res[0][0])
