# V 1.0.1

from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	make_custom_fields()

def make_custom_fields():
	allow_cost_center_in_entry_of_bs_account_field = [
		dict(	fieldname='allow_cost_center_in_entry_of_bs_account', 
			label='Allow Cost Center In Entry of Balance Sheet Account', 
			fieldtype='Check',
			insert_after='book_asset_depreciation_entry_automatically'
		),
	]	

	custom_fields = {
		"Accounts Settings": allow_cost_center_in_entry_of_bs_account_field,
	}	

	create_custom_fields(custom_fields)

	frappe.get_doc("DocType", "Accounts Settings").run_module_method("on_doctype_update")

