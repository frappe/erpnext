import webnotes

def execute():
	from_global_defaults = {
		"credit_controller": "Accounts Settings",
		"auto_inventory_accounting": "Accounts Settings",
		"acc_frozen_upto": "Accounts Settings",
		"bde_auth_role": "Accounts Settings",
		"auto_indent": "Stock Settings",
		"reorder_email_notify": "Stock Settings",
		"tolerance": "Stock Settings",
		"stock_frozen_upto": "Stock Settings",
		"stock_auth_role": "Stock Settings"
	}
	
	from_defaults = {
		"item_group": "Stock Settings",
		"item_naming_by": "Stock Settings",
		"stock_uom": "Stock Settings",
		"valuation_method": "Stock Settings",
		"allow_negative_stock": "Stock Settings"
	}

	for key in from_global_defaults:
		webnotes.conn.set_value(from_global_defaults[key], None, key, 
			webnotes.conn.get_value("Global Defaults", None, key))
			
	for key in from_defaults:
		webnotes.conn.set_value(from_defaults[key], None, key, 
			webnotes.conn.get_default(key))
		