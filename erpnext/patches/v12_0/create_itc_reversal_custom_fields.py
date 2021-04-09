from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	journal_entry_types = frappe.get_meta("Journal Entry").get_options("voucher_type").split("\n") + ['Reversal Of ITC']
	make_property_setter('Journal Entry', 'voucher_type', 'options', '\n'.join(journal_entry_types), '')

	custom_fields = {
		'Journal Entry': [
			dict(fieldname='reversal_type', label='Reversal Type',
				fieldtype='Select', insert_after='voucher_type', print_hide=1,
				options="As per rules 42 & 43 of CGST Rules\nOthers",
				depends_on="eval:doc.voucher_type=='Reversal Of ITC'",
				mandatory_depends_on="eval:doc.voucher_type=='Reversal Of ITC'"),
			dict(fieldname='company_address', label='Company Address',
				fieldtype='Link', options='Address', insert_after='reversal_type',
				print_hide=1, depends_on="eval:doc.voucher_type=='Reversal Of ITC'",
				mandatory_depends_on="eval:doc.voucher_type=='Reversal Of ITC'"),
			dict(fieldname='company_gstin', label='Company GSTIN',
				fieldtype='Data', read_only=1, insert_after='company_address', print_hide=1,
				fetch_from='company_address.gstin',
				depends_on="eval:doc.voucher_type=='Reversal Of ITC'",
				mandatory_depends_on="eval:doc.voucher_type=='Reversal Of ITC'")
		],
		'Purchase Invoice': [
			dict(fieldname='eligibility_for_itc', label='Eligibility For ITC',
				fieldtype='Select', insert_after='reason_for_issuing_document', print_hide=1,
				options='Input Service Distributor\nImport Of Service\nImport Of Capital Goods\nITC on Reverse Charge\nIneligible\nAll Other ITC', default="All Other ITC")
		]
	}

	create_custom_fields(custom_fields, update=True)