from __future__ import unicode_literals
import frappe
import json
from frappe.model.utils.rename_field import update_reports, rename_field, update_property_setters
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute():
	frappe.reload_doctype('Purchase Order Item')
	frappe.reload_doctype('Purchase Receipt Item')
	update_po_fields()
	update_prop_setters_reports_print_format_for_po()
	set_sales_order_field()
	rename_pr_fields()

def update_po_fields():
	for data in frappe.db.sql(""" select prevdoc_docname, prevdoc_detail_docname, name, prevdoc_doctype
		from `tabPurchase Order Item` where prevdoc_doctype is not null""", as_dict=True):
		if data.prevdoc_doctype == 'Material Request':
			frappe.db.set_value("Purchase Order Item", data.name, "material_request", data.prevdoc_docname, update_modified=False)
			frappe.db.set_value("Purchase Order Item", data.name, "material_request_item", data.prevdoc_detail_docname, update_modified=False)
		elif data.prevdoc_doctype == 'Sales Order':
			frappe.db.set_value("Purchase Order Item", data.name, "sales_order", data.prevdoc_docname, update_modified=False)
			frappe.db.set_value("Purchase Order Item", data.name, "sales_order_item", data.prevdoc_detail_docname, update_modified=False)

def get_columns():
	return {
		'prevdoc_docname': 'material_request',
		'prevdoc_detail_docname': 'material_request_item'
	}

def update_prop_setters_reports_print_format_for_po():
	for key, val in get_columns().items():
		update_property_setters('Purchase Order Item', key, val)
		update_reports('Purchase Order Item', key, val)
		update_print_format_for_po(key, val, 'Purchase Order')

def update_print_format_for_po(old_fieldname, new_fieldname, doc_type):
	column_mapper = get_columns()

	for data in frappe.db.sql(""" select name, format_data from `tabPrint Format` where
		format_data like %(old_fieldname)s and doc_type = %(doc_type)s""", 
		{'old_fieldname': '%%%s%%'%(old_fieldname), 'doc_type': doc_type}, as_dict=True):

		update_print_format_fields(old_fieldname, new_fieldname, data)

def update_print_format_fields(old_fieldname, new_fieldname, args):
	report_dict = json.loads(args.format_data)
	update = False

	for col in report_dict:
		if col.get('fieldname') and col.get('fieldname') == old_fieldname:
			col['fieldname'] = new_fieldname
			update = True

		if col.get('visible_columns'):
			for key in col.get('visible_columns'):
				if key.get('fieldname') == old_fieldname:
					key['fieldname'] = new_fieldname
					update = True

	if update:
		val = json.dumps(report_dict)
		frappe.db.sql("""update `tabPrint Format` set `format_data`=%s where name=%s""", (val, args.name))
		
def set_sales_order_field():
	for data in frappe.db.sql("""select doc_type, field_name, property, value, property_type 
		from `tabProperty Setter` where doc_type = 'Purchase Order Item' 
		and field_name in('material_request', 'material_request_item')""", as_dict=True):
		if data.field_name == 'material_request':
			make_property_setter(data.doc_type, 'sales_order', data.property, data.value, data.property_type)
		else:
			make_property_setter(data.doc_type, 'sales_order_item', data.property, data.value, data.property_type)

def rename_pr_fields():
	rename_field("Purchase Receipt Item", "prevdoc_docname", "purchase_order")
	rename_field("Purchase Receipt Item", "prevdoc_detail_docname", "purchase_order_item")
