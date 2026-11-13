import frappe
from frappe.permissions import get_doctypes_with_custom_docperms

from erpnext.patches.v16_0.mirror_release_perms_to_custom_docperm import mirror_role

# HR User needs select on these to save a Timesheet with a project or task
DOCTYPES = ("Task", "Project")


def execute():
	customised = get_doctypes_with_custom_docperms()
	for doctype in DOCTYPES:
		if doctype not in customised:
			continue
		if mirror_role(doctype, "HR User", ("select",)):
			frappe.clear_cache(doctype=doctype)
