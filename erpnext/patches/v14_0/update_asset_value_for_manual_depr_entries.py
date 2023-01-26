import frappe


def execute():
	asset = frappe.qb.DocType("Asset")
	gle = frappe.qb.DocType("GL Entry")
	aca = frappe.qb.DocType("Asset Category Account")
	company = frappe.qb.DocType("Company")

	frappe.qb.update(asset).join(gle).on(gle.against_voucher == asset.name).join(aca).on(
		(aca.parent == asset.asset_category) & (aca.company_name == asset.company)
	).join(company).on(company.name == asset.company).set(
		asset.value_after_depreciation, asset.value_after_depreciation - gle.debit
	).where(
		asset.docstatus == 1
	).where(
		asset.calculate_depreciation == 0
	).where(
		gle.against_voucher_type == "Asset"
	).where(
		gle.account == (aca.depreciation_expense_account or company.depreciation_expense_account)
	).where(
		gle.debit != 0
	).where(
		gle.is_cancelled == 0
	).run()
