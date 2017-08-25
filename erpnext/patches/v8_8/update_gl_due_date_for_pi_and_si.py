from __future__ import unicode_literals
import frappe

"""
This will update existing GL Entries by saving its linked Purchase/Sales Invoice's
due date as the due date for the GL Entry
"""


def execute():
	pi_kwargs = dict(
		voucher_type='Purchase Invoice', doctype='GL Entry', fields=['voucher_no'],
		limit_start=0, limit_page_length=5, filters={
			"ifnull(due_date, '')": ('=', ''), "ifnull(party, '')": ('!=', ''),
			'voucher_type': 'Purchase Invoice', 'debit': ('!=', '0')
		}
	)
	si_kwargs = dict(
		voucher_type='Sales Invoice', doctype='GL Entry', fields=['voucher_no'],
		limit_start=0, limit_page_length=5, filters={
			"ifnull(due_date, '')": ('=', ''), "ifnull(party, '')": ('!=', ''),
			'voucher_type': 'Sales Invoice', 'credit': ('!=', '0')
		}
	)
	kwargs = [pi_kwargs, si_kwargs]

	for kwarg in kwargs:
		for batch in get_result_in_batches(**kwarg):
			conditions, names = build_conditions(batch, kwarg.get('voucher_type'))
			if conditions and names:
				start = 'UPDATE `tabGL Entry` SET `due_date` = CASE '
				cond = ' '.join(conditions)
				frappe.db.sql(
					start + cond + ' ELSE `due_date` END WHERE `voucher_no` IN %s',
					values=(names,)
				)


def get_result_in_batches(**kwargs):
	"""A simple generator to yield slices of GL Entry records"""
	while True:
		batch = get_gle_batch(**kwargs)
		if batch:
			yield batch
		else:
			return


def get_gle_batch(**kwargs):
	"""Returns a slice of records in GL Entry"""
	doctype = kwargs.get('doctype')
	fields = kwargs.get('fields')
	limit_start = kwargs.get('limit_start')
	limit_page_length = kwargs.get('limit_page_length')
	filters = kwargs.get('filters')

	results = frappe.get_list(
		doctype, fields=fields, limit_start=limit_start, limit_page_length=limit_page_length,
		filters=filters
	)

	return results


def build_conditions(query_results, voucher_type):
	"""
	builds the string to be used is sql CASE statement. Returns the a tuple of
	the string for the CASE statement and a tuple of applicable voucher names
	"""
	conditions = []
	invoice_names = []

	# first extract the voucher names into two separate lists so it can be easy to query the db
	for result in query_results:
		voucher_no = result.get('voucher_no')
		if voucher_no:
			invoice_names.append("%s" % (voucher_no,))

	# get invoice details
	invoice_details = frappe.get_list(
		voucher_type, fields=['name', 'due_date'], filters={'name': ('in', invoice_names)}
	)

	if invoice_details:
		for d in invoice_details:
			conditions.append('WHEN `voucher_no`="{number}" THEN "{date}"'.format(number=d.name, date=d.due_date))

	return conditions, invoice_names
