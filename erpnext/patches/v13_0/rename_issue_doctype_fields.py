# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	if frappe.db.exists("DocType", "Issue"):
		issues = frappe.db.get_all(
			"Issue",
			fields=["name", "response_by_variance", "resolution_by_variance", "mins_to_first_response"],
			order_by="creation desc",
		)
		frappe.reload_doc("support", "doctype", "issue")

		# rename fields
		rename_map = {
			"agreement_fulfilled": "agreement_status",
			"mins_to_first_response": "first_response_time",
		}
		for old, new in rename_map.items():
			rename_field("Issue", old, new)

		# change fieldtype to duration
		count = 0
		for entry in issues:
			response_by_variance = convert_to_seconds(entry.response_by_variance, "Hours")
			resolution_by_variance = convert_to_seconds(entry.resolution_by_variance, "Hours")
			mins_to_first_response = convert_to_seconds(entry.mins_to_first_response, "Minutes")
			frappe.db.set_value(
				"Issue",
				entry.name,
				{
					"response_by_variance": response_by_variance,
					"resolution_by_variance": resolution_by_variance,
					"first_response_time": mins_to_first_response,
				},
				update_modified=False,
			)
			# commit after every 100 updates
			count += 1
			if count % 100 == 0:
				frappe.db.commit()

	if frappe.db.exists("DocType", "Opportunity"):
		opportunities = frappe.db.get_all(
			"Opportunity", fields=["name", "mins_to_first_response"], order_by="creation desc"
		)
		frappe.reload_doctype("Opportunity", force=True)
		rename_field("Opportunity", "mins_to_first_response", "first_response_time")

		# change fieldtype to duration
		frappe.reload_doc("crm", "doctype", "opportunity", force=True)
		count = 0
		for entry in opportunities:
			mins_to_first_response = convert_to_seconds(entry.mins_to_first_response, "Minutes")
			frappe.db.set_value(
				"Opportunity", entry.name, "first_response_time", mins_to_first_response, update_modified=False
			)
			# commit after every 100 updates
			count += 1
			if count % 100 == 0:
				frappe.db.commit()

	# renamed reports from "Minutes to First Response for Issues" to "First Response Time for Issues". Same for Opportunity
	for report in [
		"Minutes to First Response for Issues",
		"Minutes to First Response for Opportunity",
	]:
		if frappe.db.exists("Report", report):
			frappe.delete_doc("Report", report, ignore_permissions=True)


def convert_to_seconds(value, unit):
	seconds = 0
	if not value:
		return seconds
	if unit == "Hours":
		seconds = value * 3600
	if unit == "Minutes":
		seconds = value * 60
	return seconds
