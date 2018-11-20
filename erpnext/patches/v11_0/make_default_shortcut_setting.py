import frappe

def execute():
	frappe.reload_doc('setup', 'doctype', 'shortcut_settings')
	frappe.reload_doc('setup', 'doctype', 'shortcut_item')
	default_setting = frappe.get_doc(dict(
		doctype='Shortcut Settings',
		shortcut_items=[{
			'label': 'Social',
			'link': 'social/home'
		}, {
			'label': 'Marketplace',
			'link': 'marketplace/home'
		}, {
			'label': 'Explore',
			'link': 'modules'
		}]
	))
	default_setting.insert()