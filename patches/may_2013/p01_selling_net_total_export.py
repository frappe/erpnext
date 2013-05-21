from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint

def execute():
	for module, doctype in (("Accounts", "Sales Invoice"), ("Selling", "Sales Order"), ("Selling", "Quotation"), 
		("Stock", "Delivery Note")):
			webnotes.reload_doc(module, "DocType", doctype)
			webnotes.conn.sql("""update `tab%s` 
				set net_total_export = round(net_total / if(conversion_rate=0, 1, ifnull(conversion_rate, 1)), 2),
				other_charges_total_export = round(grand_total_export - net_total_export, 2)""" %
				(doctype,))
	
	for module, doctype in (("Accounts", "Sales Invoice Item"), ("Selling", "Sales Order Item"), ("Selling", "Quotation Item"), 
		("Stock", "Delivery Note Item")):
			if cint(webnotes.conn.get_value("DocField", {"parent": doctype, "fieldname": "ref_rate"}, "read_only")) == 0 and \
				not webnotes.conn.sql("""select name from `tabProperty Setter` where doc_type=%s and doctype_or_field='DocField'
					and field_name='ref_rate' and property='read_only'""", doctype):
				webnotes.bean({
					"doctype": "Property Setter",
					"doc_type": doctype,
					"doctype_or_field": "DocField",
					"field_name": "ref_rate",
					"property": "read_only",
					"property_type": "Check",
					"value": "0"
				}).insert()
				
			webnotes.reload_doc(module, "DocType", doctype)