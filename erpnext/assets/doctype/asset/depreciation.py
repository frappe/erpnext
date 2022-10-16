# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today, date_diff, nowdate
from frappe.utils.data import get_first_day, get_last_day, add_years
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)


def post_depreciation_entries(date=None):
	# Return if automatic booking of asset depreciation is disabled
	if not cint(
		frappe.db.get_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically")
	):
		return

	if not date:
		date = today()
	for asset in get_depreciable_assets(date):
		make_depreciation_entry(asset, date)
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
	branch = asset.branch
	for d in asset.get("schedules"):
		if not d.journal_entry and getdate(d.schedule_date) <= getdate(date):
			je = frappe.new_doc("Journal Entry")
			je.voucher_type 	= "Depreciation Entry"
			je.naming_series 	= depreciation_series
			je.posting_date	 	= d.schedule_date
			je.company 			= asset.company
			je.finance_book 	= d.finance_book
			je.remark 			= "Depreciation Entry against {0} worth {1}".format(asset_name, d.depreciation_amount)
			je.branch 			= branch
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


@frappe.whitelist()
def reset_asset_value_for_scrap_sales(asset_name, posting_date):
	asset = frappe.get_doc("Asset", asset_name)
	if frappe.db.get_value("Company", asset.company, "reset_asset_value"):
		reverse_start_date = frappe.defaults.get_user_default("year_start_date")
	else:
		if date_diff(posting_date, nowdate()) > 1 and not frappe.db.get_value("Company", asset.company, "allow_back_date_scrapping"):
			frappe.throw(_("Asset scrapping and sales is not allowed for back dates {0}. Scrapping date should be {1}").format(posting_date, getdate(now())))

		reverse_start_date = posting_date

	if getdate(posting_date) < getdate(frappe.defaults.get_user_default("year_start_date")):
		frappe.throw(_("Asset Sales and Scrap date should be within the current fiscal year"))
	
	schedules = frappe.db.sql('''SELECT name, journal_entry, depreciation_amount 
								FROM `tabDepreciation Schedule` 
								WHERE parent = %s 
								AND schedule_date BETWEEN %s AND %s 
								AND (journal_entry !='' or journal_entry is NOT NULL)''',
									( asset_name, reverse_start_date, today()), as_dict=True)
	accounts = frappe.db.sql("""
					SELECT 
						depreciation_expense_account, 
						accumulated_depreciation_account 
					FROM 
						`tabAsset Category Account`
					WHERE 
						parent = '{}'
					""".format(asset.asset_category), as_dict = 1)
	if schedules:
		total_amount = 0.00
		for i in schedules:
			total_amount += flt(i.depreciation_amount)
			frappe.db.set_value("Depreciation Schedule", i.name, "journal_entry", None)

			je = frappe.new_doc("Journal Entry")
			je.voucher_type = "Depreciation Entry"
			je.posting_date = posting_date 
			je.company = asset.company
			je.branch = asset.branch
			je.remark = "Scrap Entry for asset {0}".format(asset_name)
			entry_cred = {
				"reference_name" : asset_name,
				"reference_type" : "Asset",
				"account" : accounts[0].depreciation_expense_account,
				"credit_in_account_currency" : i.depreciation_amount,
				"credit": i.depreciation_amount,
				# "business_activity" : asset.business_activity,
				"cost_center" : asset.cost_center
			}
			je.append("accounts", entry_cred)
			entry_deb = {
				"reference_name" : asset_name,
				"reference_type" : "Asset",
				"account" : accounts[0].accumulated_depreciation_account,
				"debit_in_account_currency" : i.depreciation_amount,
				"debit": i.depreciation_amount,
				# "business_activity" : asset.business_activity,
				"cost_center" : asset.cost_center
			}
			je.append("accounts", entry_deb)
			je.insert()
			je.submit()
		if total_amount > 0:
			value_after_depreciation, finance_book_name = frappe.db.get_value('Asset Finance Book',{'asset_sub_category':asset.asset_sub_category,'parent':asset.name},['value_after_depreciation','name'])
			value_after_depreciation = flt(value_after_depreciation) + flt(total_amount)
			frappe.db.sql('''
				update `tabAsset Finance Book` set value_after_depreciation = {}
				where name = '{}' and parent = '{}'
			'''.format(value_after_depreciation,finance_book_name,asset.name))
	#Pro rating of asset value upon Scrapping Asset in Middle of month written by Thukten
	if cint(frappe.db.get_value("Company", asset.company, "pro_rate_asset_value")) == 1 and cint(frappe.db.get_value("Company", asset.company, "reset_asset_value")) == 0:
		pro_rate_days, no_of_days_in_month = 0, 0
		if posting_date != get_first_day(posting_date):
			pro_rate_days = date_diff(posting_date, get_first_day(posting_date))
			no_of_days_in_month = date_diff(get_last_day(getdate(posting_date)),get_first_day(getdate(posting_date)))
		if pro_rate_days > 1:
			dtl = frappe.db.sql("""select name, journal_entry, depreciation_amount, income_depreciation_amount, 
									accumulated_depreciation_amount, income_accumulated_depreciation,
									no_of_days_in_a_schedule,finance_book 
									from `tabDepreciation Schedule` 
									where parent = %s 
									and schedule_date = %s
								""", (asset_name, get_last_day(posting_date)), as_dict=1)
			if not dtl:
				return
			if dtl[0].journal_entry:
				frappe.throw(_("Reversal entry for the depreciation schedule date {0} has not happened").format(get_last_day(posting_date)))
			pro_rate_depreciation_amount = (flt(dtl[0].depreciation_amount)/dtl[0].no_of_days_in_a_schedule) * flt(pro_rate_days)
			pro_rate_depreciation_income_tax = (flt(dtl[0].income_depreciation_amount)/dtl[0].no_of_days_in_a_schedule) * flt(pro_rate_days)

			pro_accumulated_depreciation_amount = flt(dtl[0].accumulated_depreciation_amount - dtl[0].depreciation_amount + pro_rate_depreciation_amount)
			pro_accumulated_depreciation_income_tax = flt(dtl[0].income_accumulated_depreciation - dtl[0].income_depreciation_amount + pro_rate_depreciation_income_tax)
			if pro_rate_depreciation_amount <= 0:
				frappe.throw(_(" Pro Rate depreciation amount is {}, It should be greater than 0").format(pro_rate_depreciation_amount))

			je = frappe.new_doc("Journal Entry")
			je.voucher_type = "Depreciation Entry"
			je.posting_date = posting_date 
			je.company = asset.company
			je.branch = asset.branch  
			je.remark = "Depreciation Entry against {0} worth {1}".format(asset_name, pro_rate_depreciation_amount)

			je.append("accounts", {
				"account": accounts[0].accumulated_depreciation_account,
				"credit_in_account_currency": flt(pro_rate_depreciation_amount),
				"reference_type": "Asset",
				"reference_name": asset.name,
				# "business_activity": asset.business_activity, 
				"cost_center": asset.cost_center
			})
			je.append("accounts", {
				"account": accounts[0].depreciation_expense_account,
				"debit_in_account_currency": flt(pro_rate_depreciation_amount),
				"reference_type": "Asset",
				"reference_name": asset_name,
				# "business_activity": asset.business_activity, 
				"cost_center": asset.cost_center
			})

			je.flags.ignore_permissions = True
			je.submit()
			value_after_depreciation, finance_book_name = frappe.db.get_value('Asset Finance Book',
															{'finance_book':dtl[0].finance_book,
															'asset_sub_category':asset.asset_sub_category,
															'parent':asset.name},['value_after_depreciation','name'])
			value_after_depreciation = flt(value_after_depreciation) - flt(pro_rate_depreciation_amount)

			#Update Depreciation Schedule table
			frappe.db.set_value("Depreciation Schedule", dtl[0].name, "schedule_date", posting_date)
			frappe.db.set_value("Depreciation Schedule", dtl[0].name, "no_of_days_in_a_schedule", pro_rate_days)
			frappe.db.set_value("Depreciation Schedule", dtl[0].name, "journal_entry", je.name)
			frappe.db.set_value("Depreciation Schedule", dtl[0].name, "depreciation_amount", flt(pro_rate_depreciation_amount))
			frappe.db.set_value("Depreciation Schedule", dtl[0].name, "income_depreciation_amount", flt(pro_rate_depreciation_income_tax))
			frappe.db.set_value("Depreciation Schedule", dtl[0].name, "accumulated_depreciation_amount", flt(pro_accumulated_depreciation_amount))
			frappe.db.set_value("Depreciation Schedule", dtl[0].name, "income_accumulated_depreciation", flt(pro_accumulated_depreciation_income_tax))
			frappe.db.set_value("Asset Finance Book", finance_book_name, "value_after_depreciation", value_after_depreciation)

