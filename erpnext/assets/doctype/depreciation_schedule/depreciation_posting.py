import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today
from frappe.utils.data import get_link_to_form

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)


def post_all_depreciation_entries(date=None):
	# Return if automatic booking of asset depreciation is disabled
	if not cint(
		frappe.db.get_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically")
	):
		return

	if not date:
		date = today()

	for schedule in get_schedules_that_need_posting(date):
		post_depreciation_entries(schedule, date)

		# since values in child tables of submitted docs are getting updated directly // no semgrep
		frappe.db.commit()

	schedules_that_failed_posting = get_schedules_that_failed_to_post_depr_entries()

	if schedules_that_failed_posting:
		notify_accounts_managers(schedules_that_failed_posting)


def get_schedules_that_need_posting(date):
	active_schedules = frappe.get_all(
		"Depreciation Schedule", filters={"status": "Active"}, pluck="name"
	)

	schedules_that_need_posting = frappe.get_all(
		"Asset Depreciation Schedule",
		filters={
			"parent": ["in", active_schedules],
			"schedule_date": ["<=", date],
			"depreciation_entry": None,
		},
		pluck="parent",
	)

	# to remove duplicates
	schedules_that_need_posting = list(set(schedules_that_need_posting))

	return schedules_that_need_posting


@frappe.whitelist()
def post_depreciation_entries(schedule_name, date=None):
	frappe.has_permission("Depreciation Entry", throw=True)

	if not date:
		date = today()

	depr_schedule = frappe.get_doc("Depreciation Schedule", schedule_name)

	if depr_schedule.status != "Active":
		return

	asset = frappe.get_doc("Asset", depr_schedule.asset)
	parent = get_parent(depr_schedule, asset)

	credit_account, debit_account = get_depreciation_accounts(asset.asset_category, asset.company)
	depreciation_cost_center, depreciation_series = get_depreciation_details(asset)
	decrease_in_value = 0

	for schedule in depr_schedule.depreciation_schedule:
		if not schedule.depreciation_entry and getdate(schedule.schedule_date) <= getdate(date):
			depr_entry = make_depreciation_entry(
				schedule,
				depr_schedule,
				asset,
				credit_account,
				debit_account,
				depreciation_cost_center,
				depreciation_series,
			)

			schedule.db_set("depreciation_entry", depr_entry.name)
			record_depreciation_posting(parent, depr_entry)
			decrease_in_value += schedule.depreciation_amount

	update_asset_value_in_parent(parent, depr_schedule.finance_book, decrease_in_value)
	parent.set_status()


def get_parent(depr_schedule, asset):
	if depr_schedule.serial_no:
		parent = frappe.get_doc("Asset Serial No", depr_schedule.serial_no)
	else:
		parent = asset

	return parent


@frappe.whitelist()
def get_depreciation_accounts(asset_category, company):
	accumulated_depreciation_account = depreciation_expense_account = None

	(
		accumulated_depreciation_account,
		depreciation_expense_account,
	) = get_depreciation_accounts_from_asset_category(asset_category, company)

	if not accumulated_depreciation_account or not depreciation_expense_account:
		(
			accumulated_depreciation_account,
			depreciation_expense_account,
		) = get_depreciation_accounts_from_company(
			company, accumulated_depreciation_account, depreciation_expense_account
		)

	if not accumulated_depreciation_account or not depreciation_expense_account:
		frappe.throw(
			_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}").format(
				asset_category, company
			)
		)

	credit_account, debit_account = get_credit_and_debit_accounts(
		accumulated_depreciation_account, depreciation_expense_account
	)

	return credit_account, debit_account


def get_depreciation_accounts_from_asset_category(asset_category, company):
	return frappe.db.get_value(
		"Asset Category Account",
		filters={"parent": asset_category, "company_name": company},
		fieldname=["accumulated_depreciation_account", "depreciation_expense_account"],
	)


def get_depreciation_accounts_from_company(
	company, accumulated_depreciation_account, depreciation_expense_account
):
	accounts = frappe.get_cached_value(
		"Company", company, ["accumulated_depreciation_account", "depreciation_expense_account"]
	)

	if not accumulated_depreciation_account:
		accumulated_depreciation_account = accounts[0]
	if not depreciation_expense_account:
		depreciation_expense_account = accounts[1]

	return accumulated_depreciation_account, depreciation_expense_account


