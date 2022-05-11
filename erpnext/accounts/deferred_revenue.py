import frappe
from frappe import _
from frappe.email import sendmail_to_system_managers
from frappe.utils import (
	add_days,
	add_months,
	cint,
	date_diff,
	flt,
	get_first_day,
	get_last_day,
	get_link_to_form,
	getdate,
	rounded,
	today,
)

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.utils import get_account_currency


def validate_service_stop_date(doc):
	"""Validates service_stop_date for Purchase Invoice and Sales Invoice"""

	enable_check = (
		"enable_deferred_revenue" if doc.doctype == "Sales Invoice" else "enable_deferred_expense"
	)

	old_stop_dates = {}
	old_doc = frappe.db.get_all(
		"{0} Item".format(doc.doctype), {"parent": doc.name}, ["name", "service_stop_date"]
	)

	for d in old_doc:
		old_stop_dates[d.name] = d.service_stop_date or ""

	for item in doc.items:
		if not item.get(enable_check):
			continue

		if item.service_stop_date:
			if date_diff(item.service_stop_date, item.service_start_date) < 0:
				frappe.throw(_("Service Stop Date cannot be before Service Start Date"))

			if date_diff(item.service_stop_date, item.service_end_date) > 0:
				frappe.throw(_("Service Stop Date cannot be after Service End Date"))

		if (
			old_stop_dates
			and old_stop_dates.get(item.name)
			and item.service_stop_date != old_stop_dates.get(item.name)
		):
			frappe.throw(_("Cannot change Service Stop Date for item in row {0}").format(item.idx))


def build_conditions(process_type, account, company):
	conditions = ""
	deferred_account = (
		"item.deferred_revenue_account" if process_type == "Income" else "item.deferred_expense_account"
	)

	if account:
		conditions += "AND %s='%s'" % (deferred_account, account)
	elif company:
		conditions += f"AND p.company = {frappe.db.escape(company)}"

	return conditions


def convert_deferred_expense_to_expense(
	deferred_process, start_date=None, end_date=None, conditions=""
):
	# book the expense/income on the last day, but it will be trigger on the 1st of month at 12:00 AM

	if not start_date:
		start_date = add_months(today(), -1)
	if not end_date:
		end_date = add_days(today(), -1)

	# check for the purchase invoice for which GL entries has to be done
	invoices = frappe.db.sql_list(
		"""
		select distinct item.parent
		from `tabPurchase Invoice Item` item, `tabPurchase Invoice` p
		where item.service_start_date<=%s and item.service_end_date>=%s
		and item.enable_deferred_expense = 1 and item.parent=p.name
		and item.docstatus = 1 and ifnull(item.amount, 0) > 0
		{0}
	""".format(
			conditions
		),
		(end_date, start_date),
	)  # nosec

	# For each invoice, book deferred expense
	for invoice in invoices:
		doc = frappe.get_doc("Purchase Invoice", invoice)
		book_deferred_income_or_expense(doc, deferred_process, end_date)

	if frappe.flags.deferred_accounting_error:
		send_mail(deferred_process)


def convert_deferred_revenue_to_income(
	deferred_process, start_date=None, end_date=None, conditions=""
):
	# book the expense/income on the last day, but it will be trigger on the 1st of month at 12:00 AM

	if not start_date:
		start_date = add_months(today(), -1)
	if not end_date:
		end_date = add_days(today(), -1)

	# check for the sales invoice for which GL entries has to be done
	invoices = frappe.db.sql_list(
		"""
		select distinct item.parent
		from `tabSales Invoice Item` item, `tabSales Invoice` p
		where item.service_start_date<=%s and item.service_end_date>=%s
		and item.enable_deferred_revenue = 1 and item.parent=p.name
		and item.docstatus = 1 and ifnull(item.amount, 0) > 0
		{0}
	""".format(
			conditions
		),
		(end_date, start_date),
	)  # nosec

	for invoice in invoices:
		doc = frappe.get_doc("Sales Invoice", invoice)
		book_deferred_income_or_expense(doc, deferred_process, end_date)

	if frappe.flags.deferred_accounting_error:
		send_mail(deferred_process)


