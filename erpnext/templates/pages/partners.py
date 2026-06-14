# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe

page_title = "Partners"


def get_context(context):
	partners = frappe.get_all(
		"Sales Partner",
		filters={"show_in_website": 1},
		fields=["*"],
		order_by="name asc",
	)

	return {"partners": partners, "title": page_title}
