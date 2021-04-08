import os
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup(company=None, patch=True):
	make_custom_fields()


def make_custom_fields():
	custom_fields = {
		'Party Account': [
			dict(fieldname='debtor_creditor_number', label='Debtor/Creditor Number',
			fieldtype='Data', insert_after='account', translatable=0)
		]
	}

	create_custom_fields(custom_fields)
