def execute():
	frappe.reload_doctype("Web Form Field")
	import erpnext.setup.install
	erpnext.setup.install.add_web_forms()
