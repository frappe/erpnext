import frappe
from frappe.permissions import get_doctypes_with_custom_docperms
from frappe.utils import cint

from erpnext.patches.v16_0.remove_all_role_from_payment_terms_template import remove_rule
from erpnext.setup.install import get_role_rules

DOCTYPE = "Import Supplier Invoice"


def execute():
	if DOCTYPE not in get_doctypes_with_custom_docperms():
		return
	removed = False
	for rule in get_role_rules(DOCTYPE, "All"):
		if not cint(rule.permlevel) and remove_rule(DOCTYPE, rule.name):
			removed = True
	if removed:
		frappe.clear_cache(doctype=DOCTYPE)
