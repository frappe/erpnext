import frappe

def execute():
	frappe.db.sql("""DELETE
		FROM `tabDesktop Icon`
		WHERE
			`module_name` in ('Project', 'Projects') AND
			`standard`=1 AND
			`app`='erpnext'
	""")

	desktop_icon = frappe.get_doc({
		'doctype': 'Desktop Icon',
		'idx': 5,
		'standard': 1,
		'app': 'erpnext',
		'owner': 'Administrator',
		'module_name': 'Projects',
		'color': '#8e44ad',
		'icon': 'octicon octicon-rocket',
		'type': 'module'
	})

	desktop_icon.save()
