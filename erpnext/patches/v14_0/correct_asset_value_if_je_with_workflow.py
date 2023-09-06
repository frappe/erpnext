import frappe
from frappe.model.workflow import get_workflow_name
from frappe.query_builder.functions import IfNull, Sum


def execute():
	active_je_workflow = get_workflow_name("Journal Entry")
	if not active_je_workflow:
		return

	correct_value_for_assets_with_manual_depr_entries()

	finance_books = frappe.db.get_all("Finance Book", pluck="name")

	if finance_books:
		for fb_name in finance_books:
			correct_value_for_assets_with_auto_depr(fb_name)

	correct_value_for_assets_with_auto_depr()


def correct_value_for_assets_with_manual_depr_entries():
	asset = frappe.qb.DocType("Asset")
	gle = frappe.qb.DocType("GL Entry")
	aca = frappe.qb.DocType("Asset Category Account")
	company = frappe.qb.DocType("Company")

	asset_details_and_depr_amount_map = (
		frappe.qb.from_(gle)
		.join(asset)
		.on(gle.against_voucher == asset.name)
		.join(aca)
		.on((aca.parent == asset.asset_category) & (aca.company_name == asset.company))
		.join(company)
		.on(company.name == asset.company)
		.select(
			asset.name.as_("asset_name"),
			asset.gross_purchase_amount.as_("gross_purchase_amount"),
			asset.opening_accumulated_depreciation.as_("opening_accumulated_depreciation"),
			Sum(gle.debit).as_("depr_amount"),
		)
		.where(
			gle.account == IfNull(aca.depreciation_expense_account, company.depreciation_expense_account)
		)
		.where(gle.debit != 0)
		.where(gle.is_cancelled == 0)
		.where(asset.docstatus == 1)
		.where(asset.calculate_depreciation == 0)
		.groupby(asset.name)
	)

	frappe.qb.update(asset).join(asset_details_and_depr_amount_map).on(
		asset_details_and_depr_amount_map.asset_name == asset.name
	).set(
		asset.value_after_depreciation,
		asset_details_and_depr_amount_map.gross_purchase_amount
		- asset_details_and_depr_amount_map.opening_accumulated_depreciation
		- asset_details_and_depr_amount_map.depr_amount,
	).run()


def correct_value_for_assets_with_auto_depr(fb_name=None):
	asset = frappe.qb.DocType("Asset")
	gle = frappe.qb.DocType("GL Entry")
	aca = frappe.qb.DocType("Asset Category Account")
	company = frappe.qb.DocType("Company")
	afb = frappe.qb.DocType("Asset Finance Book")

	asset_details_and_depr_amount_map = (
		frappe.qb.from_(gle)
		.join(asset)
		.on(gle.against_voucher == asset.name)
		.join(aca)
		.on((aca.parent == asset.asset_category) & (aca.company_name == asset.company))
		.join(company)
		.on(company.name == asset.company)
		.select(
			asset.name.as_("asset_name"),
			asset.gross_purchase_amount.as_("gross_purchase_amount"),
			asset.opening_accumulated_depreciation.as_("opening_accumulated_depreciation"),
			Sum(gle.debit).as_("depr_amount"),
		)
		.where(
			gle.account == IfNull(aca.depreciation_expense_account, company.depreciation_expense_account)
		)
		.where(gle.debit != 0)
		.where(gle.is_cancelled == 0)
		.where(asset.docstatus == 1)
		.where(asset.calculate_depreciation == 1)
		.groupby(asset.name)
	)

	if fb_name:
		asset_details_and_depr_amount_map = asset_details_and_depr_amount_map.where(
			gle.finance_book == fb_name
		)
	else:
		asset_details_and_depr_amount_map = asset_details_and_depr_amount_map.where(
			(gle.finance_book.isin([""])) | (gle.finance_book.isnull())
		)

	query = (
		frappe.qb.update(afb)
		.join(asset_details_and_depr_amount_map)
		.on(asset_details_and_depr_amount_map.asset_name == afb.parent)
		.set(
			afb.value_after_depreciation,
			asset_details_and_depr_amount_map.gross_purchase_amount
			- asset_details_and_depr_amount_map.opening_accumulated_depreciation
			- asset_details_and_depr_amount_map.depr_amount,
		)
	)

	if fb_name:
		query = query.where(afb.finance_book == fb_name)
	else:
		query = query.where((afb.finance_book.isin([""])) | (afb.finance_book.isnull()))

	query.run()