def get_credit_and_debit_accounts(accumulated_depreciation_account, depreciation_expense_account):
	root_type = frappe.get_value("Account", depreciation_expense_account, "root_type")

	if root_type == "Expense":
		credit_account = accumulated_depreciation_account
		debit_account = depreciation_expense_account
	elif root_type == "Income":
		credit_account = depreciation_expense_account
		debit_account = accumulated_depreciation_account
	else:
		frappe.throw(_("Depreciation Expense Account should be an Income or Expense Account."))

	return credit_account, debit_account


def get_depreciation_details(asset):
	depreciation_cost_center, depreciation_series = frappe.get_cached_value(
		"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
	)
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	return depreciation_cost_center, depreciation_series


def make_depreciation_entry(
	schedule_row,
	depr_schedule,
	asset,
	credit_account,
	debit_account,
	depreciation_cost_center,
	depreciation_series,
):
	depr_entry = frappe.new_doc("Depreciation Entry")
	depr_entry.update(
		{
			"naming_series": depreciation_series,
			"posting_date": schedule_row.schedule_date,
			"company": asset.company,
			"asset": depr_schedule.asset,
			"serial_no": depr_schedule.serial_no,
			"finance_book": depr_schedule.finance_book,
			"credit_account": credit_account,
			"debit_account": debit_account,
			"depreciation_amount": schedule_row.depreciation_amount,
			"cost_center": depreciation_cost_center,
			"reference_doctype": depr_schedule.doctype,
			"reference_docname": depr_schedule.name,
			"depr_schedule_row": schedule_row.name,
		}
	)

	add_accounting_dimensions(depr_entry, asset)
	submit_depr_entry(depr_entry, depr_schedule)

	return depr_entry


def add_accounting_dimensions(depr_entry, asset):
	accounting_dimensions = get_checks_for_pl_and_bs_accounts()

	for dimension in accounting_dimensions:
		if (
			asset.get(dimension["fieldname"])
			or dimension.get("mandatory_for_bs")
			or dimension.get("mandatory_for_pl")
		):
			depr_entry.update(
				{
					dimension["fieldname"]: asset.get(dimension["fieldname"])
					or dimension.get("default_dimension")
				}
			)


def submit_depr_entry(depr_entry, depr_schedule):
	depr_entry.flags.ignore_permissions = True
	depr_schedule.flags.ignore_validate_update_after_submit = True

	try:
		depr_entry.save()

		try:
			depr_entry.submit()
			depr_schedule.depr_entry_posting_status = "Successful"
		except Exception:
			depr_schedule.depr_entry_posting_status = "Submit Failed"

	except Exception:
		depr_schedule.depr_entry_posting_status = "Save Failed"

	depr_schedule.save()


def update_asset_value_in_parent(parent, finance_book, decrease_in_value):
	for fb in parent.get("finance_books"):
		if fb.finance_book == finance_book:
			fb.asset_value -= decrease_in_value
			break

	parent.update_asset_value()


def get_schedules_that_failed_to_post_depr_entries():
	schedules_that_failed_posting = frappe.get_all(
		"Depreciation Schedule",
		filters={"depr_entry_posting_status": ["in", ["Submit Failed", "Save Failed"]]},
		pluck="name",
	)
	schedules_that_failed_posting = list(set(schedules_that_failed_posting))

	return schedules_that_failed_posting


def notify_accounts_managers(schedules_that_failed_posting):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	recipients = get_accounts_managers()

	schedule_names = ", ".join(schedules_that_failed_posting)
	schedule_links = get_schedule_links(schedules_that_failed_posting)
	notification_message = _(
		"The following Depreciation Schedules have failed to post Depreciation Entries: {0}"
	).format(schedule_links)

	notification_doc = {
		"type": "Alert",
		"document_type": "Depreciation Schedule",
		"document_name": schedule_names,
		"subject": notification_message,
		"from_user": frappe.session.user,
	}

	frappe.flags.in_test = True
	enqueue_create_notification(recipients, notification_doc)


def get_schedule_links(schedules_that_failed_posting):
	schedule_links = []

	for schedule in schedules_that_failed_posting:
		schedule_links.append(get_link_to_form("Depreciation Schedule", schedule))

	schedule_links = ", ".join(schedule_links)

	return schedule_links


