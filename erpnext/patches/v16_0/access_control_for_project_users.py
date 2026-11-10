import frappe


def execute():
	Project = frappe.qb.DocType("Project")
	ProjectUser = frappe.qb.DocType("Project User")

	query = (
		frappe.qb.from_(Project)
		.join(ProjectUser)
		.on(Project.name == ProjectUser.parent)
		.select(Project.name, ProjectUser.user)
		.where(Project.status != "Cancelled")  # Not considering cancelled Projects.
	)

	proj_users = query.run(as_dict=1)

	project_mapped_users = get_project_mapped_users(proj_users)

	for d in proj_users:
		if d.user in project_mapped_users[d.name]:
			continue

		frappe.share.add_docshare("Project", d.name, user=d.user)


def get_project_mapped_users(proj_users):
	projects = set([d.name for d in proj_users])
	project_mapped_users = {}

	for d in projects:
		project_mapped_users[d] = [d.user for d in frappe.share.get_users("Project", d)]

	return project_mapped_users
