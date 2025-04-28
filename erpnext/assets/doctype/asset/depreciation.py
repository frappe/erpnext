# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Max, Min
from frappe.utils import (
	add_months,
	cint,
	flt,
	get_last_day,
	get_link_to_form,
	getdate,
	is_last_day_of_the_month,
	nowdate,
	today,
)
from frappe.utils.user import get_users_with_role

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.accounts.doctype.journal_entry.journal_entry import make_reverse_journal_entry
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
	get_asset_depr_schedule_name,
<<<<<<< HEAD
	get_temp_depr_schedule_doc,
	reschedule_depreciation,
=======
	get_temp_asset_depr_schedule_doc,
	make_new_active_asset_depr_schedules_and_cancel_current_ones,
>>>>>>> 7c4cf3e834 (Favicon.svg)
)


def post_depreciation_entries(date=None):
	# Return if automatic booking of asset depreciation is disabled
<<<<<<< HEAD
	if not cint(frappe.get_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically")):
		return

	date = date or today()
	book_depreciation_entries(date)


def book_depreciation_entries(date):
	# Process depreciation entries for all depreciable assets
	failed_assets, error_logs = [], []

	depreciable_assets_data = get_depreciable_assets_data(date)
	accounting_dimensions = get_checks_for_pl_and_bs_accounts()

	for data in depreciable_assets_data:
		(depr_schedule_name, asset_name, sch_start_idx, sch_end_idx) = data

		try:
			make_depreciation_entry(
				depr_schedule_name,
				date,
				sch_start_idx,
				sch_end_idx,
=======
	if not cint(
		frappe.db.get_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically")
	):
		return

	if not date:
		date = today()

	failed_asset_names = []
	error_log_names = []

	depreciable_asset_depr_schedules_data = get_depreciable_asset_depr_schedules_data(date)

	credit_and_debit_accounts_for_asset_category_and_company = {}
	depreciation_cost_center_and_depreciation_series_for_company = (
		get_depreciation_cost_center_and_depreciation_series_for_company()
	)

	accounting_dimensions = get_checks_for_pl_and_bs_accounts()

	for asset_depr_schedule_data in depreciable_asset_depr_schedules_data:
		(
			asset_depr_schedule_name,
			asset_name,
			asset_category,
			asset_company,
			sch_start_idx,
			sch_end_idx,
		) = asset_depr_schedule_data

		if (
			asset_category,
			asset_company,
		) not in credit_and_debit_accounts_for_asset_category_and_company:
			credit_and_debit_accounts_for_asset_category_and_company.update(
				{
					(
						asset_category,
						asset_company,
					): get_credit_and_debit_accounts_for_asset_category_and_company(
						asset_category, asset_company
					),
				}
			)

		try:
			make_depreciation_entry(
				asset_depr_schedule_name,
				date,
				sch_start_idx,
				sch_end_idx,
				credit_and_debit_accounts_for_asset_category_and_company[(asset_category, asset_company)],
				depreciation_cost_center_and_depreciation_series_for_company[asset_company],
>>>>>>> 7c4cf3e834 (Favicon.svg)
				accounting_dimensions,
			)

			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback()
<<<<<<< HEAD
			failed_assets.append(asset_name)
			error_log = frappe.log_error(e)
			error_logs.append(error_log.name)

	if failed_assets:
		set_depr_entry_posting_status_for_failed_assets(failed_assets)
		notify_depr_entry_posting_error(failed_assets, error_logs)
	frappe.db.commit()


def get_depreciable_assets_data(date):
=======
			failed_asset_names.append(asset_name)
			error_log = frappe.log_error(e)
			error_log_names.append(error_log.name)

	if failed_asset_names:
		set_depr_entry_posting_status_for_failed_assets(failed_asset_names)
		notify_depr_entry_posting_error(failed_asset_names, error_log_names)

	frappe.db.commit()


def get_depreciable_asset_depr_schedules_data(date):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	a = frappe.qb.DocType("Asset")
	ads = frappe.qb.DocType("Asset Depreciation Schedule")
	ds = frappe.qb.DocType("Depreciation Schedule")

	res = (
		frappe.qb.from_(ads)
		.join(a)
		.on(ads.asset == a.name)
		.join(ds)
		.on(ads.name == ds.parent)
<<<<<<< HEAD
		.select(ads.name, a.name, Min(ds.idx) - 1, Max(ds.idx))
=======
		.select(ads.name, a.name, a.asset_category, a.company, Min(ds.idx) - 1, Max(ds.idx))
>>>>>>> 7c4cf3e834 (Favicon.svg)
		.where(a.calculate_depreciation == 1)
		.where(a.docstatus == 1)
		.where(ads.docstatus == 1)
		.where(a.status.isin(["Submitted", "Partially Depreciated"]))
		.where(ds.journal_entry.isnull())
		.where(ds.schedule_date <= date)
		.groupby(ads.name)
		.orderby(a.creation, order=Order.desc)
	)

	acc_frozen_upto = get_acc_frozen_upto()
	if acc_frozen_upto:
		res = res.where(ds.schedule_date > acc_frozen_upto)

	res = res.run()

	return res


<<<<<<< HEAD
def make_depreciation_entry_on_disposal(asset_doc, disposal_date=None):
	for row in asset_doc.get("finance_books"):
		depr_schedule_name = get_asset_depr_schedule_name(asset_doc.name, "Active", row.finance_book)
		make_depreciation_entry(depr_schedule_name, disposal_date)


def get_acc_frozen_upto():
	acc_frozen_upto = frappe.get_single_value("Accounts Settings", "acc_frozen_upto")
=======
def make_depreciation_entry_for_all_asset_depr_schedules(asset_doc, date=None):
	for row in asset_doc.get("finance_books"):
		asset_depr_schedule_name = get_asset_depr_schedule_name(asset_doc.name, "Active", row.finance_book)
		make_depreciation_entry(asset_depr_schedule_name, date)


def get_acc_frozen_upto():
	acc_frozen_upto = frappe.db.get_single_value("Accounts Settings", "acc_frozen_upto")
>>>>>>> 7c4cf3e834 (Favicon.svg)

	if not acc_frozen_upto:
		return

<<<<<<< HEAD
	frozen_accounts_modifier = frappe.get_single_value("Accounts Settings", "frozen_accounts_modifier")
=======
	frozen_accounts_modifier = frappe.db.get_single_value("Accounts Settings", "frozen_accounts_modifier")
>>>>>>> 7c4cf3e834 (Favicon.svg)

	if frozen_accounts_modifier not in frappe.get_roles() or frappe.session.user == "Administrator":
		return getdate(acc_frozen_upto)

	return


<<<<<<< HEAD
def get_credit_debit_accounts_for_asset(asset_category, company):
	# Returns credit and debit accounts for the given asset category and company.
	(_, accumulated_depr_account, depr_expense_account) = get_depreciation_accounts(asset_category, company)

	credit_account, debit_account = get_credit_and_debit_accounts(
		accumulated_depr_account, depr_expense_account
=======
def get_credit_and_debit_accounts_for_asset_category_and_company(asset_category, company):
	(
		_,
		accumulated_depreciation_account,
		depreciation_expense_account,
	) = get_depreciation_accounts(asset_category, company)

	credit_account, debit_account = get_credit_and_debit_accounts(
		accumulated_depreciation_account, depreciation_expense_account
>>>>>>> 7c4cf3e834 (Favicon.svg)
	)

	return (credit_account, debit_account)


<<<<<<< HEAD
def get_depreciation_cost_center_and_series(asset):
	depreciation_cost_center, depreciation_series = frappe.get_cached_value(
		"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
	)
	depreciation_cost_center = asset.cost_center or depreciation_cost_center
	return depreciation_cost_center, depreciation_series


def get_depr_cost_center_and_series():
=======
def get_depreciation_cost_center_and_depreciation_series_for_company():
>>>>>>> 7c4cf3e834 (Favicon.svg)
	company_names = frappe.db.get_all("Company", pluck="name")

	res = {}

	for company_name in company_names:
		depreciation_cost_center, depreciation_series = frappe.get_cached_value(
			"Company", company_name, ["depreciation_cost_center", "series_for_depreciation_entry"]
		)
<<<<<<< HEAD
		res.setdefault(company_name, (depreciation_cost_center, depreciation_series))
=======
		res.update({company_name: (depreciation_cost_center, depreciation_series)})
>>>>>>> 7c4cf3e834 (Favicon.svg)

	return res


@frappe.whitelist()
def make_depreciation_entry(
<<<<<<< HEAD
	depr_schedule_name,
	date=None,
	sch_start_idx=None,
	sch_end_idx=None,
	accounting_dimensions=None,
):
	frappe.has_permission("Journal Entry", throw=True)
	date = date or today()

	depr_schedule_doc = frappe.get_doc("Asset Depreciation Schedule", depr_schedule_name)
	asset = frappe.get_doc("Asset", depr_schedule_doc.asset)

	credit_account, debit_account = get_credit_debit_accounts_for_asset(asset.asset_category, asset.company)
	depr_cost_center, depr_series = get_depreciation_cost_center_and_series(asset)
	accounting_dimensions = accounting_dimensions or get_checks_for_pl_and_bs_accounts()
	depr_posting_error = None

	for d in depr_schedule_doc.get("depreciation_schedule")[
		(sch_start_idx or 0) : (sch_end_idx or len(depr_schedule_doc.get("depreciation_schedule")))
	]:
		try:
			_make_journal_entry_for_depreciation(
				depr_schedule_doc,
=======
	asset_depr_schedule_name,
	date=None,
	sch_start_idx=None,
	sch_end_idx=None,
	credit_and_debit_accounts=None,
	depreciation_cost_center_and_depreciation_series=None,
	accounting_dimensions=None,
):
	frappe.has_permission("Journal Entry", throw=True)

	if not date:
		date = today()

	asset_depr_schedule_doc = frappe.get_doc("Asset Depreciation Schedule", asset_depr_schedule_name)

	asset = frappe.get_doc("Asset", asset_depr_schedule_doc.asset)

	if credit_and_debit_accounts:
		credit_account, debit_account = credit_and_debit_accounts
	else:
		credit_account, debit_account = get_credit_and_debit_accounts_for_asset_category_and_company(
			asset.asset_category, asset.company
		)

	if depreciation_cost_center_and_depreciation_series:
		depreciation_cost_center, depreciation_series = depreciation_cost_center_and_depreciation_series
	else:
		depreciation_cost_center, depreciation_series = frappe.get_cached_value(
			"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
		)

	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	if not accounting_dimensions:
		accounting_dimensions = get_checks_for_pl_and_bs_accounts()

	depreciation_posting_error = None

	for d in asset_depr_schedule_doc.get("depreciation_schedule")[
		sch_start_idx or 0 : sch_end_idx or len(asset_depr_schedule_doc.get("depreciation_schedule"))
	]:
		try:
			_make_journal_entry_for_depreciation(
				asset_depr_schedule_doc,
>>>>>>> 7c4cf3e834 (Favicon.svg)
				asset,
				date,
				d,
				sch_start_idx,
				sch_end_idx,
<<<<<<< HEAD
				depr_cost_center,
				depr_series,
=======
				depreciation_cost_center,
				depreciation_series,
>>>>>>> 7c4cf3e834 (Favicon.svg)
				credit_account,
				debit_account,
				accounting_dimensions,
			)
		except Exception as e:
<<<<<<< HEAD
			depr_posting_error = e

	asset.reload()
	asset.set_status()

	if not depr_posting_error:
		asset.db_set("depr_entry_posting_status", "Successful")
		depr_schedule_doc.reload()
		return depr_schedule_doc

	raise depr_posting_error


def _make_journal_entry_for_depreciation(
	depr_schedule_doc,
=======
			depreciation_posting_error = e

	asset.set_status()

	if not depreciation_posting_error:
		asset.db_set("depr_entry_posting_status", "Successful")
		return asset_depr_schedule_doc

	raise depreciation_posting_error


def _make_journal_entry_for_depreciation(
	asset_depr_schedule_doc,
>>>>>>> 7c4cf3e834 (Favicon.svg)
	asset,
	date,
	depr_schedule,
	sch_start_idx,
	sch_end_idx,
<<<<<<< HEAD
	depr_cost_center,
	depr_series,
=======
	depreciation_cost_center,
	depreciation_series,
>>>>>>> 7c4cf3e834 (Favicon.svg)
	credit_account,
	debit_account,
	accounting_dimensions,
):
	if not (sch_start_idx and sch_end_idx) and not (
		not depr_schedule.journal_entry and getdate(depr_schedule.schedule_date) <= getdate(date)
	):
		return

	je = frappe.new_doc("Journal Entry")
<<<<<<< HEAD
	setup_journal_entry_metadata(je, depr_schedule_doc, depr_series, depr_schedule, asset)

	credit_entry, debit_entry = get_credit_and_debit_entry(
		credit_account, depr_schedule, asset, depr_cost_center, debit_account, accounting_dimensions
	)

	je.append("accounts", credit_entry)
	je.append("accounts", debit_entry)

	je.flags.ignore_permissions = True
	je.save()

	if not je.meta.get_workflow():
		je.submit()


def setup_journal_entry_metadata(je, depr_schedule_doc, depr_series, depr_schedule, asset):
	je.voucher_type = "Depreciation Entry"
	je.naming_series = depr_series
	je.posting_date = depr_schedule.schedule_date
	je.company = asset.company
	je.finance_book = depr_schedule_doc.finance_book
	je.remark = _("Depreciation Entry against {0} worth {1}").format(
		asset.name, depr_schedule.depreciation_amount
	)


def get_credit_and_debit_entry(
	credit_account, depr_schedule, asset, depr_cost_center, debit_account, dimensions
):
=======
	je.voucher_type = "Depreciation Entry"
	je.naming_series = depreciation_series
	je.posting_date = depr_schedule.schedule_date
	je.company = asset.company
	je.finance_book = asset_depr_schedule_doc.finance_book
	je.remark = f"Depreciation Entry against {asset.name} worth {depr_schedule.depreciation_amount}"

>>>>>>> 7c4cf3e834 (Favicon.svg)
	credit_entry = {
		"account": credit_account,
		"credit_in_account_currency": depr_schedule.depreciation_amount,
		"reference_type": "Asset",
		"reference_name": asset.name,
<<<<<<< HEAD
		"cost_center": depr_cost_center,
=======
		"cost_center": depreciation_cost_center,
>>>>>>> 7c4cf3e834 (Favicon.svg)
	}

	debit_entry = {
		"account": debit_account,
		"debit_in_account_currency": depr_schedule.depreciation_amount,
		"reference_type": "Asset",
		"reference_name": asset.name,
<<<<<<< HEAD
		"cost_center": depr_cost_center,
	}

	for dimension in dimensions:
		if asset.get(dimension["fieldname"]) or dimension.get("mandatory_for_bs"):
			credit_entry[dimension["fieldname"]] = asset.get(dimension["fieldname"]) or dimension.get(
				"default_dimension"
			)

		if asset.get(dimension["fieldname"]) or dimension.get("mandatory_for_pl"):
			debit_entry[dimension["fieldname"]] = asset.get(dimension["fieldname"]) or dimension.get(
				"default_dimension"
			)
	return credit_entry, debit_entry
=======
		"cost_center": depreciation_cost_center,
	}

	for dimension in accounting_dimensions:
		if asset.get(dimension["fieldname"]) or dimension.get("mandatory_for_bs"):
			credit_entry.update(
				{
					dimension["fieldname"]: asset.get(dimension["fieldname"])
					or dimension.get("default_dimension")
				}
			)

		if asset.get(dimension["fieldname"]) or dimension.get("mandatory_for_pl"):
			debit_entry.update(
				{
					dimension["fieldname"]: asset.get(dimension["fieldname"])
					or dimension.get("default_dimension")
				}
			)

	je.append("accounts", credit_entry)
	je.append("accounts", debit_entry)

	je.flags.ignore_permissions = True
	je.flags.planned_depr_entry = True
	je.save()

	depr_schedule.db_set("journal_entry", je.name)

	if not je.meta.get_workflow():
		je.submit()
		asset.reload()
		idx = cint(asset_depr_schedule_doc.finance_book_id)
		row = asset.get("finance_books")[idx - 1]
		row.value_after_depreciation -= depr_schedule.depreciation_amount
		row.db_update()


def get_depreciation_accounts(asset_category, company):
	fixed_asset_account = accumulated_depreciation_account = depreciation_expense_account = None

	accounts = frappe.db.get_value(
		"Asset Category Account",
		filters={"parent": asset_category, "company_name": company},
		fieldname=[
			"fixed_asset_account",
			"accumulated_depreciation_account",
			"depreciation_expense_account",
		],
		as_dict=1,
	)

	if accounts:
		fixed_asset_account = accounts.fixed_asset_account
		accumulated_depreciation_account = accounts.accumulated_depreciation_account
		depreciation_expense_account = accounts.depreciation_expense_account

	if not accumulated_depreciation_account or not depreciation_expense_account:
		accounts = frappe.get_cached_value(
			"Company", company, ["accumulated_depreciation_account", "depreciation_expense_account"]
		)

		if not accumulated_depreciation_account:
			accumulated_depreciation_account = accounts[0]
		if not depreciation_expense_account:
			depreciation_expense_account = accounts[1]

	if not fixed_asset_account or not accumulated_depreciation_account or not depreciation_expense_account:
		frappe.throw(
			_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}").format(
				asset_category, company
			)
		)

	return fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account
>>>>>>> 7c4cf3e834 (Favicon.svg)


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


def set_depr_entry_posting_status_for_failed_assets(failed_asset_names):
	for asset_name in failed_asset_names:
		frappe.db.set_value("Asset", asset_name, "depr_entry_posting_status", "Failed")


def notify_depr_entry_posting_error(failed_asset_names, error_log_names):
	recipients = get_users_with_role("Accounts Manager")

	if not recipients:
		recipients = get_users_with_role("System Manager")

	subject = _("Error while posting depreciation entries")

	asset_links = get_comma_separated_links(failed_asset_names, "Asset")
	error_log_links = get_comma_separated_links(error_log_names, "Error Log")

<<<<<<< HEAD
	message = get_message_for_depr_entry_posting_error(asset_links, error_log_links)

	frappe.sendmail(recipients=recipients, subject=subject, message=message)


def get_comma_separated_links(names, doctype):
	links = []

	for name in names:
		links.append(get_link_to_form(doctype, name))

	links = ", ".join(links)

	return links


def get_message_for_depr_entry_posting_error(asset_links, error_log_links):
	return (
=======
	message = (
>>>>>>> 7c4cf3e834 (Favicon.svg)
		_("Hello,")
		+ "<br><br>"
		+ _("The following assets have failed to automatically post depreciation entries: {0}").format(
			asset_links
		)
		+ "."
		+ "<br><br>"
		+ _("Here are the error logs for the aforementioned failed depreciation entries: {0}").format(
			error_log_links
		)
		+ "."
		+ "<br><br>"
		+ _("Please share this email with your support team so that they can find and fix the issue.")
	)

<<<<<<< HEAD

@frappe.whitelist()
def scrap_asset(asset_name, scrap_date=None):
	asset = frappe.get_doc("Asset", asset_name)
	scrap_date = getdate(scrap_date) or getdate(today())
	asset.db_set("disposal_date", scrap_date)
	validate_asset_for_scrap(asset, scrap_date)

	depreciate_asset(asset, scrap_date, get_note_for_scrap(asset))
	asset.reload()

	create_journal_entry_for_scrap(asset, scrap_date)


def validate_asset_for_scrap(asset, scrap_date):
	if asset.docstatus != 1:
		frappe.throw(_("Asset {0} must be submitted").format(asset.name))
	elif asset.status in ("Cancelled", "Sold", "Scrapped", "Capitalized"):
		frappe.throw(_("Asset {0} cannot be scrapped, as it is already {1}").format(asset.name, asset.status))

	validate_scrap_date(asset, scrap_date)


def validate_scrap_date(asset, scrap_date):
	if scrap_date > getdate():
		frappe.throw(_("Future date is not allowed"))
	elif scrap_date < getdate(asset.purchase_date):
		frappe.throw(_("Scrap date cannot be before purchase date"))

	if asset.calculate_depreciation:
		last_booked_depreciation_date = get_last_depreciation_date(asset.name)
		if (
			last_booked_depreciation_date
			and scrap_date < last_booked_depreciation_date
			and scrap_date > getdate(asset.purchase_date)
		):
			frappe.throw(_("Asset cannot be scrapped before the last depreciation entry."))


def get_last_depreciation_date(asset_name):
	depreciation = frappe.qb.DocType("Asset Depreciation Schedule")
	depreciation_schedule = frappe.qb.DocType("Depreciation Schedule")

	last_depreciation_date = (
		frappe.qb.from_(depreciation)
		.join(depreciation_schedule)
		.on(depreciation.name == depreciation_schedule.parent)
		.select(depreciation_schedule.schedule_date)
		.where(depreciation.asset == asset_name)
		.where(depreciation.docstatus == 1)
		.where(depreciation_schedule.journal_entry != "")
		.orderby(depreciation_schedule.schedule_date, order=Order.desc)
		.limit(1)
		.run()
	)

	return last_depreciation_date[0][0] if last_depreciation_date else None


def get_note_for_scrap(asset):
	return _("This schedule was created when Asset {0} was scrapped.").format(
		get_link_to_form(asset.doctype, asset.name)
	)


def create_journal_entry_for_scrap(asset, scrap_date):
	depreciation_series = frappe.get_cached_value("Company", asset.company, "series_for_depreciation_entry")

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Asset Disposal"
	je.naming_series = depreciation_series
	je.posting_date = scrap_date
	je.company = asset.company
	je.remark = f"Scrap Entry for asset {asset.name}"

	for entry in get_gl_entries_on_asset_disposal(asset, scrap_date):
		entry.update({"reference_type": "Asset", "reference_name": asset.name})
		je.append("accounts", entry)

	je.flags.ignore_permissions = True
	je.save()
	if not je.meta.get_workflow():
		je.submit()

	add_asset_activity(asset.name, _("Asset scrapped"))
	frappe.msgprint(
		_("Asset scrapped via Journal Entry {0}").format(get_link_to_form("Journal Entry", je.name))
	)
=======
	frappe.sendmail(recipients=recipients, subject=subject, message=message)


def get_comma_separated_links(names, doctype):
	links = []

	for name in names:
		links.append(get_link_to_form(doctype, name))

	links = ", ".join(links)

	return links


@frappe.whitelist()
def scrap_asset(asset_name):
	asset = frappe.get_doc("Asset", asset_name)

	if asset.docstatus != 1:
		frappe.throw(_("Asset {0} must be submitted").format(asset.name))
	elif asset.status in ("Cancelled", "Sold", "Scrapped", "Capitalized", "Decapitalized"):
		frappe.throw(_("Asset {0} cannot be scrapped, as it is already {1}").format(asset.name, asset.status))

	date = today()

	notes = _("This schedule was created when Asset {0} was scrapped.").format(
		get_link_to_form(asset.doctype, asset.name)
	)

	depreciate_asset(asset, date, notes)
	asset.reload()

	depreciation_series = frappe.get_cached_value("Company", asset.company, "series_for_depreciation_entry")

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.naming_series = depreciation_series
	je.posting_date = date
	je.company = asset.company
	je.remark = f"Scrap Entry for asset {asset_name}"

	for entry in get_gl_entries_on_asset_disposal(asset, date):
		entry.update({"reference_type": "Asset", "reference_name": asset_name})
		je.append("accounts", entry)

	je.flags.ignore_permissions = True
	je.submit()

	frappe.db.set_value("Asset", asset_name, "disposal_date", date)
	frappe.db.set_value("Asset", asset_name, "journal_entry_for_scrap", je.name)
	asset.set_status("Scrapped")

	add_asset_activity(asset_name, _("Asset scrapped"))

	frappe.msgprint(_("Asset scrapped via Journal Entry {0}").format(je.name))
>>>>>>> 7c4cf3e834 (Favicon.svg)


@frappe.whitelist()
def restore_asset(asset_name):
	asset = frappe.get_doc("Asset", asset_name)
<<<<<<< HEAD
	reverse_depreciation_entry_made_on_disposal(asset)
	reset_depreciation_schedule(asset, get_note_for_restore(asset))
	cancel_journal_entry_for_scrap(asset)
	asset.set_status()
	add_asset_activity(asset_name, _("Asset restored"))


def get_note_for_restore(asset):
	return _("This schedule was created when Asset {0} was restored.").format(
		get_link_to_form(asset.doctype, asset.name)
	)


def cancel_journal_entry_for_scrap(asset):
	if asset.journal_entry_for_scrap:
		je = asset.journal_entry_for_scrap
		asset.db_set("disposal_date", None)
		asset.db_set("journal_entry_for_scrap", None)
		frappe.get_doc("Journal Entry", je).cancel()
=======

	reverse_depreciation_entry_made_after_disposal(asset, asset.disposal_date)

	je = asset.journal_entry_for_scrap

	notes = _("This schedule was created when Asset {0} was restored.").format(
		get_link_to_form(asset.doctype, asset.name)
	)

	reset_depreciation_schedule(asset, asset.disposal_date, notes)

	asset.db_set("disposal_date", None)
	asset.db_set("journal_entry_for_scrap", None)

	frappe.get_doc("Journal Entry", je).cancel()

	asset.set_status()

	add_asset_activity(asset_name, _("Asset restored"))
>>>>>>> 7c4cf3e834 (Favicon.svg)


def depreciate_asset(asset_doc, date, notes):
	if not asset_doc.calculate_depreciation:
		return

<<<<<<< HEAD
	reschedule_depreciation(asset_doc, notes, disposal_date=date)
	make_depreciation_entry_on_disposal(asset_doc, date)

	# As per Income Tax Act (India), the asset should not be depreciated
	# in the financial year in which it is sold/scraped
=======
	asset_doc.flags.ignore_validate_update_after_submit = True

	make_new_active_asset_depr_schedules_and_cancel_current_ones(asset_doc, notes, date_of_disposal=date)

	asset_doc.save()

	make_depreciation_entry_for_all_asset_depr_schedules(asset_doc, date)

>>>>>>> 7c4cf3e834 (Favicon.svg)
	asset_doc.reload()
	cancel_depreciation_entries(asset_doc, date)


@erpnext.allow_regional
def cancel_depreciation_entries(asset_doc, date):
<<<<<<< HEAD
	# Cancel all depreciation entries for the current financial year
	# if the asset is sold/scraped in the current financial year
	# Overwritten via India Compliance app
	pass


def reset_depreciation_schedule(asset_doc, notes):
	if asset_doc.calculate_depreciation:
		reschedule_depreciation(asset_doc, notes)
		asset_doc.set_total_booked_depreciations()


def reverse_depreciation_entry_made_on_disposal(asset):
	for row in asset.get("finance_books"):
		schedule_doc = get_asset_depr_schedule_doc(asset.name, "Active", row.finance_book)
		if not schedule_doc or not schedule_doc.get("depreciation_schedule"):
			continue

		for schedule_idx, schedule in enumerate(schedule_doc.get("depreciation_schedule")):
			if schedule.schedule_date == asset.disposal_date and schedule.journal_entry:
				if not disposal_was_made_on_original_schedule_date(
					schedule_idx, row, asset.disposal_date
				) or disposal_happens_in_the_future(asset.disposal_date):
					je = create_reverse_depreciation_entry(asset.name, schedule.journal_entry)
					update_value_after_depreciation_on_asset_restore(schedule, row, je)


def disposal_was_made_on_original_schedule_date(schedule_idx, row, disposal_date):
	"""
	If asset is scrapped or sold on original schedule date,
	then the depreciation entry should not be reversed.
	"""
	orginal_schedule_date = add_months(
		row.depreciation_start_date, schedule_idx * cint(row.frequency_of_depreciation)
	)

	if is_last_day_of_the_month(row.depreciation_start_date):
		orginal_schedule_date = get_last_day(orginal_schedule_date)

	if orginal_schedule_date == disposal_date:
		return True

	return False


def disposal_happens_in_the_future(disposal_date):
	if disposal_date > getdate():
		return True

	return False


def create_reverse_depreciation_entry(asset_name, journal_entry):
	reverse_journal_entry = make_reverse_journal_entry(journal_entry)
	reverse_journal_entry.posting_date = nowdate()

	for account in reverse_journal_entry.accounts:
		account.update(
			{
				"reference_type": "Asset",
				"reference_name": asset_name,
			}
		)

	frappe.flags.is_reverse_depr_entry = True
	if not reverse_journal_entry.meta.get_workflow():
		reverse_journal_entry.submit()
		return reverse_journal_entry
	else:
		frappe.throw(
			_("Please disable workflow temporarily for Journal Entry {0}").format(reverse_journal_entry.name)
		)


def update_value_after_depreciation_on_asset_restore(schedule, row, journal_entry):
	frappe.db.set_value("Depreciation Schedule", schedule.name, "journal_entry", None, update_modified=False)
	depreciation_amount = get_depreciation_amount_in_je(journal_entry)
	value_after_depreciation = flt(
		row.value_after_depreciation + depreciation_amount, row.precision("value_after_depreciation")
	)
	row.db_set("value_after_depreciation", value_after_depreciation)
=======
	pass


def reset_depreciation_schedule(asset_doc, date, notes):
	if not asset_doc.calculate_depreciation:
		return

	asset_doc.flags.ignore_validate_update_after_submit = True

	make_new_active_asset_depr_schedules_and_cancel_current_ones(asset_doc, notes, date_of_return=date)

	modify_depreciation_schedule_for_asset_repairs(asset_doc, notes)

	asset_doc.save()


def modify_depreciation_schedule_for_asset_repairs(asset, notes):
	asset_repairs = frappe.get_all(
		"Asset Repair", filters={"asset": asset.name}, fields=["name", "increase_in_asset_life"]
	)

	for repair in asset_repairs:
		if repair.increase_in_asset_life:
			asset_repair = frappe.get_doc("Asset Repair", repair.name)
			asset_repair.modify_depreciation_schedule()
			make_new_active_asset_depr_schedules_and_cancel_current_ones(asset, notes)


def reverse_depreciation_entry_made_after_disposal(asset, date):
	for row in asset.get("finance_books"):
		asset_depr_schedule_doc = get_asset_depr_schedule_doc(asset.name, "Active", row.finance_book)
		if not asset_depr_schedule_doc or not asset_depr_schedule_doc.get("depreciation_schedule"):
			continue

		for schedule_idx, schedule in enumerate(asset_depr_schedule_doc.get("depreciation_schedule")):
			if schedule.schedule_date == date and schedule.journal_entry:
				if not disposal_was_made_on_original_schedule_date(
					schedule_idx, row, date
				) or disposal_happens_in_the_future(date):
					reverse_journal_entry = make_reverse_journal_entry(schedule.journal_entry)
					reverse_journal_entry.posting_date = nowdate()

					for account in reverse_journal_entry.accounts:
						account.update(
							{
								"reference_type": "Asset",
								"reference_name": asset.name,
							}
						)

					frappe.flags.is_reverse_depr_entry = True
					reverse_journal_entry.submit()

					frappe.flags.is_reverse_depr_entry = False
					asset_depr_schedule_doc.flags.ignore_validate_update_after_submit = True
					asset.flags.ignore_validate_update_after_submit = True
					schedule.journal_entry = None
					depreciation_amount = get_depreciation_amount_in_je(reverse_journal_entry)
					row.value_after_depreciation += depreciation_amount
					asset_depr_schedule_doc.save()
					asset.save()
>>>>>>> 7c4cf3e834 (Favicon.svg)


def get_depreciation_amount_in_je(journal_entry):
	if journal_entry.accounts[0].debit_in_account_currency:
		return journal_entry.accounts[0].debit_in_account_currency
	else:
		return journal_entry.accounts[0].credit_in_account_currency


<<<<<<< HEAD
=======
# if the invoice had been posted on the date the depreciation was initially supposed to happen, the depreciation shouldn't be undone
def disposal_was_made_on_original_schedule_date(schedule_idx, row, posting_date_of_disposal):
	orginal_schedule_date = add_months(
		row.depreciation_start_date, schedule_idx * cint(row.frequency_of_depreciation)
	)

	if is_last_day_of_the_month(row.depreciation_start_date):
		orginal_schedule_date = get_last_day(orginal_schedule_date)

	if orginal_schedule_date == posting_date_of_disposal:
		return True

	return False


def disposal_happens_in_the_future(posting_date_of_disposal):
	if posting_date_of_disposal > getdate():
		return True

	return False


>>>>>>> 7c4cf3e834 (Favicon.svg)
def get_gl_entries_on_asset_regain(
	asset, selling_amount=0, finance_book=None, voucher_type=None, voucher_no=None, date=None
):
	if not date:
		date = getdate()

	(
		fixed_asset_account,
		asset,
		depreciation_cost_center,
		accumulated_depr_account,
		accumulated_depr_amount,
		disposal_account,
		value_after_depreciation,
	) = get_asset_details(asset, finance_book)

	gl_entries = [
		asset.get_gl_dict(
			{
				"account": fixed_asset_account,
<<<<<<< HEAD
				"debit_in_account_currency": asset.net_purchase_amount,
				"debit": asset.net_purchase_amount,
=======
				"debit_in_account_currency": asset.gross_purchase_amount,
				"debit": asset.gross_purchase_amount,
>>>>>>> 7c4cf3e834 (Favicon.svg)
				"cost_center": depreciation_cost_center,
				"posting_date": date,
			},
			item=asset,
		),
		asset.get_gl_dict(
			{
				"account": accumulated_depr_account,
				"credit_in_account_currency": accumulated_depr_amount,
				"credit": accumulated_depr_amount,
				"cost_center": depreciation_cost_center,
				"posting_date": date,
			},
			item=asset,
		),
	]

	profit_amount = abs(flt(value_after_depreciation)) - abs(flt(selling_amount))
	if profit_amount:
		get_profit_gl_entries(
			asset, profit_amount, gl_entries, disposal_account, depreciation_cost_center, date
		)

	if voucher_type and voucher_no:
		for entry in gl_entries:
			entry["voucher_type"] = voucher_type
			entry["voucher_no"] = voucher_no

	return gl_entries


def get_gl_entries_on_asset_disposal(
	asset, selling_amount=0, finance_book=None, voucher_type=None, voucher_no=None, date=None
):
	if not date:
		date = getdate()

	(
		fixed_asset_account,
		asset,
		depreciation_cost_center,
		accumulated_depr_account,
		accumulated_depr_amount,
		disposal_account,
		value_after_depreciation,
	) = get_asset_details(asset, finance_book)

	gl_entries = [
		asset.get_gl_dict(
			{
				"account": fixed_asset_account,
<<<<<<< HEAD
				"credit_in_account_currency": asset.net_purchase_amount,
				"credit": asset.net_purchase_amount,
=======
				"credit_in_account_currency": asset.gross_purchase_amount,
				"credit": asset.gross_purchase_amount,
>>>>>>> 7c4cf3e834 (Favicon.svg)
				"cost_center": depreciation_cost_center,
				"posting_date": date,
			},
			item=asset,
		),
	]

	if accumulated_depr_amount:
		gl_entries.append(
			asset.get_gl_dict(
				{
					"account": accumulated_depr_account,
					"debit_in_account_currency": accumulated_depr_amount,
					"debit": accumulated_depr_amount,
					"cost_center": depreciation_cost_center,
					"posting_date": date,
				},
				item=asset,
			),
		)

	profit_amount = flt(selling_amount) - flt(value_after_depreciation)
	if profit_amount:
		get_profit_gl_entries(
			asset, profit_amount, gl_entries, disposal_account, depreciation_cost_center, date
		)

	if voucher_type and voucher_no:
		for entry in gl_entries:
			entry["voucher_type"] = voucher_type
			entry["voucher_no"] = voucher_no

	return gl_entries


def get_asset_details(asset, finance_book=None):
<<<<<<< HEAD
	value_after_depreciation = asset.get_value_after_depreciation(finance_book)
	accumulated_depr_amount = flt(asset.net_purchase_amount) - flt(value_after_depreciation)

=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
	fixed_asset_account, accumulated_depr_account, _ = get_depreciation_accounts(
		asset.asset_category, asset.company
	)
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(asset.company)
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

<<<<<<< HEAD
=======
	value_after_depreciation = asset.get_value_after_depreciation(finance_book)

	accumulated_depr_amount = flt(asset.gross_purchase_amount) - flt(value_after_depreciation)

>>>>>>> 7c4cf3e834 (Favicon.svg)
	return (
		fixed_asset_account,
		asset,
		depreciation_cost_center,
		accumulated_depr_account,
		accumulated_depr_amount,
		disposal_account,
		value_after_depreciation,
	)


<<<<<<< HEAD
def get_depreciation_accounts(asset_category, company):
	fixed_asset_account = accumulated_depreciation_account = depreciation_expense_account = None

	non_depreciable_category = frappe.db.get_value(
		"Asset Category", asset_category, "non_depreciable_category"
	)

	accounts = frappe.db.get_value(
		"Asset Category Account",
		filters={"parent": asset_category, "company_name": company},
		fieldname=[
			"fixed_asset_account",
			"accumulated_depreciation_account",
			"depreciation_expense_account",
		],
		as_dict=1,
	)

	if accounts:
		fixed_asset_account = accounts.fixed_asset_account
		accumulated_depreciation_account = accounts.accumulated_depreciation_account
		depreciation_expense_account = accounts.depreciation_expense_account

	if not fixed_asset_account:
		frappe.throw(_("Please set Fixed Asset Account in Asset Category {0}").format(asset_category))

	if not non_depreciable_category:
		accounts = frappe.get_cached_value(
			"Company", company, ["accumulated_depreciation_account", "depreciation_expense_account"]
		)

		if not accumulated_depreciation_account:
			accumulated_depreciation_account = accounts[0]
		if not depreciation_expense_account:
			depreciation_expense_account = accounts[1]

		if not accumulated_depreciation_account or not depreciation_expense_account:
			frappe.throw(
				_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}").format(
					asset_category, company
				)
			)

	return fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account


