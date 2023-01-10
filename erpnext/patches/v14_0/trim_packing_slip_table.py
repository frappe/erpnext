from frappe.model.meta import trim_tables


def execute():
	trim_tables('Packing Slip')
	trim_tables('Packing Slip Item')
