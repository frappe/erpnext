from __future__ import unicode_literals
import frappe

"""This will update existing GL Entries by saving its linked Purchase/Sales Invoice's
and Journal Entry's due date as the due date for the GL Entry"""


def execute():
	kwargs = get_query_kwargs()

	for kwarg in kwargs:
		for batch in get_result_in_batches(**kwarg):
			voucher_num_col = kwarg.get('voucher_num_col', 'voucher_no')
			voucher_type = kwarg.get('use_voucher_type') or kwarg.get('voucher_type')
			conditions, names = build_conditions(batch, voucher_type, voucher_num_col)
			if conditions and names:
				start = 'UPDATE `tabGL Entry` SET `due_date` = CASE '
				cond = ' '.join(conditions)
				else_cond = ' ELSE `due_date` END WHERE '

				frappe.db.sql(
					start + cond + else_cond + voucher_num_col + ' IN %s',
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
	or_filters = kwargs.get('or_filters')

	results = frappe.get_list(
		doctype, fields=fields, limit_start=limit_start, limit_page_length=limit_page_length,
		filters=filters, or_filters=or_filters
	)

	return results


def build_conditions(query_results, voucher_type, voucher_num_col):
	"""
	builds the string to be used is sql CASE statement. Returns the a tuple of
	the string for the CASE statement and a tuple of applicable voucher names
	"""
	conditions = []
	invoice_names = []

	for result in query_results:
		voucher_no = result.get(voucher_num_col)
		if voucher_no:
			invoice_names.append("%s" % (voucher_no,))

	# get invoice details
	invoice_details = frappe.get_list(
		voucher_type, fields=['name', 'due_date'], filters={'name': ('in', invoice_names)}
	)

	if invoice_details:
		for d in invoice_details:
			conditions.append('WHEN `{voucher_no}`="{number}" THEN "{date}"'.format(
				number=d.name, date=d.due_date, voucher_no=voucher_num_col))

	return conditions, invoice_names


def get_query_kwargs():
	pi_kwargs = dict(
		voucher_type='Purchase Invoice', doctype='GL Entry', fields=['voucher_no'],
		limit_start=0, limit_page_length=5, filters={
			"ifnull(due_date, '')": ('=', ''), "ifnull(party, '')": ('!=', ''),
			'voucher_type': 'Purchase Invoice', 'credit': ('!=', '0')
		}
	)

	si_kwargs = dict(
		voucher_type='Sales Invoice', doctype='GL Entry', fields=['voucher_no'],
		limit_start=0, limit_page_length=5, filters={
			"ifnull(due_date, '')": ('=', ''), "ifnull(party, '')": ('!=', ''),
			'voucher_type': 'Sales Invoice', 'debit': ('!=', '0')
		}
	)

	journal_kwargs_si = dict(
		voucher_type='Journal Entry', doctype='GL Entry', fields=['against_voucher'],
		limit_start=0, limit_page_length=5, filters={
			"ifnull(due_date, '')": ('=', ''), "ifnull(party, '')": ('!=', ''),
			'voucher_type': 'Journal Entry', 'against_voucher_type': 'Sales Invoice'
		},
		voucher_num_col='against_voucher', use_voucher_type='Sales Invoice',
	)

	journal_kwargs_pi = dict(
		voucher_type='Journal Entry', doctype='GL Entry', fields=['against_voucher'],
		limit_start=0, limit_page_length=5, filters={
			"ifnull(due_date, '')": ('=', ''), "ifnull(party, '')": ('!=', ''),
			'voucher_type': 'Journal Entry', 'against_voucher_type': 'Purchase Invoice'
		},
		voucher_num_col='against_voucher', use_voucher_type='Purchase Invoice',
	)

	payment_entry_kwargs_pi = dict(
		voucher_type='Payment Entry', doctype='GL Entry', fields=['against_voucher'],
		limit_start=0, limit_page_length=5, filters={
			"ifnull(due_date, '')": ('=', ''), "ifnull(party, '')": ('!=', ''),
			'voucher_type': 'Payment Entry', 'against_voucher_type': 'Purchase Invoice'
		},
		voucher_num_col='against_voucher', use_voucher_type='Purchase Invoice',
	)

	payment_entry_kwargs_si = dict(
		voucher_type='Payment Entry', doctype='GL Entry', fields=['against_voucher'],
		limit_start=0, limit_page_length=5, filters={
			"ifnull(due_date, '')": ('=', ''), "ifnull(party, '')": ('!=', ''),
			'voucher_type': 'Payment Entry', 'against_voucher_type': 'Sales Invoice'
		},
		voucher_num_col='against_voucher', use_voucher_type='Sales Invoice',
	)

	return [
		pi_kwargs, si_kwargs, journal_kwargs_pi, journal_kwargs_si,
		payment_entry_kwargs_pi, payment_entry_kwargs_si
	]
