import frappe
from frappe import _
from frappe.utils import flt


def update_itemised_tax_data(doc):
	if not doc.items:
		return

	meta = frappe.get_meta(doc.items[0].doctype)
	if not meta.has_field("tax_rate"):
		return


def validate_returns(doc, method):
	country = frappe.get_cached_value("Company", doc.company, "country")
	if country != "Iraq":
		return
