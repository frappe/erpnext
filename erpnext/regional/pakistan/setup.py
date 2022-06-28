import frappe, os, json
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import add_permission, update_permission_property
from frappe.utils import today

def setup(company=None, patch=True):
	# Company independent fixtures should be called only once at the first company setup
	if patch or frappe.db.count("Company", {"country": "Pakistan"}) <= 1:
		setup_company_independent_fixtures(patch=patch)
  
# TODO: for all countries
def setup_company_independent_fixtures(patch=False):
	make_custom_fields()
 
def make_custom_fields(update=True):
	custom_fields = get_custom_fields()
	create_custom_fields(custom_fields, update=update)
 
def get_custom_fields():
    
	custom_fields = {
		"Item": [
			dict(
				fieldname="hex_code",
				label="Hex Code",
				fieldtype="Data",
				insert_after="item_group",
			)
		]
		
	}

	return custom_fields
