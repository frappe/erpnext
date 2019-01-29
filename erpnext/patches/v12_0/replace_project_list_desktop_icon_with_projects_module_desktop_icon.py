import frappe

def execute():
	projects_icons = frappe.get_all('Desktop Icon', filters={
		'module_name': ['in', ('Project', 'Projects')],
	})

	fields_to_update = {
		'module_name': 'Projects',
		'color': '#8e44ad',
		'icon': 'octicon octicon-rocket',
		'type': 'module',
		'link': ''
	}

	for icon in projects_icons:
		icon_doc = frappe.get_doc('Desktop Icon', icon.name)
		icon_doc.update(fields_to_update)
		try:
			icon_doc.save()
		except frappe.exceptions.UniqueValidationError:
			# delete duplicate icon
			icon_doc.delete()