def get_booking_dates(doc, item, posting_date=None):
	if not posting_date:
		posting_date = add_days(today(), -1)

	last_gl_entry = False

	deferred_account = (
		"deferred_revenue_account" if doc.doctype == "Sales Invoice" else "deferred_expense_account"
	)

	prev_gl_entry = frappe.db.sql(
		"""
		select name, posting_date from `tabGL Entry` where company=%s and account=%s and
		voucher_type=%s and voucher_no=%s and voucher_detail_no=%s
		and is_cancelled = 0
		order by posting_date desc limit 1
	""",
		(doc.company, item.get(deferred_account), doc.doctype, doc.name, item.name),
		as_dict=True,
	)

	prev_gl_via_je = frappe.db.sql(
		"""
		SELECT p.name, p.posting_date FROM `tabJournal Entry` p, `tabJournal Entry Account` c
		WHERE p.name = c.parent and p.company=%s and c.account=%s
		and c.reference_type=%s and c.reference_name=%s
		and c.reference_detail_no=%s and c.docstatus < 2 order by posting_date desc limit 1
	""",
		(doc.company, item.get(deferred_account), doc.doctype, doc.name, item.name),
		as_dict=True,
	)

	if prev_gl_via_je:
		if (not prev_gl_entry) or (
			prev_gl_entry and prev_gl_entry[0].posting_date < prev_gl_via_je[0].posting_date
		):
			prev_gl_entry = prev_gl_via_je

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


def calculate_monthly_amount(
	doc, item, last_gl_entry, start_date, end_date, total_days, total_booking_days, account_currency
):
	amount, base_amount = 0, 0

	if not last_gl_entry:
		total_months = (
			(item.service_end_date.year - item.service_start_date.year) * 12
			+ (item.service_end_date.month - item.service_start_date.month)
			+ 1
		)

		prorate_factor = flt(date_diff(item.service_end_date, item.service_start_date)) / flt(
			date_diff(get_last_day(item.service_end_date), get_first_day(item.service_start_date))
		)

		actual_months = rounded(total_months * prorate_factor, 1)

		already_booked_amount, already_booked_amount_in_account_currency = get_already_booked_amount(
			doc, item
		)
		base_amount = flt(item.base_net_amount / actual_months, item.precision("base_net_amount"))

		if base_amount + already_booked_amount > item.base_net_amount:
			base_amount = item.base_net_amount - already_booked_amount

		if account_currency == doc.company_currency:
			amount = base_amount
		else:
			amount = flt(item.net_amount / actual_months, item.precision("net_amount"))
			if amount + already_booked_amount_in_account_currency > item.net_amount:
				amount = item.net_amount - already_booked_amount_in_account_currency

		if not (get_first_day(start_date) == start_date and get_last_day(end_date) == end_date):
			partial_month = flt(date_diff(end_date, start_date)) / flt(
				date_diff(get_last_day(end_date), get_first_day(start_date))
			)

			base_amount = rounded(partial_month, 1) * base_amount
			amount = rounded(partial_month, 1) * amount
	else:
		already_booked_amount, already_booked_amount_in_account_currency = get_already_booked_amount(
			doc, item
		)
		base_amount = flt(
			item.base_net_amount - already_booked_amount, item.precision("base_net_amount")
		)
		if account_currency == doc.company_currency:
			amount = base_amount
		else:
			amount = flt(
				item.net_amount - already_booked_amount_in_account_currency, item.precision("net_amount")
			)

	return amount, base_amount


def calculate_amount(doc, item, last_gl_entry, total_days, total_booking_days, account_currency):
	amount, base_amount = 0, 0
	if not last_gl_entry:
		base_amount = flt(
			item.base_net_amount * total_booking_days / flt(total_days), item.precision("base_net_amount")
		)
		if account_currency == doc.company_currency:
			amount = base_amount
		else:
			amount = flt(
				item.net_amount * total_booking_days / flt(total_days), item.precision("net_amount")
			)
	else:
		already_booked_amount, already_booked_amount_in_account_currency = get_already_booked_amount(
			doc, item
		)

		base_amount = flt(
			item.base_net_amount - already_booked_amount, item.precision("base_net_amount")
		)
		if account_currency == doc.company_currency:
			amount = base_amount
		else:
			amount = flt(
				item.net_amount - already_booked_amount_in_account_currency, item.precision("net_amount")
			)

	return amount, base_amount