def get_accounts_managers():
	return list(
		set(
			frappe.get_all(
				"Has Role", filters={"role": "Accounts Manager", "parenttype": "User"}, pluck="parent"
			)
		)
	)


def record_depreciation_posting(parent, depr_entry):
	from erpnext.assets.doctype.asset_activity.asset_activity import create_asset_activity
	from erpnext.assets.doctype.depreciation_schedule.depreciation_schedule import (
		get_asset_and_serial_no,
	)

	asset, serial_no = get_asset_and_serial_no(parent)

	create_asset_activity(
		asset=asset,
		asset_serial_no=serial_no,
		activity_type="Depreciation",
		activity_date=depr_entry.posting_date,
		reference_doctype=depr_entry.doctype,
		reference_docname=depr_entry.name,
		notes=_("{0} {1} depreciated by {2}.").format(
			parent.doctype, get_link_to_form(parent.doctype, parent.name), depr_entry.depreciation_amount
		),
	)


@frappe.whitelist()
def scrap_asset(asset_name, serial_no=None):
	docstatus, status, company = get_asset_values(asset_name, serial_no)
	doctype, docname = get_doctype_and_docname(asset_name, serial_no)

	validate_asset_or_serial_no(docstatus, status, doctype, docname)

	je = create_journal_entry(asset_name, serial_no, company, doctype, docname)
	update_asset_or_serial_no(doctype, docname, je.name)

	frappe.msgprint(
		_("{0} scrapped via Journal Entry {1}").format(docname, get_link_to_form(je.doctype, je.name))
	)


@frappe.whitelist()
def restore_asset(asset_name, serial_no=None):
	asset_doc = get_asset_doc(asset_name, serial_no)

	je = asset_doc.journal_entry_for_scrap

	asset_doc.db_set("disposal_date", None)
	asset_doc.db_set("journal_entry_for_scrap", None)

	frappe.get_doc("Journal Entry", je).cancel()

	asset_doc.set_status()


def get_asset_doc(asset_name, serial_no):
	if not serial_no:
		return frappe.get_doc("Asset", asset_name)
	else:
		return frappe.get_doc("Asset Serial No", serial_no)


def get_asset_values(asset_name, serial_no):
	if not serial_no:
		docstatus, status, company = frappe.get_value(
			"Asset", asset_name, ["docstatus", "status", "company"]
		)
	else:
		docstatus, status = frappe.get_value("Asset Serial No", serial_no, ["docstatus", "status"])
		company = frappe.get_value("Asset", asset_name, "company")

	return docstatus, status, company


def validate_asset_or_serial_no(docstatus, status, doctype, docname):
	if docstatus != 1:
		frappe.throw(_("{0} {1} must be submitted").format(doctype, docname))
	elif status in ("Cancelled", "Sold", "Scrapped"):
		frappe.throw(
			_("{0} {1} cannot be scrapped, as it is already {2}").format(doctype, docname, status)
		)


def get_doctype_and_docname(asset_name, serial_no):
	doctype = "Asset" if not serial_no else "Asset Serial No"
	docname = asset_name if not serial_no else serial_no

	return doctype, docname


def create_journal_entry(asset_name, serial_no, company, doctype, docname):
	depreciation_series = frappe.get_cached_value("Company", company, "series_for_depreciation_entry")

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.naming_series = depreciation_series
	je.posting_date = today()
	je.company = company
	je.remark = "Scrap Entry for {0} {1}".format(doctype, docname)

	for entry in get_gl_entries_on_asset_disposal(asset_name, serial_no):
		entry.update({"reference_type": doctype, "reference_name": docname})
		je.append("accounts", entry)

	je.flags.ignore_permissions = True
	je.submit()

	return je


def update_asset_or_serial_no(doctype, docname, journal_entry):
	frappe.db.set_value(
		doctype,
		docname,
		{"disposal_date": today(), "journal_entry_for_scrap": journal_entry, "status": "Scrapped"},
	)


