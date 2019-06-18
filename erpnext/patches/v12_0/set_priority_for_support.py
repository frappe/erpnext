import frappe

def execute():
	frappe.reload_doc("support", "doctype", "issue_priority")
	frappe.reload_doc("support", "doctype", "service_level_priority")

	set_issue_priority()
	set_priority_for_issue()
	set_priorities_service_level()
	set_priorities_service_level_agreement()

def set_issue_priority():
	for priority in frappe.get_meta("Issue").get_field("priority").options.split("\n"):
		if not frappe.db.exists("Issue Priority", priority):
			frappe.get_doc({
				"doctype": "Issue Priority",
				"name": priority
			}).insert(ignore_permissions=True)

def set_priority_for_issue():
	issue_priority = frappe.get_list("Issue", fields=["name", "priority"])
	frappe.reload_doc("support", "doctype", "issue")

	for issue in issue_priority:
		frappe.db.set_value("Issue", issue.name, "priority", issue.priority)

def set_priorities_service_level():
	service_level_priorities = frappe.get_list("Service Level", fields=["name", "priority", "response_time", "response_time_period", "resolution_time", "resolution_time_period"])
	frappe.reload_doc("support", "doctype", "service_level")

	for service_level in service_level_priorities:
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

def set_priorities_service_level_agreement():
	service_level_agreement_priorities = frappe.get_list("Service Level Agreement", fields=["name", "priority", "response_time", "response_time_period", "resolution_time", "resolution_time_period"])
	frappe.reload_doc("support", "doctype", "service_level_agreement")

	for service_level_agreement in service_level_agreement_priorities:
		doc = frappe.get_doc("Service Level Agreement", service_level_agreement.name)

		if doc.customer:
			doc.apply_to = "Customer"
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