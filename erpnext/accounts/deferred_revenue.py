from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import date_diff, add_months, today, getdate, add_days, flt, get_last_day
from erpnext.accounts.utils import get_account_currency
from frappe.email import sendmail_to_system_managers

def validate_service_stop_date(doc):
	''' Validates service_stop_date for Purchase Invoice and Sales Invoice '''

	enable_check = "enable_deferred_revenue" \
		if doc.doctype=="Sales Invoice" else "enable_deferred_expense"

	old_stop_dates = {}
	old_doc = frappe.db.get_all("{0} Item".format(doc.doctype),
		{"parent": doc.name}, ["name", "service_stop_date"])

	for d in old_doc:
		old_stop_dates[d.name] = d.service_stop_date or ""

	for item in doc.items:
		if not item.get(enable_check): continue

		if item.service_stop_date:
			if date_diff(item.service_stop_date, item.service_start_date) < 0:
				frappe.throw(_("Service Stop Date cannot be before Service Start Date"))

			if date_diff(item.service_stop_date, item.service_end_date) > 0:
				frappe.throw(_("Service Stop Date cannot be after Service End Date"))

		if old_stop_dates and old_stop_dates.get(item.name) and item.service_stop_date!=old_stop_dates.get(item.name):
			frappe.throw(_("Cannot change Service Stop Date for item in row {0}".format(item.idx)))

def convert_deferred_expense_to_expense(start_date=None, end_date=None):
	# book the expense/income on the last day, but it will be trigger on the 1st of month at 12:00 AM
	if not start_date:
		start_date = add_months(today(), -1)
	if not end_date:
		end_date = add_days(today(), -1)

	# check for the purchase invoice for which GL entries has to be done
	invoices = frappe.db.sql_list('''
		select distinct parent from `tabPurchase Invoice Item`
		where service_start_date<=%s and service_end_date>=%s
		and enable_deferred_expense = 1 and docstatus = 1 and ifnull(amount, 0) > 0
	''', (end_date, start_date))

	# For each invoice, book deferred expense
	for invoice in invoices:
		doc = frappe.get_doc("Purchase Invoice", invoice)
		book_deferred_income_or_expense(doc, end_date)

def convert_deferred_revenue_to_income(start_date=None, end_date=None):
	# book the expense/income on the last day, but it will be trigger on the 1st of month at 12:00 AM
	if not start_date:
		start_date = add_months(today(), -1)
	if not end_date:
		end_date = add_days(today(), -1)

	# check for the sales invoice for which GL entries has to be done
	invoices = frappe.db.sql_list('''
		select distinct parent from `tabSales Invoice Item`
		where service_start_date<=%s and service_end_date>=%s
		and enable_deferred_revenue = 1 and docstatus = 1 and ifnull(amount, 0) > 0
	''', (end_date, start_date))

	for invoice in invoices:
		doc = frappe.get_doc("Sales Invoice", invoice)
		book_deferred_income_or_expense(doc, end_date)

def get_booking_dates(doc, item, posting_date=None):
	if not posting_date:
		posting_date = add_days(today(), -1)

	last_gl_entry = False

	deferred_account = "deferred_revenue_account" if doc.doctype=="Sales Invoice" else "deferred_expense_account"

	prev_gl_entry = frappe.db.sql('''
		select name, posting_date from `tabGL Entry` where company=%s and account=%s and
		voucher_type=%s and voucher_no=%s and voucher_detail_no=%s
		order by posting_date desc limit 1
	''', (doc.company, item.get(deferred_account), doc.doctype, doc.name, item.name), as_dict=True)

	if prev_gl_entry:
		start_date = getdate(add_days(prev_gl_entry[0].posting_date, 1))
	else:
		start_date = item.service_start_date

	end_date = get_last_day(start_date)
	if end_date >= item.service_end_date:
		end_date = item.service_end_date
		last_gl_entry = True
	elif item.service_stop_date and end_date >= item.service_stop_date:
		end_date = item.service_stop_date
		last_gl_entry = True

	if end_date > getdate(posting_date):
		end_date = posting_date

	if getdate(start_date) <= getdate(end_date):
		return start_date, end_date, last_gl_entry
	else:
		return None, None, None

