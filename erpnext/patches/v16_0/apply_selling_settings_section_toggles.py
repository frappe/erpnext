import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from erpnext.selling.doctype.selling_settings.selling_settings import COMMISSION_SECTIONS, UTM_DOCTYPES


def execute():
	settings = frappe.get_single("Selling Settings")

	for doctype, sections in COMMISSION_SECTIONS.items():
		for section in sections:
			_backfill_hidden(doctype, section, not settings.enable_tracking_sales_commissions)

	for doctype in UTM_DOCTYPES:
		if frappe.get_meta(doctype).has_field("utm_analytics_section"):
			_backfill_hidden(doctype, "utm_analytics_section", not settings.enable_utm)


def _backfill_hidden(doctype, fieldname, hidden):
	# only fill the missing default; never clobber a value set manually or by the on-change toggle
	if frappe.db.exists(
		"Property Setter", {"doc_type": doctype, "field_name": fieldname, "property": "hidden"}
	):
		return
	make_property_setter(doctype, fieldname, "hidden", hidden, "Check", validate_fields_for_doctype=False)
