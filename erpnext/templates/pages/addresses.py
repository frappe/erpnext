# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.shopping_cart.cart import get_address_docs

no_cache = 1
no_sitemap = 1

@frappe.whitelist()
def get_addresses():
	return get_address_docs()
