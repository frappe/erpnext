
# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doc('accounts', 'doctype', 'mode_of_payment')

	mode_of_payment_list = frappe.db.sql("""select name, default_account
		from `tabMode of Payment`""", as_dict=1)

	for d in mode_of_payment_list:
		if d.get("default_account"):
			parent_doc = frappe.get_doc("Mode of Payment", d.get("name"))

			parent_doc.set("mode_of_payment_details",
				[{"company": frappe.db.get_value("Account", d.get("default_account"), "company"),
				"default_account": d.get("default_account")}])
			parent_doc.save()
