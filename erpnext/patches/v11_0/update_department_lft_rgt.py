import frappe
from frappe import _
from frappe.utils.nestedset import rebuild_tree


def execute():
	"""assign lft and rgt appropriately"""
	frappe.reload_doc("setup", "doctype", "department")
	if not frappe.db.exists("Department", _("All Departments")):
		frappe.get_doc(
			{"doctype": "Department", "department_name": _("All Departments"), "is_group": 1}
		).insert(ignore_permissions=True, ignore_mandatory=True)

	frappe.db.sql(
		"""update `tabDepartment` set parent_department = '{}'
		where is_group = 0""".format(_("All Departments"))
	)

	rebuild_tree("Department", "parent_department")
