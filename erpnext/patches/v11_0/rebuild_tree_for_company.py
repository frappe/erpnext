from __future__ import unicode_literals

import frappe
from frappe.utils.nestedset import rebuild_tree


def execute():
	frappe.reload_doc("setup", "doctype", "company")
	rebuild_tree('Company', 'parent_company')
