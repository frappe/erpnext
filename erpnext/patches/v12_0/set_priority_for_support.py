import frappe

def execute():
	frappe.reload_doc("support", "doctype", "issue_priority")

	priorities = frappe.get_meta("Issue").get_field("priority").options.split("\n")

	for priority in priorities:
		if not frappe.db.exists("Issue Priority", priority):
			frappe.get_doc({
				"doctype": "Issue Priority",
				"name": priority
			}).insert(ignore_permissions=True)

	frappe.reload_doc("support", "doctype", "issue")
	frappe.reload_doc("support", "doctype", "service_level")
	frappe.reload_doc("support", "doctype", "service_level_agreement")

	for issue in frappe.get_list("Issue", fields=["name", "priority"]):
		frappe.db.set_value("Issue", issue.name, "priority", issue.priority)

	for service_level in frappe.get_list("Service Level", fields=["name", "priority", "response_time", "response_time_period",
		"resolution_time", "resolution_time_period"]):

		doc = frappe.get_doc("Service Level", service_level.name)
		doc.append("priorities", {
			"priority": service_level.priority,
			"default_priority": 1,
			"response_time": service_level.response_time,
			"response_time_period": service_level.response_time_period,
			"resolution_time": service_level.resolution_time,
			"resolution_time_period": service_level.resolution_time_period
		})
		doc.save(ignore_permissions=True)

	for service_level_agreement in frappe.get_list("Service Level Agreement", fields=["name", "priority", "response_time", "response_time_period",
		"resolution_time", "resolution_time_period"]):

		doc = frappe.get_doc("Service Level Agreement", service_level_agreement.name)

		if doc.customer:
			doc.append_to = "Customer"
			doc.entity = doc.customer

		doc.append("priorities", {
			"priority": service_level_agreement.priority,
			"default_priority": 1,
			"response_time": service_level_agreement.response_time,
			"response_time_period": service_level_agreement.response_time_period,
			"resolution_time": service_level_agreement.resolution_time,
			"resolution_time_period": service_level_agreement.resolution_time_period
		})
		doc.save(ignore_permissions=True)