def get_gl_entries_on_asset_disposal(asset, serial_no=None, selling_amount=0, finance_book=None):
	(
		fixed_asset_account,
		accumulated_depr_account,
		asset,
		depreciation_cost_center,
		accumulated_depr_amount,
		disposal_account,
		asset_value,
		gross_purchase_amount,
	) = get_asset_details(asset, serial_no, finance_book)

	gl_entries = [
		{
			"account": fixed_asset_account,
			"credit_in_account_currency": gross_purchase_amount,
			"credit": gross_purchase_amount,
			"cost_center": depreciation_cost_center,
		}
	]

	if accumulated_depr_amount:
		gl_entries.append(
			{
				"account": accumulated_depr_account,
				"debit_in_account_currency": accumulated_depr_amount,
				"debit": accumulated_depr_amount,
				"cost_center": depreciation_cost_center,
			}
		)

	profit_amount = flt(selling_amount) - flt(asset_value)
	if profit_amount:
		get_profit_gl_entries(profit_amount, gl_entries, disposal_account, depreciation_cost_center)

	return gl_entries


def get_gl_entries_on_asset_regain(asset, serial_no=None, selling_amount=0, finance_book=None):
	(
		fixed_asset_account,
		accumulated_depr_account,
		asset,
		depreciation_cost_center,
		accumulated_depr_amount,
		disposal_account,
		asset_value,
		gross_purchase_amount,
	) = get_asset_details(asset, serial_no, finance_book)

	gl_entries = [
		{
			"account": fixed_asset_account,
			"debit_in_account_currency": gross_purchase_amount,
			"debit": gross_purchase_amount,
			"cost_center": depreciation_cost_center,
		},
		{
			"account": accumulated_depr_account,
			"credit_in_account_currency": accumulated_depr_amount,
			"credit": accumulated_depr_amount,
			"cost_center": depreciation_cost_center,
		},
	]

	profit_amount = abs(flt(asset_value)) - abs(flt(selling_amount))
	if profit_amount:
		get_profit_gl_entries(profit_amount, gl_entries, disposal_account, depreciation_cost_center)

	return gl_entries


def get_asset_details(asset, serial_no=None, finance_book=None):
	from erpnext.assets.doctype.asset_revaluation.asset_revaluation import get_current_asset_value

	asset_category, company, cost_center, gross_purchase_amount = frappe.get_value(
		"Asset", asset, ["asset_category", "company", "cost_center", "gross_purchase_amount"]
	)

	fixed_asset_account, accumulated_depr_account = get_asset_accounts(asset_category, company)
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(company)
	depreciation_cost_center = cost_center or depreciation_cost_center

	asset_value = get_current_asset_value(asset, serial_no, finance_book)
	accumulated_depr_amount = flt(gross_purchase_amount) - flt(asset_value)

	return (
		fixed_asset_account,
		accumulated_depr_account,
		asset,
		depreciation_cost_center,
		accumulated_depr_amount,
		disposal_account,
		asset_value,
		gross_purchase_amount,
	)


def get_asset_accounts(asset_category, company):
	fixed_asset_account, accumulated_depr_account = frappe.db.get_value(
		"Asset Category Account",
		filters={"parent": asset_category, "company_name": company},
		fieldname=["fixed_asset_account", "accumulated_depreciation_account"],
	)

	if not accumulated_depr_account:
		accumulated_depr_account = frappe.get_cached_value(
			"Company", company, "accumulated_depreciation_account"
		)

	if not accumulated_depr_account or not fixed_asset_account:
		frappe.throw(
			_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}").format(
				asset_category, company
			)
		)

	return fixed_asset_account, accumulated_depr_account


@frappe.whitelist()
def get_disposal_account_and_cost_center(company):
	disposal_account, depreciation_cost_center = frappe.get_cached_value(
		"Company", company, ["disposal_account", "depreciation_cost_center"]
	)

	if not disposal_account:
		frappe.throw(
			_("Please set 'Gain/Loss Account on Asset Disposal' in Company {0}").format(company)
		)
	if not depreciation_cost_center:
		frappe.throw(_("Please set 'Asset Depreciation Cost Center' in Company {0}").format(company))

	return disposal_account, depreciation_cost_center


def get_profit_gl_entries(profit_amount, gl_entries, disposal_account, depreciation_cost_center):
	debit_or_credit = "debit" if profit_amount < 0 else "credit"
	gl_entries.append(
		{
			"account": disposal_account,
			"cost_center": depreciation_cost_center,
			debit_or_credit: abs(profit_amount),
			debit_or_credit + "_in_account_currency": abs(profit_amount),
		}
	)
