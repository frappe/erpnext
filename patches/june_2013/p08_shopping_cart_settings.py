# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("selling", "doctype", "shopping_cart_settings")
	
	# create two default territories, one for home country and one named Rest of the World
	from setup.page.setup_wizard.setup_wizard import create_territories
	create_territories()
	
	webnotes.conn.set_value("Shopping Cart Settings", None, "default_territory", "Rest of the World")
	