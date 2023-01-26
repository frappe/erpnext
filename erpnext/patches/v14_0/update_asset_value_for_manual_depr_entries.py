import frappe


def execute():
	asset = frappe.qb.DocType("Asset")
	gle = frappe.qb.DocType("GL Entry")

	depreciation_expense_account = frappe.db.get_value(
		"Asset Category Account",
		filters={"parent": asset.asset_category, "company_name": asset.company},
		fieldname="depreciation_expense_account",
	)

	frappe.qb.update(asset).inner_join(gle).on(gle.against_voucher == asset.name).set(
		asset.value_after_depreciation, asset.value_after_depreciation - gle.debit
	).where(asset.docstatus == 1).where(asset.calculate_depreciation == 0).where(
		gle.against_voucher_type == "Asset"
	).where(
		gle.account == depreciation_expense_account
	).where(
		gle.debit != 0
	).where(
		gle.is_cancelled == 0
	).run()
