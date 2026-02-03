from frappe.utils.install import add_link_field_formatters

from erpnext.setup.install import LINK_FIELD_DATA


def execute():
	add_link_field_formatters(LINK_FIELD_DATA)
