import frappe

def execute():
	for doctype, fieldname in (
		("Sales Invoice", "against_invoice"),
		("Purchase Invoice", "against_voucher"),
		("Sales Order", "against_sales_order"),
		("Purchase Order", "against_purchase_order"),
		("Journal Entry", "against_jv"),
		("Expense Claim", "against_expense_claim"),
	):
		frappe.db.update("""update `tabJournal Entry Detail`
			set reference_type=%s and reference_name={0} where ifnull({0}, '') != ''
		""".format(fieldname), doctype)
