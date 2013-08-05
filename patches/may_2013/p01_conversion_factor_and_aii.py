# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import cint
from accounts.utils import create_stock_in_hand_jv

def execute():
	webnotes.conn.auto_commit_on_many_writes = True
	
	aii_enabled = cint(webnotes.conn.get_value("Global Defaults", None, 
		"auto_inventory_accounting"))
	
	if aii_enabled:
		create_stock_in_hand_jv(reverse = True)
	
	webnotes.conn.sql("""update `tabPurchase Invoice Item` pi_item 
		set conversion_factor = (select ifnull(if(conversion_factor=0, 1, conversion_factor), 1) 
			from `tabUOM Conversion Detail` 
			where parent = pi_item.item_code and uom = pi_item.uom limit 1
		)
		where ifnull(conversion_factor, 0)=0""")
	
	if aii_enabled:
		create_stock_in_hand_jv()
	
	webnotes.conn.auto_commit_on_many_writes = False
	
	