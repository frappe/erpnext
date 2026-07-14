import frappe


def execute():
	Project = frappe.qb.DocType("Project")
	ProjectUser = frappe.qb.DocType("Project User")

	query = (
		frappe.qb.from_(Project)
		.join(ProjectUser)
		.on(Project.name == ProjectUser.parent)
		.select(Project.name, ProjectUser.user)
	)

	proj_user = query.run(as_dict=1)

	for d in proj_user:
		if frappe.has_permission("Project", doc=d.name, user=d.user):
			continue

		frappe.share.add_docshare("Project", d.name, user=d.user)
