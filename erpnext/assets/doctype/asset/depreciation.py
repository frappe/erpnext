# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_months, cint, flt, get_last_day, getdate, nowdate, today
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

	for asset_name in get_depreciable_assets(date):
		try:
			make_depreciation_entry(asset_name, date)
			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback()
			failed_asset_names.append(asset_name)

	if failed_asset_names:
		set_depr_entry_posting_status_for_failed_assets(failed_asset_names)
		notify_depr_entry_posting_error(failed_asset_names)

	frappe.db.commit()


def get_depreciable_assets(date):
	return frappe.db.sql_list(
		"""select distinct a.name
		from tabAsset a, `tabDepreciation Schedule` ds
		where a.name = ds.parent and a.docstatus=1 and ds.schedule_date<=%s and a.calculate_depreciation = 1
			and a.status in ('Submitted', 'Partially Depreciated')
			and ifnull(ds.journal_entry, '')=''""",
		date,
	)


@frappe.whitelist()
def make_depreciation_entry(asset_name, date=None):
	frappe.has_permission("Journal Entry", throw=True)

	if not date:
		date = today()

	asset = frappe.get_doc("Asset", asset_name)
	(
		fixed_asset_account,
		accumulated_depreciation_account,
		depreciation_expense_account,
	) = get_depreciation_accounts(asset)

	depreciation_cost_center, depreciation_series = frappe.get_cached_value(
		"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
	)

	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	accounting_dimensions = get_checks_for_pl_and_bs_accounts()

	for d in asset.get("schedules"):
		if not d.journal_entry and getdate(d.schedule_date) <= getdate(date):
			je = frappe.new_doc("Journal Entry")
			je.voucher_type = "Depreciation Entry"
			je.naming_series = depreciation_series
			je.posting_date = d.schedule_date
			je.company = asset.company
			je.finance_book = d.finance_book
			je.remark = "Depreciation Entry against {0} worth {1}".format(asset_name, d.depreciation_amount)

			credit_account, debit_account = get_credit_and_debit_accounts(
				accumulated_depreciation_account, depreciation_expense_account
			)

			credit_entry = {
				"account": credit_account,
				"credit_in_account_currency": d.depreciation_amount,
				"reference_type": "Asset",
				"reference_name": asset.name,
				"cost_center": depreciation_cost_center,
			}

			debit_entry = {
				"account": debit_account,
				"debit_in_account_currency": d.depreciation_amount,
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
			je.save()
			if not je.meta.get_workflow():
				je.submit()

			d.db_set("journal_entry", je.name)

			idx = cint(d.finance_book_id)
			finance_books = asset.get("finance_books")[idx - 1]
			finance_books.value_after_depreciation -= d.depreciation_amount
			finance_books.db_update()

	frappe.db.set_value("Asset", asset_name, "depr_entry_posting_status", "Successful")

	asset.set_status()

	return asset


def get_depreciation_accounts(asset):
	fixed_asset_account = accumulated_depreciation_account = depreciation_expense_account = None

	accounts = frappe.db.get_value(
		"Asset Category Account",
		filters={"parent": asset.asset_category, "company_name": asset.company},
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
			"Company", asset.company, ["accumulated_depreciation_account", "depreciation_expense_account"]
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
				asset.asset_category, asset.company
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


def notify_depr_entry_posting_error(failed_asset_names):
	recipients = get_users_with_role("Accounts Manager")

	if not recipients:
		recipients = get_users_with_role("System Manager")

	subject = _("Error while posting depreciation entries")

	asset_links = get_comma_separated_asset_links(failed_asset_names)

	message = (
		_("Hi,")
		+ "<br>"
		+ _("The following assets have failed to post depreciation entries: {0}").format(asset_links)
		+ "."
	)

	frappe.sendmail(recipients=recipients, subject=subject, message=message)


def get_comma_separated_asset_links(asset_names):
	asset_links = []

	for asset_name in asset_names:
		asset_links.append(get_link_to_form("Asset", asset_name))

	asset_links = ", ".join(asset_links)

	return asset_links


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

	for entry in get_gl_entries_on_asset_disposal(asset):
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
	asset.flags.ignore_validate_update_after_submit = True
	asset.prepare_depreciation_data(date_of_disposal=date)
	asset.save()

	make_depreciation_entry(asset.name, date)


def reset_depreciation_schedule(asset, date):
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
	asset, selling_amount=0, finance_book=None, voucher_type=None, voucher_no=None
):
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
				"posting_date": getdate(),
			},
			item=asset,
		),
		asset.get_gl_dict(
			{
				"account": accumulated_depr_account,
				"credit_in_account_currency": accumulated_depr_amount,
				"credit": accumulated_depr_amount,
				"cost_center": depreciation_cost_center,
				"posting_date": getdate(),
			},
			item=asset,
		),
	]

	profit_amount = abs(flt(value_after_depreciation)) - abs(flt(selling_amount))
	if profit_amount:
		get_profit_gl_entries(
			asset, profit_amount, gl_entries, disposal_account, depreciation_cost_center
		)

	if voucher_type and voucher_no:
		for entry in gl_entries:
			entry["voucher_type"] = voucher_type
			entry["voucher_no"] = voucher_no

	return gl_entries


def get_gl_entries_on_asset_disposal(
	asset, selling_amount=0, finance_book=None, voucher_type=None, voucher_no=None
):
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
				"posting_date": getdate(),
			},
			item=asset,
		),
		asset.get_gl_dict(
			{
				"account": accumulated_depr_account,
				"debit_in_account_currency": accumulated_depr_amount,
				"debit": accumulated_depr_amount,
				"cost_center": depreciation_cost_center,
				"posting_date": getdate(),
			},
			item=asset,
		),
	]

	profit_amount = flt(selling_amount) - flt(value_after_depreciation)
	if profit_amount:
		get_profit_gl_entries(
			asset, profit_amount, gl_entries, disposal_account, depreciation_cost_center
		)

	if voucher_type and voucher_no:
		for entry in gl_entries:
			entry["voucher_type"] = voucher_type
			entry["voucher_no"] = voucher_no

	return gl_entries


def get_asset_details(asset, finance_book=None):
	fixed_asset_account, accumulated_depr_account, depr_expense_account = get_depreciation_accounts(
		asset
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
	asset, profit_amount, gl_entries, disposal_account, depreciation_cost_center
):
	debit_or_credit = "debit" if profit_amount < 0 else "credit"
	gl_entries.append(
		asset.get_gl_dict(
			{
				"account": disposal_account,
				"cost_center": depreciation_cost_center,
				debit_or_credit: abs(profit_amount),
				debit_or_credit + "_in_account_currency": abs(profit_amount),
				"posting_date": getdate(),
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
