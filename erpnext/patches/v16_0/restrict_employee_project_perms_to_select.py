import frappe
from frappe.permissions import get_all_perms, get_doctypes_with_custom_docperms
from frappe.utils import cint

DOCTYPE = "Project"
ROLE = "Employee"
# Rights that expose a Project to a role that cannot read it.
PTYPES = ("print", "email", "export", "report", "share")


def execute():
	"""Keep Employee at select only on Project for sites that customised Project permissions."""
	if DOCTYPE not in get_doctypes_with_custom_docperms():
		return

	changed = False
	for rule in get_all_perms(ROLE):
		if rule.parent != DOCTYPE or cint(rule.permlevel) or cint(rule.read):
			continue
		frappe.db.set_value("Custom DocPerm", rule.name, dict.fromkeys(PTYPES, 0))
		changed = True

	if changed:
		frappe.clear_cache(doctype=DOCTYPE)
