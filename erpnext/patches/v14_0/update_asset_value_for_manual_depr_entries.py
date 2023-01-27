import frappe
from frappe.query_builder.functions import IfNull, Sum


def execute():
	asset = frappe.qb.DocType("Asset")
	gle = frappe.qb.DocType("GL Entry")
	aca = frappe.qb.DocType("Asset Category Account")
	company = frappe.qb.DocType("Company")

	frappe.qb.update(asset).join(gle).on(gle.against_voucher == asset.name).join(aca).on(
		(aca.parent == asset.asset_category) & (aca.company_name == asset.company)
	).join(company).on(company.name == asset.company).set(
		asset.value_after_depreciation, asset.value_after_depreciation - Sum(gle.debit)
	).where(
		asset.docstatus == 1
	).where(
		asset.calculate_depreciation == 0
	).where(
		gle.account == IfNull(aca.depreciation_expense_account, company.depreciation_expense_account)
	).where(
		gle.debit != 0
	).where(
		gle.is_cancelled == 0
	).run()
