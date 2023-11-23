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
	get_first_day,
	get_last_day,
	getdate,
	nowdate,
	today,
)
from frappe.utils.data import get_link_to_form
from frappe.utils.user import get_users_with_role

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.accounts.doctype.journal_entry.journal_entry import make_reverse_journal_entry


def post_depreciation_entries(date=None):
	# Return if automatic booking of asset depreciation is disabled
	if not cint(
		frappe.db.get_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically")
	):
		return

	if not date:
		date = today()

	failed_asset_names = []
	error_log_names = []

	depreciable_assets = get_depreciable_assets(date)

	credit_and_debit_accounts_for_asset_category_and_company = {}
	depreciation_cost_center_and_depreciation_series_for_company = (
		get_depreciation_cost_center_and_depreciation_series_for_company()
	)

	accounting_dimensions = get_checks_for_pl_and_bs_accounts()

	for asset in depreciable_assets:
		asset_name, asset_category, asset_company, sch_start_idx, sch_end_idx = asset

		if (
			asset_category,
			asset_company,
		) not in credit_and_debit_accounts_for_asset_category_and_company:
			credit_and_debit_accounts_for_asset_category_and_company.update(
				{
					(asset_category, asset_company): get_credit_and_debit_accounts_for_asset_category_and_company(
						asset_category, asset_company
					),
				}
			)

		try:
			make_depreciation_entry(
				asset_name,
				date,
				sch_start_idx,
				sch_end_idx,
				credit_and_debit_accounts_for_asset_category_and_company[(asset_category, asset_company)],
				depreciation_cost_center_and_depreciation_series_for_company[asset_company],
				accounting_dimensions,
			)
			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback()
			failed_asset_names.append(asset_name)
			error_log = frappe.log_error(e)
			error_log_names.append(error_log.name)

	if failed_asset_names:
		set_depr_entry_posting_status_for_failed_assets(failed_asset_names)
		notify_depr_entry_posting_error(failed_asset_names, error_log_names)

	frappe.db.commit()


def get_depreciable_assets(date):
	a = frappe.qb.DocType("Asset")
	ds = frappe.qb.DocType("Depreciation Schedule")

	res = (
		frappe.qb.from_(a)
		.join(ds)
		.on(a.name == ds.parent)
		.select(a.name, a.asset_category, a.company, Min(ds.idx) - 1, Max(ds.idx))
		.where(a.calculate_depreciation == 1)
		.where(a.docstatus == 1)
		.where(a.status.isin(["Submitted", "Partially Depreciated"]))
		.where(ds.journal_entry.isnull())
		.where(ds.schedule_date <= date)
		.groupby(a.name)
		.orderby(a.creation, order=Order.desc)
	)

	acc_frozen_upto = get_acc_frozen_upto()
	if acc_frozen_upto:
		res = res.where(ds.schedule_date > acc_frozen_upto)

	res = res.run()

	return res


def get_acc_frozen_upto():
	acc_frozen_upto = frappe.db.get_single_value("Accounts Settings", "acc_frozen_upto")

	if not acc_frozen_upto:
		return

	frozen_accounts_modifier = frappe.db.get_single_value(
		"Accounts Settings", "frozen_accounts_modifier"
	)

	if frozen_accounts_modifier not in frappe.get_roles() or frappe.session.user == "Administrator":
		return getdate(acc_frozen_upto)

	return


def get_credit_and_debit_accounts_for_asset_category_and_company(asset_category, company):
	(
		_,
		accumulated_depreciation_account,
		depreciation_expense_account,
	) = get_depreciation_accounts(asset_category, company)

	credit_account, debit_account = get_credit_and_debit_accounts(
		accumulated_depreciation_account, depreciation_expense_account
	)

	return (credit_account, debit_account)


def get_depreciation_cost_center_and_depreciation_series_for_company():
	company_names = frappe.db.get_all("Company", pluck="name")

	res = {}

	for company_name in company_names:
		depreciation_cost_center, depreciation_series = frappe.get_cached_value(
			"Company", company_name, ["depreciation_cost_center", "series_for_depreciation_entry"]
		)
		res.update({company_name: (depreciation_cost_center, depreciation_series)})

	return res