def get_already_booked_amount(doc, item):
	if doc.doctype == "Sales Invoice":
		total_credit_debit, total_credit_debit_currency = "debit", "debit_in_account_currency"
		deferred_account = "deferred_revenue_account"
	else:
		total_credit_debit, total_credit_debit_currency = "credit", "credit_in_account_currency"
		deferred_account = "deferred_expense_account"

	gl_entries_details = frappe.db.sql(
		"""
		select sum({0}) as total_credit, sum({1}) as total_credit_in_account_currency, voucher_detail_no
		from `tabGL Entry` where company=%s and account=%s and voucher_type=%s and voucher_no=%s and voucher_detail_no=%s
		and is_cancelled = 0
		group by voucher_detail_no
	""".format(
			total_credit_debit, total_credit_debit_currency
		),
		(doc.company, item.get(deferred_account), doc.doctype, doc.name, item.name),
		as_dict=True,
	)

	journal_entry_details = frappe.db.sql(
		"""
		SELECT sum(c.{0}) as total_credit, sum(c.{1}) as total_credit_in_account_currency, reference_detail_no
		FROM `tabJournal Entry` p , `tabJournal Entry Account` c WHERE p.name = c.parent and
		p.company = %s and c.account=%s and c.reference_type=%s and c.reference_name=%s and c.reference_detail_no=%s
		and p.docstatus < 2 group by reference_detail_no
	""".format(
			total_credit_debit, total_credit_debit_currency
		),
		(doc.company, item.get(deferred_account), doc.doctype, doc.name, item.name),
		as_dict=True,
	)

	already_booked_amount = gl_entries_details[0].total_credit if gl_entries_details else 0
	already_booked_amount += journal_entry_details[0].total_credit if journal_entry_details else 0

	if doc.currency == doc.company_currency:
		already_booked_amount_in_account_currency = already_booked_amount
	else:
		already_booked_amount_in_account_currency = (
			gl_entries_details[0].total_credit_in_account_currency if gl_entries_details else 0
		)
		already_booked_amount_in_account_currency += (
			journal_entry_details[0].total_credit_in_account_currency if journal_entry_details else 0
		)

	return already_booked_amount, already_booked_amount_in_account_currency


def book_deferred_income_or_expense(doc, deferred_process, posting_date=None):
	enable_check = (
		"enable_deferred_revenue" if doc.doctype == "Sales Invoice" else "enable_deferred_expense"
	)

	accounts_frozen_upto = frappe.get_cached_value("Accounts Settings", "None", "acc_frozen_upto")

	def _book_deferred_revenue_or_expense(
		item, via_journal_entry, submit_journal_entry, book_deferred_entries_based_on
	):
		start_date, end_date, last_gl_entry = get_booking_dates(doc, item, posting_date=posting_date)
		if not (start_date and end_date):
			return

		account_currency = get_account_currency(item.expense_account or item.income_account)
		if doc.doctype == "Sales Invoice":
			against, project = doc.customer, doc.project
			credit_account, debit_account = item.income_account, item.deferred_revenue_account
		else:
			against, project = doc.supplier, item.project
			credit_account, debit_account = item.deferred_expense_account, item.expense_account

		total_days = date_diff(item.service_end_date, item.service_start_date) + 1
		total_booking_days = date_diff(end_date, start_date) + 1

		if book_deferred_entries_based_on == "Months":
			amount, base_amount = calculate_monthly_amount(
				doc,
				item,
				last_gl_entry,
				start_date,
				end_date,
				total_days,
				total_booking_days,
				account_currency,
			)
		else:
			amount, base_amount = calculate_amount(
				doc, item, last_gl_entry, total_days, total_booking_days, account_currency
			)

		if not amount:
			return

		# check if books nor frozen till endate:
		if accounts_frozen_upto and (end_date) <= getdate(accounts_frozen_upto):
			end_date = get_last_day(add_days(accounts_frozen_upto, 1))

		if via_journal_entry:
			book_revenue_via_journal_entry(
				doc,
				credit_account,
				debit_account,
				amount,
				base_amount,
				end_date,
				project,
				account_currency,
				item.cost_center,
				item,
				deferred_process,
				submit_journal_entry,
			)
		else:
			make_gl_entries(
				doc,
				credit_account,
				debit_account,
				against,
				amount,
				base_amount,
				end_date,
				project,
				account_currency,
				item.cost_center,
				item,
				deferred_process,
			)

		# Returned in case of any errors because it tries to submit the same record again and again in case of errors
		if frappe.flags.deferred_accounting_error:
			return

		if getdate(end_date) < getdate(posting_date) and not last_gl_entry:
			_book_deferred_revenue_or_expense(
				item, via_journal_entry, submit_journal_entry, book_deferred_entries_based_on
			)

	via_journal_entry = cint(
		frappe.db.get_singles_value("Accounts Settings", "book_deferred_entries_via_journal_entry")
	)
	submit_journal_entry = cint(
		frappe.db.get_singles_value("Accounts Settings", "submit_journal_entries")
	)
	book_deferred_entries_based_on = frappe.db.get_singles_value(
		"Accounts Settings", "book_deferred_entries_based_on"
	)

	for item in doc.get("items"):
		if item.get(enable_check):
			_book_deferred_revenue_or_expense(
				item, via_journal_entry, submit_journal_entry, book_deferred_entries_based_on
			)


def process_deferred_accounting(posting_date=None):
	"""Converts deferred income/expense into income/expense
	Executed via background jobs on every month end"""

	if not posting_date:
		posting_date = today()

	if not cint(
		frappe.db.get_singles_value(
			"Accounts Settings", "automatically_process_deferred_accounting_entry"
		)
	):
		return

	start_date = add_months(today(), -1)
	end_date = add_days(today(), -1)

	companies = frappe.get_all("Company")

	for company in companies:
		for record_type in ("Income", "Expense"):
			doc = frappe.get_doc(
				dict(
					doctype="Process Deferred Accounting",
					company=company.name,
					posting_date=posting_date,
					start_date=start_date,
					end_date=end_date,
					type=record_type,
				)
			)

			doc.insert()
			doc.submit()


