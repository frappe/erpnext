import frappe

def execute():
	frappe.reload_doc("quality_management", "doctype", "quality feedback")
	frappe.reload_doc("quality_management", "doctype", "quality feedback template")

	for template in frappe.get_list("Customer Feedback Template"):
		template = frappe.get_doc("Customer Feedback Template", template.name)

		quality_template = frappe.get_doc({
			"doctype": "Quality Feedback Template",
			'template': template.template,
		})

		for parameter in template.feedback_parameter:
			quality_template.append("parameters", {
				"parameter": : parameter.parameter
			})

		template.insert(ignore_permissions=True)

	for feedback in frappe.get_list("Customer Feedback"):
		feedback = frappe.get_doc("Customer Feedback", feedback.name)

		quality_feedback = frappe.get_doc({
			"doctype": "Quality Feedback",
			"document_type": "Customer",
			"document_name": feedback.customer,
			'template': feedback.template,
			"date": frappe.utils.getdate(),
		})

		for parameter in feedback.feedback:
			quality_template.append("parameters", {
				"parameter": : parameter.parameter
				"rating": parameter.rating,
				"feedback": parameter.qualitative_feedback
			})

		quality_feedback.insert(ignore_permissions=True)