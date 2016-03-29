# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def get_context(context):
	context.no_cache = 1
	context.doc = frappe.get_doc(frappe.form_dict.doctype, frappe.form_dict.name)
	context.parents = frappe.form_dict.parents
	context.doc.supplier = get_supplier()
	unauthrized_user(context.doc.supplier)
	context["title"] = frappe.form_dict.name

def unauthrized_user(supplier):
	status = check_supplier_has_docname_access(supplier)
	if status == False:
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

def get_supplier():
	from erpnext.shopping_cart.utils import check_customer_or_supplier
	key, parties = check_customer_or_supplier()
	return parties[0] if key == 'Supplier' else ''

def check_supplier_has_docname_access(supplier):
	status = True
	if frappe.form_dict.name not in frappe.db.sql_list("""select parent from `tabRFQ Supplier`
		where supplier = '{supplier}'""".format(supplier=supplier)):
		status = False
	return status
