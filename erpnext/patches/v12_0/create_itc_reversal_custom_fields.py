from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from erpnext.regional.india.utils import get_gst_accounts

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'}, fields=['name'])
	if not company:
		return

	frappe.reload_doc("regional", "doctype", "gst_settings")
	frappe.reload_doc("accounts", "doctype", "gst_account")

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
				options='Input Service Distributor\nImport Of Service\nImport Of Capital Goods\nITC on Reverse Charge\nIneligible As Per Section 17(5)\nIneligible Others\nAll Other ITC',
				default="All Other ITC")
		],
		'Purchase Invoice Item': [
			dict(fieldname='taxable_value', label='Taxable Value',
				fieldtype='Currency', insert_after='base_net_amount', hidden=1, options="Company:company:default_currency",
				print_hide=1)
		]
	}

	create_custom_fields(custom_fields, update=True)

	# Patch ITC Availed fields from Data to Currency
	# Patch Availed ITC for current fiscal_year

	gst_accounts = get_gst_accounts(only_non_reverse_charge=1)

	frappe.db.sql("""
		UPDATE `tabCustom Field` SET fieldtype='Currency', options='Company:company:default_currency'
		WHERE dt = 'Purchase Invoice' and fieldname in ('itc_integrated_tax', 'itc_state_tax', 'itc_central_tax',
			'itc_cess_amount')
	""")

	frappe.db.sql("""UPDATE `tabPurchase Invoice` set itc_integrated_tax = '0'
		WHERE trim(coalesce(itc_integrated_tax, '')) = '' """)

	frappe.db.sql("""UPDATE `tabPurchase Invoice` set itc_state_tax = '0'
		WHERE trim(coalesce(itc_state_tax, '')) = '' """)

	frappe.db.sql("""UPDATE `tabPurchase Invoice` set itc_central_tax = '0'
		WHERE trim(coalesce(itc_central_tax, '')) = '' """)

	frappe.db.sql("""UPDATE `tabPurchase Invoice` set itc_cess_amount = '0'
		WHERE trim(coalesce(itc_cess_amount, '')) = '' """)

	# Get purchase invoices
	invoices = frappe.get_all('Purchase Invoice',
		{'posting_date': ('>=', '2021-04-01'), 'eligibility_for_itc': ('!=', 'Ineligible')},
		['name'])

	amount_map = {}

	if invoices:
		invoice_list = set([d.name for d in invoices])

		# Get GST applied
		amounts = frappe.db.sql("""
			SELECT parent, account_head, sum(base_tax_amount_after_discount_amount) as amount
			FROM `tabPurchase Taxes and Charges`
			where parent in %s
			GROUP BY parent, account_head
		""", (invoice_list), as_dict=1)

		for d in amounts:
			amount_map.setdefault(d.parent,
			{
				'itc_integrated_tax': 0,
				'itc_state_tax': 0,
				'itc_central_tax': 0,
				'itc_cess_amount': 0
			})

			if d.account_head in gst_accounts.get('igst_account'):
				amount_map[d.parent]['itc_integrated_tax'] += d.amount
			if d.account_head in gst_accounts.get('cgst_account'):
				amount_map[d.parent]['itc_central_tax'] += d.amount
			if d.account_head in gst_accounts.get('sgst_account'):
				amount_map[d.parent]['itc_state_tax'] += d.amount
			if d.account_head in gst_accounts.get('cess_account'):
				amount_map[d.parent]['itc_cess_amount'] += d.amount

		for invoice, values in amount_map.items():
			frappe.db.set_value('Purchase Invoice', invoice, {
				'itc_integrated_tax': values.get('itc_integrated_tax'),
				'itc_central_tax': values.get('itc_central_tax'),
				'itc_state_tax': values['itc_state_tax'],
				'itc_cess_amount': values['itc_cess_amount'],
			})