def calculate_amount(doc, item, last_gl_entry, total_days, total_booking_days, account_currency):
	if doc.doctype == "Sales Invoice":
		total_credit_debit, total_credit_debit_currency = "debit", "debit_in_account_currency"
		deferred_account = "deferred_revenue_account"
	else:
		total_credit_debit, total_credit_debit_currency = "credit", "credit_in_account_currency"
		deferred_account = "deferred_expense_account"

	amount, base_amount = 0, 0
	if not last_gl_entry:
		base_amount = flt(item.base_net_amount*total_booking_days/flt(total_days), item.precision("base_net_amount"))
		if account_currency==doc.company_currency:
			amount = base_amount
		else:
			amount = flt(item.net_amount*total_booking_days/flt(total_days), item.precision("net_amount"))
	else:
		gl_entries_details = frappe.db.sql('''
			select sum({0}) as total_credit, sum({1}) as total_credit_in_account_currency, voucher_detail_no
			from `tabGL Entry` where company=%s and account=%s and voucher_type=%s and voucher_no=%s and voucher_detail_no=%s
			group by voucher_detail_no
		'''.format(total_credit_debit, total_credit_debit_currency),
			(doc.company, item.get(deferred_account), doc.doctype, doc.name, item.name), as_dict=True)
		already_booked_amount = gl_entries_details[0].total_credit if gl_entries_details else 0
		base_amount = flt(item.base_net_amount - already_booked_amount, item.precision("base_net_amount"))
		if account_currency==doc.company_currency:
			amount = base_amount
		else:
			already_booked_amount_in_account_currency = gl_entries_details[0].total_credit_in_account_currency if gl_entries_details else 0
			amount = flt(item.net_amount - already_booked_amount_in_account_currency, item.precision("net_amount"))

	return amount, base_amount

def book_deferred_income_or_expense(doc, posting_date=None):
	enable_check = "enable_deferred_revenue" \
		if doc.doctype=="Sales Invoice" else "enable_deferred_expense"

	def _book_deferred_revenue_or_expense(item):
		start_date, end_date, last_gl_entry = get_booking_dates(doc, item, posting_date=posting_date)
		if not (start_date and end_date): return

		account_currency = get_account_currency(item.expense_account)
		if doc.doctype == "Sales Invoice":
			against, project = doc.customer, doc.project
			credit_account, debit_account = item.income_account, item.deferred_revenue_account
		else:
			against, project = doc.supplier, item.project
			credit_account, debit_account = item.deferred_expense_account, item.expense_account

		total_days = date_diff(item.service_end_date, item.service_start_date) + 1
		total_booking_days = date_diff(end_date, start_date) + 1

		amount, base_amount = calculate_amount(doc, item, last_gl_entry,
			total_days, total_booking_days, account_currency)

		make_gl_entries(doc, credit_account, debit_account, against,
			amount, base_amount, end_date, project, account_currency, item.cost_center, item)

		if getdate(end_date) < getdate(posting_date) and not last_gl_entry:
			_book_deferred_revenue_or_expense(item)


	for item in doc.get('items'):
		if item.get(enable_check):
			_book_deferred_revenue_or_expense(item)

def make_gl_entries(doc, credit_account, debit_account, against,
	amount, base_amount, posting_date, project, account_currency, cost_center, item):
	# GL Entry for crediting the amount in the deferred expense
	from erpnext.accounts.general_ledger import make_gl_entries

	if amount == 0: return

	gl_entries = []
	gl_entries.append(
		doc.get_gl_dict({
			"account": credit_account,
			"against": against,
			"credit": base_amount,
			"credit_in_account_currency": amount,
			"cost_center": cost_center,
			"voucher_detail_no": item.name,
			'posting_date': posting_date,
			'project': project
		}, account_currency, item=item)
	)
	# GL Entry to debit the amount from the expense
	gl_entries.append(
		doc.get_gl_dict({
			"account": debit_account,
			"against": against,
			"debit": base_amount,
			"debit_in_account_currency": amount,
			"cost_center": cost_center,
			"voucher_detail_no": item.name,
			'posting_date': posting_date,
			'project': project
		}, account_currency, item=item)
	)

	if gl_entries:
		try:
			make_gl_entries(gl_entries, cancel=(doc.docstatus == 2), merge_entries=True)
			frappe.db.commit()
		except:
			frappe.db.rollback()
			title = _("Error while processing deferred accounting for {0}").format(doc.name)
			traceback = frappe.get_traceback()
			frappe.log_error(message=traceback , title=title)
			sendmail_to_system_managers(title, traceback)