@frappe.whitelist()
def scrap_asset(asset_name,scrap_date=None):
	asset = frappe.get_doc("Asset", asset_name)
	reset_asset_value_for_scrap_sales(asset_name, scrap_date if scrap_date else nowdate())

	if asset.docstatus != 1:
		frappe.throw(_("Asset {0} must be submitted").format(asset.name))
	elif asset.status in ("Cancelled", "Sold", "Scrapped"):
		frappe.throw(
			_("Asset {0} cannot be scrapped, as it is already {1}").format(asset.name, asset.status)
		)

	depreciation_series = frappe.get_cached_value(
		"Company", asset.company, "series_for_depreciation_entry"
	)
	# reset_asset_value_for_scrap_sales(asset_name, getdate(today()))
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Depreciation Entry"
	je.naming_series = depreciation_series
	je.posting_date = today()
	je.company = asset.company
	je.remark = "Scrap Entry for asset {0}".format(asset_name)
	je.branch = asset.branch
	for entry in get_gl_entries_on_asset_disposal(asset):
		entry.update({"reference_type": "Asset", "reference_name": asset_name})
		je.append("accounts", entry)

	je.flags.ignore_permissions = True
	je.submit()

	frappe.db.set_value("Asset", asset_name, "disposal_date", today())
	frappe.db.set_value("Asset", asset_name, "journal_entry_for_scrap", je.name)
	asset.set_status("Scrapped")



