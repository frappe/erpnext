# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import frappe

def execute():
	frappe.reload_doc('crm', 'doctype', 'lead')
	frappe.reload_doc('crm', 'doctype', 'opportunity')

	add_crm_to_user_desktop_items()

def add_crm_to_user_desktop_items():
	key = "_user_desktop_items"
	for user in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}):
		user = user.name
		user_desktop_items = frappe.db.get_defaults(key, parent=user)
		if user_desktop_items:
			user_desktop_items = json.loads(user_desktop_items)
			if "CRM" not in user_desktop_items:
				user_desktop_items.append("CRM")
				frappe.db.set_default(key, json.dumps(user_desktop_items), parent=user)

