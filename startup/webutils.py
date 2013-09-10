# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import cint

def get_website_settings():
	return {
		"shopping_cart_enabled": cint(webnotes.conn.get_default("shopping_cart_enabled"))
	}