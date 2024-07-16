import frappe
def project_query(user):
	# Get the current user's email
	user_email = user

	# Check if the user has admin privileges
	if "System Manager" in frappe.get_roles(user_email):
		# Return a condition that includes all projects
		return "1 = 1"

	# Query to get project names from tabProjectUser where email matches the current user's email
	project_names = frappe.db.sql("""
		SELECT parent
		FROM `tabProject User`
		WHERE email = %s
	""", (user_email,), as_dict=True)

	# Extract project names from the query result
	project_names = [project['parent'] for project in project_names]

	# Construct the SQL query to filter tabProject using the fetched project names
	if project_names:
		project_names_str = "', '".join(project_names)
		return f"(`tabProject`.name IN ('{project_names_str}'))"
	else:
		return "1 = 0"  # No projects found for the user, return a condition that results in no rows
