# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("accounts", "doctype", "pos_setting")
	if "customer_account" in webnotes.conn.get_table_columns("POS Setting"):
		customer_account = webnotes.conn.sql("""select customer_account, name from `tabPOS Setting` 
			where ifnull(customer_account, '')!=''""")

		for cust_acc, pos_name in customer_account:
			customer = webnotes.conn.sql("""select master_name, account_name from `tabAccount` 
				where name=%s""", (cust_acc), as_dict=1)

			if not customer[0].master_name:
				customer_name = webnotes.conn.get_value('Customer', customer[0].account_name, 'name')
			else:
				customer_name = customer[0].master_name

			webnotes.conn.set_value('POS Setting', pos_name, 'customer', customer_name)
		
		webnotes.conn.sql_ddl("""alter table `tabPOS Setting` drop column `customer_account`""")
