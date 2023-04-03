# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	# add holiday list and employee group fields in SLA
	# change response and resolution time in priorities child table
	if frappe.db.exists("DocType", "Service Level Agreement"):
		sla_details = frappe.db.get_all("Service Level Agreement", fields=["name", "service_level"])
		priorities = frappe.db.get_all(
			"Service Level Priority",
			fields=["*"],
			filters={"parenttype": ("in", ["Service Level Agreement", "Service Level"])},
		)

		frappe.reload_doc("support", "doctype", "service_level_agreement")
		frappe.reload_doc("support", "doctype", "pause_sla_on_status")
		frappe.reload_doc("support", "doctype", "service_level_priority")
		frappe.reload_doc("support", "doctype", "service_day")

		for entry in sla_details:
			values = frappe.db.get_value(
				"Service Level", entry.service_level, ["holiday_list", "employee_group"]
			)
			if values:
				holiday_list = values[0]
				employee_group = values[1]
				frappe.db.set_value(
					"Service Level Agreement",
					entry.name,
					{"holiday_list": holiday_list, "employee_group": employee_group},
				)

		priority_dict = {}

		for priority in priorities:
			if priority.parenttype == "Service Level Agreement":
				response_time = convert_to_seconds(priority.response_time, priority.response_time_period)
				resolution_time = convert_to_seconds(priority.resolution_time, priority.resolution_time_period)
				frappe.db.set_value(
					"Service Level Priority",
					priority.name,
					{"response_time": response_time, "resolution_time": resolution_time},
				)
			if priority.parenttype == "Service Level":
				if not priority.parent in priority_dict:
					priority_dict[priority.parent] = []
				priority_dict[priority.parent].append(priority)

		# copy Service Levels to Service Level Agreements
		sl = [entry.service_level for entry in sla_details]
		if frappe.db.exists("DocType", "Service Level"):
			service_levels = frappe.db.get_all(
				"Service Level", filters={"service_level": ("not in", sl)}, fields=["*"]
			)
			for entry in service_levels:
				sla = frappe.new_doc("Service Level Agreement")
				sla.service_level = entry.service_level
				sla.holiday_list = entry.holiday_list
				sla.employee_group = entry.employee_group
				sla.flags.ignore_validate = True
				sla = sla.insert(ignore_mandatory=True)

				frappe.db.sql(
					"""
					UPDATE
						`tabService Day`
					SET
						parent = %(new_parent)s , parentfield = 'support_and_resolution', parenttype = 'Service Level Agreement'
					WHERE
						parent = %(old_parent)s
				""",
					{"new_parent": sla.name, "old_parent": entry.name},
					as_dict=1,
				)

				priority_list = priority_dict.get(entry.name)
				if priority_list:
					sla = frappe.get_doc("Service Level Agreement", sla.name)
					for priority in priority_list:
						row = sla.append(
							"priorities",
							{
								"priority": priority.priority,
								"default_priority": priority.default_priority,
								"response_time": convert_to_seconds(priority.response_time, priority.response_time_period),
								"resolution_time": convert_to_seconds(
									priority.resolution_time, priority.resolution_time_period
								),
							},
						)
						row.db_update()
					sla.db_update()

	frappe.delete_doc_if_exists("DocType", "Service Level")


def convert_to_seconds(value, unit):
	seconds = 0
	if unit == "Hour":
		seconds = value * 3600
	if unit == "Day":
		seconds = value * 3600 * 24
	if unit == "Week":
		seconds = value * 3600 * 24 * 7
	return seconds
