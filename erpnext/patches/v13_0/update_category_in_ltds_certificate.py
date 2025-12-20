import frappe


def execute():
	company = frappe.get_all("Company", filters={"country": "India"})
	if not company:
		return

	frappe.reload_doc("regional", "doctype", "lower_deduction_certificate")

	ldc = frappe.qb.DocType("Lower Deduction Certificate").as_("ldc")
	supplier = frappe.qb.DocType("Supplier")

	frappe.qb.update(ldc).inner_join(supplier).on(ldc.supplier == supplier.name).set(
		ldc.tax_withholding_category, supplier.tax_withholding_category
	).where(ldc.tax_withholding_category.isnull()).run()
