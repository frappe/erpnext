# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	from core.page.user_properties import user_properties
	for warehouse, profile in webnotes.conn.sql("""select parent, user from `tabWarehouse User`"""):
		user_properties.add(profile, "Warehouse", warehouse)
		
	webnotes.delete_doc("DocType", "Warehouse User")