=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
def get_profit_gl_entries(
	asset, profit_amount, gl_entries, disposal_account, depreciation_cost_center, date=None
):
	if not date:
		date = getdate()

	debit_or_credit = "debit" if profit_amount < 0 else "credit"
	gl_entries.append(
		asset.get_gl_dict(
			{
				"account": disposal_account,
				"cost_center": depreciation_cost_center,
				debit_or_credit: abs(profit_amount),
				debit_or_credit + "_in_account_currency": abs(profit_amount),
				"posting_date": date,
			},
			item=asset,
		)
	)


@frappe.whitelist()
def get_disposal_account_and_cost_center(company):
	disposal_account, depreciation_cost_center = frappe.get_cached_value(
		"Company", company, ["disposal_account", "depreciation_cost_center"]
	)

	if not disposal_account:
		frappe.throw(_("Please set 'Gain/Loss Account on Asset Disposal' in Company {0}").format(company))
	if not depreciation_cost_center:
		frappe.throw(_("Please set 'Asset Depreciation Cost Center' in Company {0}").format(company))

	return disposal_account, depreciation_cost_center


@frappe.whitelist()
def get_value_after_depreciation_on_disposal_date(asset, disposal_date, finance_book=None):
	asset_doc = frappe.get_doc("Asset", asset)

