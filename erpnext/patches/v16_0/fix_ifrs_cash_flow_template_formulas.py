import frappe

TEMPLATE = "Standard Cash Flow Statement (IFRS)"

# reference code: (formula as shipped before the fix, fixed formula)
FORMULAS = {
	"CF_OP100": (
		'{"and": [["root_type", "in", ["Income", "Expense"]], ["account_category", "!=", "Tax Expense"]]}',
		'{"and": [["root_type", "in", ["Income", "Expense"]], {"or": [["account_category", "is", "not set"], ["account_category", "!=", "Tax Expense"]]}]}',
	),
	"CF_WC500": (
		'["account_category", "in", ["Other Payables", "Current Tax Liabilities", "Short-term Borrowings", "Short-term Provisions", "Other Current Liabilities"]]',
		'["account_category", "in", ["Other Payables", "Current Tax Liabilities", "Short-term Provisions", "Other Current Liabilities"]]',
	),
}


# short-term borrowings stay counted in financing activities only while this row is as shipped
FINANCING_ROW = ("CF_FIN200", '["account_category", "in", ["Long-term Borrowings", "Short-term Borrowings"]]')


def execute():
	"""Fix the shipped IFRS cash flow formulas on sites whose copy still has them unchanged."""
	formulas = dict(FORMULAS)
	if not has_formula(*FINANCING_ROW):
		formulas.pop("CF_WC500")

	for reference_code, (shipped_formula, fixed_formula) in formulas.items():
		frappe.db.set_value(
			"Financial Report Row",
			{
				"parenttype": "Financial Report Template",
				"parent": TEMPLATE,
				"reference_code": reference_code,
				"calculation_formula": shipped_formula,
			},
			"calculation_formula",
			fixed_formula,
			update_modified=False,
		)


def has_formula(reference_code: str, formula: str) -> bool:
	return bool(
		frappe.db.exists(
			"Financial Report Row",
			{
				"parenttype": "Financial Report Template",
				"parent": TEMPLATE,
				"reference_code": reference_code,
				"calculation_formula": formula,
			},
		)
	)