@frappe.whitelist()
def restore_asset(asset_name):
	asset = frappe.get_doc("Asset", asset_name)

	je = asset.journal_entry_for_scrap

	asset.db_set("disposal_date", None)
	asset.db_set("journal_entry_for_scrap", None)

	frappe.get_doc("Journal Entry", je).cancel()

	asset.set_status()


def get_gl_entries_on_asset_regain(asset, selling_amount=0, finance_book=None):
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
		{
			"account": fixed_asset_account,
			"debit_in_account_currency": asset.gross_purchase_amount,
			"debit": asset.gross_purchase_amount,
			"cost_center": depreciation_cost_center,
		},
		{
			"account": accumulated_depr_account,
			"credit_in_account_currency": accumulated_depr_amount,
			"credit": accumulated_depr_amount,
			"cost_center": depreciation_cost_center,
		},
	]

	profit_amount = abs(flt(value_after_depreciation)) - abs(flt(selling_amount))
	if profit_amount:
		get_profit_gl_entries(profit_amount, gl_entries, disposal_account, depreciation_cost_center)

	return gl_entries


def get_gl_entries_on_asset_disposal(asset, selling_amount=0, finance_book=None):
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
		{
			"account": fixed_asset_account,
			"credit_in_account_currency": asset.gross_purchase_amount,
			"credit": asset.gross_purchase_amount,
			"cost_center": depreciation_cost_center,
		},
		{
			"account": accumulated_depr_account,
			"debit_in_account_currency": accumulated_depr_amount,
			"debit": accumulated_depr_amount,
			"cost_center": depreciation_cost_center,
		},
	]
	loss_disposal_account, gain_disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(asset.company)
	
	profit_amount = flt(selling_amount) - flt(value_after_depreciation)
	disposal_account = loss_disposal_account if flt(profit_amount) < 0 else gain_disposal_account
	if profit_amount:
		get_profit_gl_entries(profit_amount, gl_entries, disposal_account, depreciation_cost_center)
	return gl_entries


def get_asset_details(asset, finance_book=None):
	fixed_asset_account, accumulated_depr_account, depr_expense_account = get_depreciation_accounts(
		asset
	)
	loss_disposal_account, gain_disposal_account, depreciation_cost_center= get_disposal_account_and_cost_center(asset.company)
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	idx = 1
	if finance_book:
		for d in asset.finance_books:
			if d.finance_book == finance_book:
				idx = d.idx
				break

	value_after_depreciation = (
		# asset.finance_books[idx - 1].value_after_depreciation
		# add by biren to include pro rated depreciated amount in value after depreciation
		frappe.db.get_value("Asset Finance Book", asset.finance_books[idx - 1].name, "value_after_depreciation")
		if asset.calculate_depreciation
		else asset.value_after_depreciation
	)
	accumulated_depr_amount = flt(asset.gross_purchase_amount) - flt(value_after_depreciation)
	return (
		fixed_asset_account,
		asset,
		depreciation_cost_center,
		accumulated_depr_account,
		accumulated_depr_amount,
		gain_disposal_account,
		value_after_depreciation,
	)


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


@frappe.whitelist()
def get_disposal_account_and_cost_center(company):
	loss_disposal_account, gain_disposal_account, depreciation_cost_center = frappe.get_cached_value(
		"Company", company, ["loss_disposal_account", "gain_disposal_account", "depreciation_cost_center"]
	)

	if not gain_disposal_account or not loss_disposal_account:
		frappe.throw(
			_("Please set 'Gain/Loss Account on Asset Disposal' in Company {0}").format(company)
		)
	if not depreciation_cost_center:
		frappe.throw(_("Please set 'Asset Depreciation Cost Center' in Company {0}").format(company))

	return loss_disposal_account, gain_disposal_account, depreciation_cost_center