@frappe.whitelist()
def make_depreciation_entry(
	asset_name,
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

	asset = frappe.get_doc("Asset", asset_name)

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

	for d in asset.get("schedules")[sch_start_idx or 0 : sch_end_idx or len(asset.get("schedules"))]:
		try:
			_make_journal_entry_for_depreciation(
				asset,
				date,
				d,
				sch_start_idx,
				sch_end_idx,
				depreciation_cost_center,
				depreciation_series,
				credit_account,
				debit_account,
				accounting_dimensions,
			)
			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback()
			depreciation_posting_error = e

	asset.set_status()

	if not depreciation_posting_error:
		asset.db_set("depr_entry_posting_status", "Successful")
		return asset

	raise depreciation_posting_error


def _make_journal_entry_for_depreciation(
	asset,
	date,
	depr_schedule,
	sch_start_idx,
	sch_end_idx,
	depreciation_cost_center,
	depreciation_series,
	credit_account,
	debit_account,
	accounting_dimensions,
):
	if not (sch_start_idx and sch_end_idx) and not (
		not depr_schedule.journal_entry and getdate(depr_schedule.schedule_date) <= getdate(date)
	):
		return

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Depreciation Entry"
	je.naming_series = depreciation_series
	je.posting_date = depr_schedule.schedule_date
	je.company = asset.company
	je.finance_book = depr_schedule.finance_book
	je.remark = "Depreciation Entry against {0} worth {1}".format(
		asset.name, depr_schedule.depreciation_amount
	)

	credit_entry = {
		"account": credit_account,
		"credit_in_account_currency": depr_schedule.depreciation_amount,
		"reference_type": "Asset",
		"reference_name": asset.name,
		"cost_center": depreciation_cost_center,
	}

	debit_entry = {
		"account": debit_account,
		"debit_in_account_currency": depr_schedule.depreciation_amount,
		"reference_type": "Asset",
		"reference_name": asset.name,
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
		idx = cint(depr_schedule.finance_book_id)
		finance_books = asset.get("finance_books")[idx - 1]
		finance_books.value_after_depreciation -= depr_schedule.depreciation_amount
		finance_books.db_update()


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

	if (
		not fixed_asset_account
		or not accumulated_depreciation_account
		or not depreciation_expense_account
	):
		frappe.throw(
			_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}").format(
				asset_category, company
			)
		)

	return fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account


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

	message = (
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
		frappe.throw(
			_("Asset {0} cannot be scrapped, as it is already {1}").format(asset.name, asset.status)
		)

	date = today()

	depreciate_asset(asset, date)
	asset.reload()

	depreciation_series = frappe.get_cached_value(
		"Company", asset.company, "series_for_depreciation_entry"
	)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.naming_series = depreciation_series
	je.posting_date = date
	je.company = asset.company
	je.remark = "Scrap Entry for asset {0}".format(asset_name)

	for entry in get_gl_entries_on_asset_disposal(asset, date):
		entry.update({"reference_type": "Asset", "reference_name": asset_name})
		je.append("accounts", entry)

	je.flags.ignore_permissions = True
	je.submit()

	frappe.db.set_value("Asset", asset_name, "disposal_date", date)
	frappe.db.set_value("Asset", asset_name, "journal_entry_for_scrap", je.name)
	asset.set_status("Scrapped")

	frappe.msgprint(_("Asset scrapped via Journal Entry {0}").format(je.name))


@frappe.whitelist()
def restore_asset(asset_name):
	asset = frappe.get_doc("Asset", asset_name)

	reverse_depreciation_entry_made_after_disposal(asset, asset.disposal_date)
	reset_depreciation_schedule(asset, asset.disposal_date)

	je = asset.journal_entry_for_scrap

	asset.db_set("disposal_date", None)
	asset.db_set("journal_entry_for_scrap", None)

	frappe.get_doc("Journal Entry", je).cancel()

	asset.set_status()


def depreciate_asset(asset, date):
	if not asset.calculate_depreciation:
		return

	asset.flags.ignore_validate_update_after_submit = True
	asset.prepare_depreciation_data(date_of_disposal=date)
	asset.save()

	make_depreciation_entry(asset.name, date)


def reset_depreciation_schedule(asset, date):
	if not asset.calculate_depreciation:
		return

	asset.flags.ignore_validate_update_after_submit = True

	# recreate original depreciation schedule of the asset
	asset.prepare_depreciation_data(date_of_return=date)

	modify_depreciation_schedule_for_asset_repairs(asset)
	asset.save()


def modify_depreciation_schedule_for_asset_repairs(asset):
	asset_repairs = frappe.get_all(
		"Asset Repair", filters={"asset": asset.name}, fields=["name", "increase_in_asset_life"]
	)

	for repair in asset_repairs:
		if repair.increase_in_asset_life:
			asset_repair = frappe.get_doc("Asset Repair", repair.name)
			asset_repair.modify_depreciation_schedule()
			asset.prepare_depreciation_data()


def reverse_depreciation_entry_made_after_disposal(asset, date):
	if not asset.calculate_depreciation:
		return

	row = -1
	finance_book = asset.get("schedules")[0].get("finance_book")
	for schedule in asset.get("schedules"):
		if schedule.finance_book != finance_book:
			row = 0
			finance_book = schedule.finance_book
		else:
			row += 1

		if schedule.schedule_date == date:
			if not disposal_was_made_on_original_schedule_date(
				asset, schedule, row, date
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
				asset.flags.ignore_validate_update_after_submit = True
				schedule.journal_entry = None
				depreciation_amount = get_depreciation_amount_in_je(reverse_journal_entry)

				idx = cint(schedule.finance_book_id)
				asset.finance_books[idx - 1].value_after_depreciation += depreciation_amount

				asset.save()


def get_depreciation_amount_in_je(journal_entry):
	if journal_entry.accounts[0].debit_in_account_currency:
		return journal_entry.accounts[0].debit_in_account_currency
	else:
		return journal_entry.accounts[0].credit_in_account_currency


# if the invoice had been posted on the date the depreciation was initially supposed to happen, the depreciation shouldn't be undone
def disposal_was_made_on_original_schedule_date(asset, schedule, row, posting_date_of_disposal):
	for finance_book in asset.get("finance_books"):
		if schedule.finance_book == finance_book.finance_book:
			orginal_schedule_date = add_months(
				finance_book.depreciation_start_date, row * cint(finance_book.frequency_of_depreciation)
			)

			if is_last_day_of_the_month(finance_book.depreciation_start_date):
				orginal_schedule_date = get_last_day(orginal_schedule_date)

			if orginal_schedule_date == posting_date_of_disposal:
				return True
	return False


def disposal_happens_in_the_future(posting_date_of_disposal):
	if posting_date_of_disposal > getdate():
		return True

	return False


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
				"debit_in_account_currency": asset.gross_purchase_amount,
				"debit": asset.gross_purchase_amount,
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
				"credit_in_account_currency": asset.gross_purchase_amount,
				"credit": asset.gross_purchase_amount,
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
	fixed_asset_account, accumulated_depr_account, _ = get_depreciation_accounts(
		asset.asset_category, asset.company
	)
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(asset.company)
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	value_after_depreciation = asset.get_value_after_depreciation(finance_book)

	accumulated_depr_amount = flt(asset.gross_purchase_amount) - flt(value_after_depreciation)

	return (
		fixed_asset_account,
		asset,
		depreciation_cost_center,
		accumulated_depr_account,
		accumulated_depr_amount,
		disposal_account,
		value_after_depreciation,
	)


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
		frappe.throw(
			_("Please set 'Gain/Loss Account on Asset Disposal' in Company {0}").format(company)
		)
	if not depreciation_cost_center:
		frappe.throw(_("Please set 'Asset Depreciation Cost Center' in Company {0}").format(company))

	return disposal_account, depreciation_cost_center


@frappe.whitelist()
def get_value_after_depreciation_on_disposal_date(asset, disposal_date, finance_book=None):
	asset_doc = frappe.get_doc("Asset", asset)

	if asset_doc.available_for_use_date > getdate(disposal_date):
		frappe.throw(
			"Disposal date {0} cannot be before available for use date {1} of the asset.".format(
				disposal_date, asset_doc.available_for_use_date
			)
		)
	elif asset_doc.available_for_use_date == getdate(disposal_date):
		return flt(asset_doc.gross_purchase_amount - asset_doc.opening_accumulated_depreciation)

	if asset_doc.calculate_depreciation:
		asset_doc.prepare_depreciation_data(getdate(disposal_date))

		finance_book_id = 1
		if finance_book:
			for fb in asset_doc.finance_books:
				if fb.finance_book == finance_book:
					finance_book_id = fb.idx
					break

		asset_schedules = [
			sch for sch in asset_doc.schedules if cint(sch.finance_book_id) == finance_book_id
		]
		accumulated_depr_amount = asset_schedules[-1].accumulated_depreciation_amount

		return flt(
			flt(asset_doc.gross_purchase_amount) - accumulated_depr_amount,
			asset_doc.precision("gross_purchase_amount"),
		)
	else:
		return flt(asset_doc.value_after_depreciation)


def is_last_day_of_the_month(date):
	last_day_of_the_month = get_last_day(date)

	return getdate(last_day_of_the_month) == getdate(date)


def is_first_day_of_the_month(date):
	first_day_of_the_month = get_first_day(date)

	return getdate(first_day_of_the_month) == getdate(date)
