# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# Contributed by Case Solved and sponsored by Nulight Studios

from __future__ import unicode_literals
import frappe, json
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


def execute(filters=None):
	if not filters:
		return [], []

	fieldlist = required_sql_fields
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

	report_data = modify_report_data(gl_entries)
	summary = None
	if filters['mode'] == 'run' and filters['report_name'] != 'Tax Detail':
		report_data, summary = run_report(filters['report_name'], report_data)

	# return columns, data, message, chart, report_summary
	return get_columns(fieldlist), report_data, None, None, summary

def run_report(report_name, data):
	"Applies the sections and filters saved in the custom report"
	report_config = json.loads(frappe.get_doc('Report', report_name).json)
	# Columns indexed from 1 wrt colno
	columns = report_config.get('columns')
	sections = report_config.get('sections', {})
	show_detail = report_config.get('show_detail', 1)
	new_data = []
	summary = []
	for section_name, section in sections.items():
		section_total = 0.0
		for filt_name, filt in section.items():
			value_field = filt['fieldname']
			rmidxs = []
			for colno, filter_string in filt['filters'].items():
				filter_field = columns[int(colno) - 1]['fieldname']
				for i, row in enumerate(data):
					if not filter_match(row[filter_field], filter_string):
						rmidxs += [i]
			rows = [row for i, row in enumerate(data) if i not in rmidxs]
			section_total += subtotal(rows, value_field)
			if show_detail: new_data += rows
		new_data += [ {columns[1]['fieldname']: section_name, columns[2]['fieldname']: section_total} ]
		summary += [ {'label': section_name, 'datatype': 'Currency', 'value': section_total} ]
		if show_detail: new_data += [ {} ]
	return new_data if new_data else data, summary

def filter_match(value, string):
	"Approximation to datatable filters"
	import datetime
	if string == '': return True
	if value is None: value = -999999999999999
	elif isinstance(value, datetime.date): return True

	if isinstance(value, str):
		value = value.lower()
		string = string.lower()
		if string[0] == '<': return True if string[1:].strip() else False
		elif string[0] == '>': return False if string[1:].strip() else True
		elif string[0] == '=': return string[1:] in value if string[1:] else False
		elif string[0:2] == '!=': return string[2:] not in value
		elif len(string.split(':')) == 2:
			pre, post = string.split(':')
			return (True if not pre.strip() and post.strip() in value else False)
		else:
			return string in value
	else:
		if string[0] in ['<', '>', '=']:
			operator = string[0]
			if operator == '=': operator = '=='
			string = string[1:].strip()
		elif string[0:2] == '!=':
			operator = '!='
			string = string[2:].strip()
		elif len(string.split(':')) == 2:
			pre, post = string.split(':')
			try:
				return (True if float(pre) <= value and float(post) >= value else False)
			except ValueError:
				return (False if pre.strip() else True)
		else:
			return string in str(value)

	try:
		num = float(string) if string.strip() else 0
		return eval(f'{value} {operator} {num}')
	except ValueError:
		if operator == '<': return True
		return False

def subtotal(data, field):
	subtotal = 0.0
	for row in data:
		subtotal += row[field]
	return subtotal

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
def get_custom_reports(name=None):
	filters = custom_report_dict.copy()
	if name:
		filters['name'] = name
	reports = frappe.get_list('Report',
		filters = filters,
		fields = ['name', 'json'],
		as_list=False
	)
	reports_dict = {rep.pop('name'): rep for rep in reports}
	# Prevent custom reports with the same name
	reports_dict['Tax Detail'] = {'json': None}
	return reports_dict

@frappe.whitelist()
def save_custom_report(reference_report, report_name, data):
	if reference_report != 'Tax Detail':
		frappe.throw(_("The wrong report is referenced."))
	if report_name == 'Tax Detail':
		frappe.throw(_("The parent report cannot be overwritten."))

	doc = {
		'doctype': 'Report',
		'report_name': report_name,
		'is_standard': 'No',
		'module': 'Accounts',
		'json': data
	}
	doc.update(custom_report_dict)

	try:
		newdoc = frappe.get_doc(doc)
		newdoc.insert()
		frappe.msgprint(_("Report created successfully"))
	except frappe.exceptions.DuplicateEntryError:
		dbdoc = frappe.get_doc('Report', report_name)
		dbdoc.update(doc)
		dbdoc.save()
		frappe.msgprint(_("Report updated successfully"))
	return report_name
