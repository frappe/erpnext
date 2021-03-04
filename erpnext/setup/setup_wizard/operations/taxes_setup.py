# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import os
import json

import frappe
from frappe import _


def setup_taxes_and_charges(company_name: str, country: str):
	file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'country_wise_tax.json')
	with open(file_path, 'r') as json_file:
		tax_data = json.load(json_file)

	country_wise_tax = tax_data.get(country)

	if country_wise_tax:
		if 'chart_of_accounts' in country_wise_tax:
			from_detailed_data(company_name, country_wise_tax.get('chart_of_accounts'))
		else:
			from_simple_data(company_name, country_wise_tax)


def from_detailed_data(company_name, data):
	"""
	Create Taxes and Charges Templates from detailed data like this:

	{
		"chart_of_accounts": {
			coa_name: {
				"sales_tax_templates": [
					{
						'title': '',
						'is_default': 1,
						'accounts': [
							{
								'account_name': '',
								'account_number': '',
								'root_type': '',
							}
						]
					}
				],
				"purchase_tax_templates": [ ... ],
				"item_tax_templates": [ ... ],
				"*": [ ... ]
			}
		}
	}
	"""
	coa_name = frappe.db.get_value('Company', company_name, 'chart_of_accounts')
	tax_templates = data.get(coa_name) or data.get('*')
	sales_tax_templates = tax_templates.get('sales_tax_templates') or tax_templates.get('*')
	purchase_tax_templates = tax_templates.get('purchase_tax_templates') or tax_templates.get('*')
	item_tax_templates = tax_templates.get('item_tax_templates') or tax_templates.get('*')

	if sales_tax_templates:
		for template in sales_tax_templates:
			make_tax_template(company_name, 'Sales Taxes and Charges Template', template)

	if purchase_tax_templates:
		for template in purchase_tax_templates:
			make_tax_template(company_name, 'Purchase Taxes and Charges Template', template)

	if item_tax_templates:
		for template in item_tax_templates:
			make_item_tax_template(company_name, template)


def from_simple_data(company_name, data):
	"""
	Create Taxes and Charges Templates from simple data like this:

	"Austria Tax": {
		"account_name": "VAT",
		"tax_rate": 20.00
	}
	"""
	for template_name, tax_data in data.items():
		template = {
			'title': template_name,
			'is_default': tax_data.get('default'),
			'accounts': [
				{
					'account_name': tax_data.get('account_name'),
					'tax_rate': tax_data.get('tax_rate')
				}
			]
		}
		make_tax_template(company_name, 'Sales Taxes and Charges Template', template)
		make_tax_template(company_name, 'Purchase Taxes and Charges Template', template)
		make_item_tax_template(company_name, template)


def make_tax_template(company_name, doctype, template):
	if frappe.db.exists(doctype, {'title': template.get('title'), 'company': company_name}):
		return

	accounts = get_or_create_accounts(company_name, template.get('accounts'))

	# Get all fields of the Taxes and Charges Template
	tax_template = {'doctype': doctype}
	tax_template_fields = frappe.get_meta(doctype).fields
	tax_template_fieldnames = [field.fieldname for field in tax_template_fields]

	# Get all fields of the taxes child table
	table_doctype = [field.options for field in tax_template_fields if field.fieldname=='taxes'][0]
	table_fields = frappe.get_meta(table_doctype).fields
	table_field_names = [field.fieldname for field in table_fields]

	# Check if field exists as a key in the import data and, if yes, set the
	# value accordingly
	for field in tax_template_fieldnames:
		if field in template:
			tax_template[field] = template.get(field)

	# However, company always fixed and taxes table must be empty to start with
	tax_template['company'] = company_name
	tax_template['taxes'] = []

	for account in accounts:
		row = {
			'category': 'Total',
			'charge_type': 'On Net Total',
			'account_head': account.get('name'),
			'description': '{0} @ {1}'.format(account.get('account_name'), account.get('tax_rate')),
			'rate': account.get('tax_rate')
		}
		# Check if field exists as a key in the import data and, if yes, set the
		# value accordingly
		for field in table_field_names:
			if field in account:
				row[field] = account.get(field)

		tax_template['taxes'].append(row)

	return frappe.get_doc(tax_template).insert(ignore_permissions=True)


def make_item_tax_template(company_name, template):
	"""Create an Item Tax Template.

	This requires a separate method because Item Tax Template is structured
	differently from Sales and Purchase Tax Templates.
	"""
	doctype = 'Item Tax Template'
	if frappe.db.exists(doctype, {'title': template.get('title'), 'company': company_name}):
		return

	accounts = get_or_create_accounts(company_name, template.get('accounts'))

	item_tax_template = {
		'doctype': doctype,
		'title': template.get('title'),
		'company': company_name,
		'taxes': [{
			'tax_type': account.get('name'),
			'tax_rate': account.get('tax_rate')
		} for account in accounts]
	}

	return frappe.get_doc(item_tax_template).insert(ignore_permissions=True)


def get_or_create_accounts(company: str, account_data: list):
	for account in account_data:
		if 'creation' in account:
			# Hack to check if account already contains a real Account doc
			# or just the attibutes from country_wise_tax.json
			continue

		# tax_rate should survive the following lines because it might not be
		# specified in an existing account or different rates might get booked
		# onto the same account.
		tax_rate = account.get('tax_rate')
		doc = get_or_create_account(company, account)
		account.update(doc.as_dict())
		account['tax_rate'] = tax_rate

	return account_data


def get_or_create_account(company, account_data):
	"""
	Check if account already exists. If not, create it.
	Return a tax account or None.
	"""
	root_type = account_data.get('root_type', 'Liability')
	account_name = account_data.get('account_name')
	account_number = account_data.get('account_number')

	existing_accounts = frappe.get_list('Account',
		filters={
			'company': company,
			'root_type': root_type
		},
		or_filters={
			'account_name': account_name,
			'account_number': account_number
		}
	)

	if existing_accounts:
		return frappe.get_doc('Account', existing_accounts[0].name)

	tax_group = get_or_create_tax_account_group(company, root_type)
	full_account_data = {
		'doctype': 'Account',
		'account_name': account_name,
		'account_number': account_number,
		'tax_rate': account_data.get('tax_rate'),
		'company': company,
		'parent_account': tax_group,
		'is_group': 0,
		'report_type': 'Balance Sheet',
		'root_type': root_type,
		'account_type': 'Tax'
	}
	return frappe.get_doc(full_account_data).insert(ignore_permissions=True, ignore_mandatory=True)


def get_or_create_tax_account_group(company, root_type):
	tax_group = frappe.db.get_value('Account', {
		'is_group': 1,
		'root_type': root_type,
		'account_type': 'Tax',
		'company': company
	})

	if tax_group:
		return tax_group

	root = frappe.get_list('Account', {
		'is_group': 1,
		'root_type': root_type,
		'company': company,
		'report_type': 'Balance Sheet',
		'parent_account': ('is', 'not set')
	}, limit=1)[0].name

	doc = frappe.get_doc({
		'doctype': 'Account',
		'company': company,
		'is_group': 1,
		'report_type': 'Balance Sheet',
		'root_type': root_type,
		'account_type': 'Tax',
		'account_name': _('Duties and Taxes') if root_type == 'Liability' else _('Tax Assets'),
		'parent_account': root
	}).insert(ignore_permissions=True)

	tax_group = doc.name

	return tax_group
