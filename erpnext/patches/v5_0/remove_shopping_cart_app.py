# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	from frappe.installer import remove_from_installed_apps
	remove_from_installed_apps("shopping_cart")
