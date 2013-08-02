# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

# do not run this patch
from __future__ import unicode_literals
field_list = [
['Contact', 'notes'],
['Contact', 'birthday'],
['Contact', 'anniversary'],
['Customer', 'state_tax_type'],
['Customer', 'tin_no'],
['Customer', 'excise_registration_number'],
['Customer', 'customer_discount_details'],
['Customer', 'notes'],
['Customer', 'follow_up_section'],
['Customer', 'follow_up'],
['Delivery Note', 'shipping_contact_no'],
['Delivery Note', 'shipping_tin_no'],
['Delivery Note', 'shipping_excise_no'],
['Delivery Note', 'tin_no'],
['Delivery Note', 'excise_no'],
['Delivery Note Detail', 'cetsh_number'],
['Item', 'base_material'],
['Item', 'tool_type'],
['Item', 'no_of_flutes'],
['Item', 'special_treatment'],
['Item', 'length'],
['Item', 'width'],
['Item', 'height_dia'],
['Item', 'pl_item'],
['Item', 'cetsh_number'],
['Item', 'stock_maintained'],
['Item', 'is_rm'],
['Journal Voucher Detail', 'line_remarks'],
['Lead', 'designation'],
['Purchase Order', 'challan_number'],
['Quotation', 'cust_enq_no'],
['Quotation', 'enq_date'],
['Quotation', 'quote_valid'],
['Quotation', 'due_date'],
['Receivable Voucher', 'voucher_time'],
['Receivable Voucher', 'removal_time'],
['Receivable Voucher', 'removal_date'],
['Receivable Voucher', 'shipping_address'],
['Receivable Voucher', 'shipping_location'],
['Receivable Voucher', 'ship_to'],
['Receivable Voucher', 'shipping_contact_no'],
['Receivable Voucher', 'shipping_excise_no'],
['Receivable Voucher', 'shipping_tin_no'],
['Receivable Voucher', 'po_no'],
['Receivable Voucher', 'po_date'],
['Receivable Voucher', 'lr_no'],
['Receivable Voucher', 'transporters'],
['Receivable Voucher', 'ship_terms'],
['Receivable Voucher', 'tin_no'],
['Receivable Voucher', 'excise_no'],
['RV Detail', 'cetsh_number'],
['Sales Order', 'shipping_contact_no'],
['Sales Order', 'shipping_tin_no'],
['Sales Order', 'shipping_excise_no'],
['Sales Order', 'tin_no'],
['Sales Order', 'excise_number'],
['Sales Order Detail', 'cetsh_number'],
['Sales Order Detail', 'prd_notes'],
['Shipping Address', 'phone_no'],
['Shipping Address', 'tin_no'],
['Shipping Address', 'excise_no'],
['Stock Entry', 'process_custom'],
['Stock Entry', 'city'],
['Stock Entry', 'address_line_2'],
['Stock Entry', 'address_line_1'],
['Stock Entry', 'comp_other'],
['Stock Entry', 'mobile_no'],
['Stock Entry', 'phone_no'],
['Stock Entry', 'country'],
['Stock Entry', 'state'],
['Stock Entry', 'challan_number'],
['Stock Entry Detail', 'machine'],
['Stock Entry Detail', 'worker'],
['Supplier', 'notes'],
['Supplier', 'purchase_other_charges'],
['Supplier', 'tax_details'],
['Supplier', 'tin_number'],
['Supplier', 'excise_regd_number'],
['Supplier', 'service_tax_regd_number'],
['Warehouse', 'comp_other'],
['Warehouse', 'process'],
['Warehouse', 'country'],
['Warehouse', 'tax_registration_number'],
['Warehouse Type', 'process'],
['Workstation', 'maintenance_data'],
]


import webnotes
from webnotes.model.code import get_obj
from webnotes.model.doc import Document

def execute():
	webnotes.reload_doc('core', 'doctype', 'custom_field')	
	for f in field_list:
		res = webnotes.conn.sql("""SELECT name FROM `tabCustom Field`
				WHERE dt=%s AND fieldname=%s""", (f[0], f[1]))
		if res: continue
		docfield = webnotes.conn.sql("""SELECT * FROM `tabDocField`
			WHERE parent=%s AND fieldname=%s""", (f[0], f[1]), as_dict=1)
		if not docfield: continue
		custom_field = docfield[0]

		# scrub custom field dict
		custom_field['dt'] = custom_field['parent']
		del custom_field['parent']
		
		d = Document('Custom Field', fielddata=custom_field)
		d.name = custom_field['dt'] + '-' + custom_field['fieldname']
		d.save(1, ignore_fields=1)
		#obj = get_obj(doc=d)
		#obj.on_update()
