# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	selling_price_list =  webnotes.conn.get_value("Selling Settings", None, "selling_price_list")
	if selling_price_list and not webnotes.conn.exists("Price List", selling_price_list):
		webnotes.conn.set_value("Selling Settings", None, "selling_price_list", None)
		
	buying_price_list =  webnotes.conn.get_value("Buying Settings", None, "buying_price_list")
	if buying_price_list and not webnotes.conn.exists("Price List", buying_price_list):
		webnotes.conn.set_value("Buying Settings", None, "buying_price_list", None)
	
	# reset property setters for series
	for name in ("Stock Settings", "Selling Settings", "Buying Settings", "HR Settings"):
		webnotes.reload_doc(name.split()[0], 'DocType', name)
		webnotes.bean(name, name).save()
