import frappe
from frappe.utils import now_datetime


def execute():
	"""Returns of Components submitted before this did not use the order's supplier warehouse reservations."""
	frappe.db.set_default("reserved_components_return_cutoff", now_datetime())
