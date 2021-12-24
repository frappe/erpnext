# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.table_exists('Daily Work Summary Group'):
		frappe.reload_doc("hr", "doctype", "daily_work_summary_group")
		frappe.reload_doc("hr", "doctype", "daily_work_summary_group_user")

		# check if Daily Work Summary Settings Company table exists
		try:
			frappe.db.sql('DESC `tabDaily Work Summary Settings Company`')
		except Exception:
			return

		# get the previously saved settings
		previous_setting = get_previous_setting()
		if previous_setting["companies"]:
			for d in previous_setting["companies"]:
				users = frappe.get_list("Employee", dict(
					company=d.company, user_id=("!=", " ")), "user_id as user")
				if(len(users)):
					# create new group entry for each company entry
					new_group = frappe.get_doc(dict(doctype="Daily Work Summary Group",
						name="Daily Work Summary for " + d.company,
						users=users,
						send_emails_at=d.send_emails_at,
						subject=previous_setting["subject"],
						message=previous_setting["message"]))
					new_group.flags.ignore_permissions = True
					new_group.flags.ignore_validate = True
					new_group.insert(ignore_if_duplicate = True)

	frappe.delete_doc("DocType", "Daily Work Summary Settings")
	frappe.delete_doc("DocType", "Daily Work Summary Settings Company")


def get_previous_setting():
	obj = {}
	setting_data = frappe.db.sql(
		"select field, value from tabSingles where doctype='Daily Work Summary Settings'")
	for field, value in setting_data:
		obj[field] = value
	obj["companies"] = get_setting_companies()
	return obj

def get_setting_companies():
	return frappe.db.sql("select * from `tabDaily Work Summary Settings Company`", as_dict=True)
