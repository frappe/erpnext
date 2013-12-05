# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	# removed following fields
	webnotes.reload_doc("stock", "doctype", "stock_entry")
	custom_fields()
	deprecate_process()
	webnotes.delete_doc("doctype", "sandbox")
	
def custom_fields():
	fields = [
		{
			"label": "Is Excisable Goods",
			"fieldname": "is_excisable_goods",
			"fieldtype": "Select",
			"options": "\nYes\nNo",
			"insert_after": "Company"
		},
		{
			"label": "Excisable Goods",
			"fieldname": "excisable_goods",
			"fieldtype": "Select",
			"options": "\nReturnable\nNon-Returnable)",
			"insert_after": "Amended From"
		},
		{
			"label": "Under Rule",
			"fieldname": "under_rule",
			"fieldtype": "Select",
			"options": "\nOrdinary\n57 AC (5) a\n57 F (2) Non-Exc.",
			"insert_after": "Remarks"
		},
		{
			"label": "Transporter",
			"fieldname": "transporter",
			"fieldtype": "Data",
			"options": "",
			"insert_after": "Project Name"
		},
		{
			"label": "Transfer Date",
			"fieldname": "transfer_date",
			"fieldtype": "Date",
			"options": "",
			"insert_after": "Select Print Heading"
		},
	]
	
	for fld in fields:
		if webnotes.conn.sql("""select name from `tabStock Entry` 
				where ifnull(%s, '') != '' and docstatus<2""", (fld['fieldname'])):
			create_custom_field(fld)
			
def create_custom_field(fld):
	fld.update({
		"doctype": "Custom Field",
		"dt": "Stock Entry",
		"print_hide": 1,
		"permlevel": 0
	})
	
	from webnotes.model.doclist import DocList
	webnotes.insert(DocList([fld]))
	
def deprecate_process():
	webnotes.conn.sql("""update `tabStock Entry` 
		set `purpose`="Material Transfer"
		where process="Material Transfer" and purpose="Production Order" """)
	
	webnotes.conn.sql("""update `tabStock Entry` 
		set `purpose`="Manufacture/Repack"
		where (process="Backflush" and purpose="Production Order") or purpose="Other" """)
		
	webnotes.conn.sql("""update `tabStock Entry` 
		set `purpose`="Subcontract"
		where process="Subcontracting" """)