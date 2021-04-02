from __future__ import unicode_literals
import frappe
from frappe.model.rename_doc import rename_doc
from frappe.model.utils.rename_field import rename_field
from frappe import _
from frappe.utils.nestedset import rebuild_tree

def execute():
	if frappe.db.table_exists("Supplier Group"):
		frappe.reload_doc('setup', 'doctype', 'supplier_group')
	elif frappe.db.table_exists("Supplier Type"):
		rename_doc("DocType", "Supplier Type", "Supplier Group", force=True)
		frappe.reload_doc('setup', 'doctype', 'supplier_group')
		frappe.reload_doc("accounts", "doctype", "pricing_rule")
		frappe.reload_doc("accounts", "doctype", "tax_rule")
		frappe.reload_doc("buying", "doctype", "buying_settings")
		frappe.reload_doc("buying", "doctype", "supplier")
		rename_field("Supplier Group", "supplier_type", "supplier_group_name")
		rename_field("Supplier", "supplier_type", "supplier_group")
		rename_field("Buying Settings", "supplier_type", "supplier_group")
		rename_field("Pricing Rule", "supplier_type", "supplier_group")
		rename_field("Tax Rule", "supplier_type", "supplier_group")

	build_tree()

def build_tree():
	frappe.db.sql("""update `tabSupplier Group` set parent_supplier_group = '{0}'
		where is_group = 0""".format(_('All Supplier Groups')))

	if not frappe.db.exists("Supplier Group", _('All Supplier Groups')):
		frappe.get_doc({
			'doctype': 'Supplier Group',
			'supplier_group_name': _('All Supplier Groups'),
			'is_group': 1,
			'parent_supplier_group': ''
		}).insert(ignore_permissions=True)

	rebuild_tree("Supplier Group", "parent_supplier_group")
