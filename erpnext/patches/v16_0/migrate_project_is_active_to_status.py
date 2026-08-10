import frappe


def execute():
	"""
	Migrate Project is_active field to status field.
	Sets status = 'Disabled' for Projects where is_active = 'No' AND status is 'Open' or 'On hold'
	"""
	# Check if the column exists before migration
	if not frappe.db.has_column("Project", "is_active"):
		return

	project = frappe.qb.DocType("Project")

	(
		frappe.qb.update(project)
		.set(project.status, "Disabled")
		.where(project.is_active == "No")
		.where((project.status == "Open") | (project.status == "On hold"))
		.run()
	)
