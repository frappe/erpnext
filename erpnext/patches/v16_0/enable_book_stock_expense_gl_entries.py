import frappe


def execute():
	has_expense_accounts = frappe.db.exists(
		"Company", {"purchase_expense_account": ("is", "set")}
	) or frappe.db.exists("Item Default", {"purchase_expense_account": ("is", "set")})

	if has_expense_accounts:
		frappe.db.set_single_value("Accounts Settings", "book_stock_expense_gl_entries", 1)