<<<<<<< HEAD
	if asset_doc.is_composite_component:
		validate_disposal_date(asset_doc.purchase_date, getdate(disposal_date), "purchase")
		return flt(asset_doc.value_after_depreciation)

	validate_disposal_date(asset_doc.available_for_use_date, getdate(disposal_date), "available for use")

	if asset_doc.available_for_use_date == getdate(disposal_date):
		return flt(asset_doc.net_purchase_amount - asset_doc.opening_accumulated_depreciation)
=======
	if asset_doc.available_for_use_date > getdate(disposal_date):
		frappe.throw(
			"Disposal date {} cannot be before available for use date {} of the asset.".format(
				disposal_date, asset_doc.available_for_use_date
			)
		)
	elif asset_doc.available_for_use_date == getdate(disposal_date):
		return flt(asset_doc.gross_purchase_amount - asset_doc.opening_accumulated_depreciation)
>>>>>>> 7c4cf3e834 (Favicon.svg)

	if not asset_doc.calculate_depreciation:
		return flt(asset_doc.value_after_depreciation)

	idx = 1
	if finance_book:
<<<<<<< HEAD
		for d in asset_doc.finance_books:
=======
		for d in asset.finance_books:
>>>>>>> 7c4cf3e834 (Favicon.svg)
			if d.finance_book == finance_book:
				idx = d.idx
				break

	row = asset_doc.finance_books[idx - 1]

<<<<<<< HEAD
	temp_asset_depreciation_schedule = get_temp_depr_schedule_doc(asset_doc, row, getdate(disposal_date))
=======
	temp_asset_depreciation_schedule = get_temp_asset_depr_schedule_doc(
		asset_doc, row, getdate(disposal_date)
	)
>>>>>>> 7c4cf3e834 (Favicon.svg)

	accumulated_depr_amount = temp_asset_depreciation_schedule.get("depreciation_schedule")[
		-1
	].accumulated_depreciation_amount

	return flt(
<<<<<<< HEAD
		flt(asset_doc.net_purchase_amount) - accumulated_depr_amount,
		asset_doc.precision("net_purchase_amount"),
	)


def validate_disposal_date(reference_date, disposal_date, label):
	if reference_date > disposal_date:
		frappe.throw(
			_("Disposal date {0} cannot be before {1} date {2} of the asset.").format(
				disposal_date, label, reference_date
			)
		)
=======
		flt(asset_doc.gross_purchase_amount) - accumulated_depr_amount,
		asset_doc.precision("gross_purchase_amount"),
	)
>>>>>>> 7c4cf3e834 (Favicon.svg)