def make_gl_entries(
	doc,
	credit_account,
	debit_account,
	against,
	amount,
	base_amount,
	posting_date,
	project,
	account_currency,
	cost_center,
	item,
	deferred_process=None,
):
	# GL Entry for crediting the amount in the deferred expense
	from erpnext.accounts.general_ledger import make_gl_entries

	if amount == 0:
		return

	gl_entries = []
	gl_entries.append(
		doc.get_gl_dict(
			{
				"account": credit_account,
				"against": against,
				"credit": base_amount,
				"credit_in_account_currency": amount,
				"cost_center": cost_center,
				"voucher_detail_no": item.name,
				"posting_date": posting_date,
				"project": project,
				"against_voucher_type": "Process Deferred Accounting",
				"against_voucher": deferred_process,
			},
			account_currency,
			item=item,
		)
	)
	# GL Entry to debit the amount from the expense
	gl_entries.append(
		doc.get_gl_dict(
			{
				"account": debit_account,
				"against": against,
				"debit": base_amount,
				"debit_in_account_currency": amount,
				"cost_center": cost_center,
				"voucher_detail_no": item.name,
				"posting_date": posting_date,
				"project": project,
				"against_voucher_type": "Process Deferred Accounting",
				"against_voucher": deferred_process,
			},
			account_currency,
			item=item,
		)
	)

	if gl_entries:
		try:
			make_gl_entries(gl_entries, cancel=(doc.docstatus == 2), merge_entries=True)
			frappe.db.commit()
		except Exception as e:
			if frappe.flags.in_test:
				doc.log_error(f"Error while processing deferred accounting for Invoice {doc.name}")
				raise e
			else:
				frappe.db.rollback()
				doc.log_error(f"Error while processing deferred accounting for Invoice {doc.name}")
				frappe.flags.deferred_accounting_error = True


def send_mail(deferred_process):
	title = _("Error while processing deferred accounting for {0}").format(deferred_process)
	link = get_link_to_form("Process Deferred Accounting", deferred_process)
	content = _("Deferred accounting failed for some invoices:") + "\n"
	content += _(
		"Please check Process Deferred Accounting {0} and submit manually after resolving errors."
	).format(link)
	sendmail_to_system_managers(title, content)


def book_revenue_via_journal_entry(
	doc,
	credit_account,
	debit_account,
	amount,
	base_amount,
	posting_date,
	project,
	account_currency,
	cost_center,
	item,
	deferred_process=None,
	submit="No",
):

	if amount == 0:
		return

	journal_entry = frappe.new_doc("Journal Entry")
	journal_entry.posting_date = posting_date
	journal_entry.company = doc.company
	journal_entry.voucher_type = (
		"Deferred Revenue" if doc.doctype == "Sales Invoice" else "Deferred Expense"
	)
	journal_entry.process_deferred_accounting = deferred_process

	debit_entry = {
		"account": credit_account,
		"credit": base_amount,
		"credit_in_account_currency": amount,
		"account_currency": account_currency,
		"reference_name": doc.name,
		"reference_type": doc.doctype,
		"reference_detail_no": item.name,
		"cost_center": cost_center,
		"project": project,
	}

	credit_entry = {
		"account": debit_account,
		"debit": base_amount,
		"debit_in_account_currency": amount,
		"account_currency": account_currency,
		"reference_name": doc.name,
		"reference_type": doc.doctype,
		"reference_detail_no": item.name,
		"cost_center": cost_center,
		"project": project,
	}

	for dimension in get_accounting_dimensions():
		debit_entry.update({dimension: item.get(dimension)})

		credit_entry.update({dimension: item.get(dimension)})

	journal_entry.append("accounts", debit_entry)
	journal_entry.append("accounts", credit_entry)

	try:
		journal_entry.save()

		if submit:
			journal_entry.submit()

		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		doc.log_error(f"Error while processing deferred accounting for Invoice {doc.name}")
		frappe.flags.deferred_accounting_error = True


def get_deferred_booking_accounts(doctype, voucher_detail_no, dr_or_cr):

	if doctype == "Sales Invoice":
		credit_account, debit_account = frappe.db.get_value(
			"Sales Invoice Item",
			{"name": voucher_detail_no},
			["income_account", "deferred_revenue_account"],
		)
	else:
		credit_account, debit_account = frappe.db.get_value(
			"Purchase Invoice Item",
			{"name": voucher_detail_no},
			["deferred_expense_account", "expense_account"],
		)

	if dr_or_cr == "Debit":
		return debit_account
	else:
		return credit_account
