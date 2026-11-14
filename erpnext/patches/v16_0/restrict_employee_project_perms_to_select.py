import frappe
from frappe.permissions import get_doctypes_with_custom_docperms
from frappe.utils import cint

from erpnext.setup.install import get_role_rules

DOCTYPE = "Project"
ROLE = "Employee"
# Rights that expose a Project to a role that cannot read it.
PTYPES = ("print", "email", "export", "report", "share")


def execute():
	"""Keep Employee at select only on Project for sites that customised Project permissions."""
	if DOCTYPE not in get_doctypes_with_custom_docperms():
		return

	changed = False
	for rule in get_role_rules(DOCTYPE, ROLE):
		if cint(rule.permlevel) or cint(rule.read):
			continue
		frappe.db.set_value("Custom DocPerm", rule.name, dict.fromkeys(PTYPES, 0))
		changed = True

	if changed:
		frappe.clear_cache(doctype=DOCTYPE)
