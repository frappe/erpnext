import frappe


def get_context(context):
	context.no_cache = 1

	task = frappe.get_doc("Task", frappe.form_dict.task)
	task.check_permission()

	context.comments = frappe.get_all(
		"Comment",
		filters={"reference_doctype": "Task", "reference_name": task.name, "comment_type": "Comment"},
		fields=["content", "comment_email", "creation"],
	)

	context.doc = task
