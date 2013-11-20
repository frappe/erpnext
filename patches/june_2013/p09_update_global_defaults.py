# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	from_global_defaults = {
		"credit_controller": "Accounts Settings",
		"acc_frozen_upto": "Accounts Settings",
		"bde_auth_role": "Accounts Settings",
		"auto_indent": "Stock Settings",
		"reorder_email_notify": "Stock Settings",
		"tolerance": "Stock Settings",
		"stock_frozen_upto": "Stock Settings",
		"stock_auth_role": "Stock Settings",
		"so_required": "Selling Settings",
		"dn_required": "Selling Settings",
		"po_required": "Selling Settings",
		"pr_required": "Selling Settings"
	}
	
	from_defaults = {
		"item_group": "Stock Settings",
		"item_naming_by": "Stock Settings",
		"stock_uom": "Stock Settings",
		"valuation_method": "Stock Settings",
		"allow_negative_stock": "Stock Settings",
		"cust_master_name": "Selling Settings",
		"customer_group": "Selling Settings",
		"territory": "Selling Settings",
		"price_list_name": "Selling Settings",
		"supplier_type": "Buying Settings",
		"supp_master_name": "Buying Settings",
		"maintain_same_rate": "Buying Settings"
	}

	for key in from_global_defaults:
		webnotes.conn.set_value(from_global_defaults[key], None, key, 
			webnotes.conn.get_value("Global Defaults", None, key))
			
	for key in from_defaults:
		webnotes.conn.set_value(from_defaults[key], None, key, 
			webnotes.conn.get_default(key))
		