# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.reload_doc("core", "doctype", "has_role")
	company = frappe.get_all("Company", filters={"country": "India"})

	if not company:
		frappe.db.sql(
			"""
			delete from
				`tabHas Role`
			where
				parenttype = 'Report' and parent in('GST Sales Register',
					'GST Purchase Register', 'GST Itemised Sales Register',
					'GST Itemised Purchase Register', 'Eway Bill')"""
		)
