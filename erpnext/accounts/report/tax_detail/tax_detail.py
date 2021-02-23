# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# Contributed by Case Solved and sponsored by Nulight Studios

from __future__ import unicode_literals
import frappe
from frappe import _

# field lists in multiple doctypes will be coalesced
required_sql_fields = {
	"GL Entry": ["posting_date", "voucher_type", "voucher_no", "account", "account_currency", "debit", "credit"],
	"Account": ["account_type"],
	("Purchase Invoice", "Sales Invoice"): ["taxes_and_charges", "tax_category"],
	("Purchase Invoice Item", "Sales Invoice Item"): ["item_tax_template", "item_name", "base_net_amount", "item_tax_rate"],
#	"Journal Entry": ["total_amount_currency"],
#	"Journal Entry Account": ["debit_in_account_currency", "credit_in_account_currency"]
}

@frappe.whitelist()
def get_required_fieldlist():
	"""For overriding the fieldlist from the client"""
	return required_sql_fields

def execute(filters=None, fieldlist=required_sql_fields):
	if not filters:
		return [], []

	fieldstr = get_fieldstr(fieldlist)

	gl_entries = frappe.db.sql("""
		select {fieldstr}
		from `tabGL Entry` ge
		inner join `tabAccount` a on
			ge.account=a.name and ge.company=a.company
		left join `tabSales Invoice` si on
			a.account_type='Tax' and ge.company=si.company and ge.voucher_type='Sales Invoice' and ge.voucher_no=si.name
		left join `tabSales Invoice Item` sii on
			si.name=sii.parent
		left join `tabPurchase Invoice` pi on
			a.account_type='Tax' and ge.company=pi.company and ge.voucher_type='Purchase Invoice' and ge.voucher_no=pi.name
		left join `tabPurchase Invoice Item` pii on
			pi.name=pii.parent
/*		left outer join `tabJournal Entry` je on
			ge.voucher_no=je.name and ge.company=je.company
		left outer join `tabJournal Entry Account` jea on
			je.name=jea.parent and a.account_type='Tax' */
		where (ge.voucher_type, ge.voucher_no) in (
			select ge.voucher_type, ge.voucher_no
			from `tabGL Entry` ge
			join `tabAccount` a on ge.account=a.name and ge.company=a.company
			where
				a.account_type='Tax' and
				ge.company=%(company)s and
				ge.posting_date>=%(from_date)s and
				ge.posting_date<=%(to_date)s
		)
		order by ge.posting_date, ge.voucher_no
		""".format(fieldstr=fieldstr), filters, as_dict=1)

	gl_entries = modify_report_data(gl_entries)

	return get_columns(fieldlist), gl_entries


abbrev = lambda dt: ''.join(l[0].lower() for l in dt.split(' ')) + '.'
doclist = lambda dt, dfs: [abbrev(dt) + f for f in dfs]
coalesce = lambda dts, dfs: ['coalesce(' + ', '.join(abbrev(dt) + f for dt in dts) + ') ' + f for f in dfs]

def get_fieldstr(fieldlist):
	fields = []
	for doctypes, docfields in fieldlist.items():
		if isinstance(doctypes, str):
			fields += doclist(doctypes, docfields)
		if isinstance(doctypes, tuple):
			fields += coalesce(doctypes, docfields)
	return ', '.join(fields)

def get_columns(fieldlist):
	columns = {}
	for doctypes, docfields in fieldlist.items():
		if isinstance(doctypes, str):
			doctypes = [doctypes]
		for doctype in doctypes:
			meta = frappe.get_meta(doctype)
			# get column field metadata from the db
			fieldmeta = {}
			for field in meta.get('fields'):
				if field.fieldname in docfields:
					fieldmeta[field.fieldname] = {
						"label": _(field.label),
						"fieldname": field.fieldname,
						"fieldtype": field.fieldtype,
						"options": field.options
					}
			# edit the columns to match the modified data
			for field in docfields:
				col = modify_report_columns(doctype, field, fieldmeta[field])
				if col:
					columns[col["fieldname"]] = col
	# use of a dict ensures duplicate columns are removed
	return list(columns.values())

def modify_report_columns(doctype, field, column):
	"Because data is rearranged into other columns"
	if doctype in ["Sales Invoice Item", "Purchase Invoice Item"] and field == "item_tax_rate":
		return None
	if doctype == "Sales Invoice Item" and field == "base_net_amount":
		column.update({"label": _("Credit Net Amount"), "fieldname": "credit_net_amount"})
	if doctype == "Purchase Invoice Item" and field == "base_net_amount":
		column.update({"label": _("Debit Net Amount"), "fieldname": "debit_net_amount"})
	if field == "taxes_and_charges":
		column.update({"label": _("Taxes and Charges Template")})
	return column

def modify_report_data(data):
	import json
	for line in data:
		if line.account_type == "Tax" and line.item_tax_rate:
			tax_rates = json.loads(line.item_tax_rate)
			for account, rate in tax_rates.items():
				if account == line.account:
					if line.voucher_type == "Sales Invoice":
						line.credit = line.base_net_amount * (rate / 100)
						line.credit_net_amount = line.base_net_amount
					if line.voucher_type == "Purchase Invoice":
						line.debit = line.base_net_amount * (rate / 100)
						line.debit_net_amount = line.base_net_amount
	return data

####### JS client utilities

custom_report_dict = {
	'ref_doctype': 'GL Entry',
	'report_type': 'Custom Report',
	'reference_report': 'Tax Detail'
}

@frappe.whitelist()
def get_custom_reports():
	reports = frappe.get_list('Report',
		filters = custom_report_dict,
		fields = ['name', 'json'],
		as_list=False
	)
	reports_dict = {rep.pop('name'): rep for rep in reports}
	# Prevent custom reports with the same name
	reports_dict['Tax Detail'] = {'json': None}
	return reports_dict

@frappe.whitelist()
def new_custom_report(name=None):
	if name == 'Tax Detail':
		frappe.throw("The parent report cannot be overwritten.")
	if not name:
		frappe.throw("The report name must be supplied.")
	doc = {
		'doctype': 'Report',
		'report_name': name,
		'is_standard': 'No',
		'module': 'Accounts'
	}
	doc.update(custom_report_dict)
	doc = frappe.get_doc(doc)
	doc.insert()
	return True

@frappe.whitelist()
def save_custom_report(data):
	return None
