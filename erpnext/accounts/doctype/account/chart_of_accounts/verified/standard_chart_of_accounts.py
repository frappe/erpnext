# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe import _


def get():
	return {
		_("Application of Funds (Assets)"): {
			_("Current Assets"): {
				_("Accounts Receivable"): {
					_("Debtors"): {"account_type": "Receivable", "account_category": "Trade Receivables"}
				},
				_("Bank Accounts"): {
					"account_type": "Bank",
					"is_group": 1,
					"account_category": "Cash and Cash Equivalents",
				},
				_("Cash In Hand"): {
					_("Cash"): {"account_type": "Cash", "account_category": "Cash and Cash Equivalents"},
					"account_type": "Cash",
					"account_category": "Cash and Cash Equivalents",
				},
				_("Loans and Advances (Assets)"): {
					_("Employee Advances"): {
						"account_type": "Payable",
						"account_category": "Other Receivables",
					},
				},
				_("Securities and Deposits"): {
					_("Earnest Money"): {"account_category": "Other Current Assets"}
				},
				_("Prepaid Expenses"): {"account_category": "Other Current Assets"},
				_("Short-term Investments"): {"account_category": "Short-term Investments"},
				_("Stock Assets"): {
					_("Stock In Hand"): {"account_type": "Stock", "account_category": "Stock Assets"},
					"account_type": "Stock",
					"account_category": "Stock Assets",
				},
				_("Tax Assets"): {"is_group": 1, "account_category": "Other Current Assets"},
			},
			_("Fixed Assets"): {
				_("Capital Equipment"): {
					"account_type": "Fixed Asset",
					"account_category": "Tangible Assets",
				},
				_("Electronic Equipment"): {
					"account_type": "Fixed Asset",
					"account_category": "Tangible Assets",
				},
				_("Furniture and Fixtures"): {
					"account_type": "Fixed Asset",
					"account_category": "Tangible Assets",
				},
				_("Office Equipment"): {"account_type": "Fixed Asset", "account_category": "Tangible Assets"},
				_("Plants and Machineries"): {
					"account_type": "Fixed Asset",
					"account_category": "Tangible Assets",
				},
				_("Buildings"): {"account_type": "Fixed Asset", "account_category": "Tangible Assets"},
				_("Software"): {"account_type": "Fixed Asset", "account_category": "Intangible Assets"},
				_("Accumulated Depreciation"): {
					"account_type": "Accumulated Depreciation",
					"account_category": "Tangible Assets",
				},
				_("CWIP Account"): {
					"account_type": "Capital Work in Progress",
					"account_category": "Tangible Assets",
				},
			},
			_("Investments"): {"is_group": 1, "account_category": "Long-term Investments"},
			_("Temporary Accounts"): {
				_("Temporary Opening"): {
					"account_type": "Temporary",
					"account_category": "Other Non-current Assets",
				}
			},
			"root_type": "Asset",
		},
		_("Expenses"): {
			_("Direct Expenses"): {
				_("Stock Expenses"): {
					_("Cost of Goods Sold"): {
						"account_type": "Cost of Goods Sold",
						"account_category": "Cost of Goods Sold",
					},
					_("Expenses Included In Asset Valuation"): {
						"account_type": "Expenses Included In Asset Valuation",
						"account_category": "Other Direct Costs",
					},
					_("Expenses Included In Valuation"): {
						"account_type": "Expenses Included In Valuation",
						"account_category": "Other Direct Costs",
					},
					_("Stock Adjustment"): {
						"account_type": "Stock Adjustment",
						"account_category": "Other Direct Costs",
					},
				},
			},
			_("Indirect Expenses"): {
				_("Administrative Expenses"): {"account_category": "Operating Expenses"},
				_("Commission on Sales"): {"account_category": "Operating Expenses"},
				_("Depreciation"): {"account_type": "Depreciation", "account_category": "Operating Expenses"},
				_("Entertainment Expenses"): {"account_category": "Operating Expenses"},
				_("Freight and Forwarding Charges"): {
					"account_type": "Chargeable",
					"account_category": "Operating Expenses",
				},
				_("Legal Expenses"): {"account_category": "Operating Expenses"},
				_("Marketing Expenses"): {
					"account_type": "Chargeable",
					"account_category": "Operating Expenses",
				},
				_("Miscellaneous Expenses"): {
					"account_type": "Chargeable",
					"account_category": "Operating Expenses",
				},
				_("Office Maintenance Expenses"): {"account_category": "Operating Expenses"},
				_("Office Rent"): {"account_category": "Operating Expenses"},
				_("Postal Expenses"): {"account_category": "Operating Expenses"},
				_("Print and Stationery"): {"account_category": "Operating Expenses"},
				_("Round Off"): {"account_type": "Round Off", "account_category": "Operating Expenses"},
				_("Salary"): {"account_category": "Operating Expenses"},
				_("Sales Expenses"): {"account_category": "Operating Expenses"},
				_("Telephone Expenses"): {"account_category": "Operating Expenses"},
				_("Travel Expenses"): {"account_category": "Operating Expenses"},
				_("Utility Expenses"): {"account_category": "Operating Expenses"},
				_("Write Off"): {"account_category": "Operating Expenses"},
				_("Exchange Gain/Loss"): {"account_category": "Operating Expenses"},
				_("Interest Expense"): {"account_category": "Finance Costs"},
				_("Bank Charges"): {"account_category": "Finance Costs"},
				_("Gain/Loss on Asset Disposal"): {"account_category": "Other Operating Income"},
				_("Impairment"): {"account_category": "Operating Expenses"},
				_("Tax Expense"): {"account_category": "Tax Expense"},
			},
			"root_type": "Expense",
		},
		_("Income"): {
			_("Direct Income"): {
				_("Sales"): {"account_category": "Revenue from Operations"},
				_("Service"): {"account_category": "Revenue from Operations"},
			},
			_("Indirect Income"): {
				_("Interest Income"): {"account_category": "Investment Income"},
				_("Interest on Fixed Deposits"): {"account_category": "Investment Income"},
				"is_group": 1,
			},
			"root_type": "Income",
		},
		_("Source of Funds (Liabilities)"): {
			_("Current Liabilities"): {
				_("Accounts Payable"): {
					_("Creditors"): {"account_type": "Payable", "account_category": "Trade Payables"},
					_("Payroll Payable"): {"account_category": "Other Payables"},
				},
				_("Accrued Expenses"): {"account_category": "Other Current Liabilities"},
				_("Customer Advances"): {"account_category": "Other Current Liabilities"},
				_("Stock Liabilities"): {
					_("Stock Received But Not Billed"): {
						"account_type": "Stock Received But Not Billed",
						"account_category": "Trade Payables",
					},
					_("Asset Received But Not Billed"): {
						"account_type": "Asset Received But Not Billed",
						"account_category": "Trade Payables",
					},
				},
				_("Duties and Taxes"): {
					"account_type": "Tax",
					"is_group": 1,
					"account_category": "Current Tax Liabilities",
				},
				_("Short-term Provisions"): {"account_category": "Short-term Provisions"},
				_("Loans (Liabilities)"): {
					_("Secured Loans"): {"account_category": "Long-term Borrowings"},
					_("Unsecured Loans"): {"account_category": "Long-term Borrowings"},
					_("Bank Overdraft Account"): {"account_category": "Short-term Borrowings"},
				},
			},
			_("Non-Current Liabilities"): {
				_("Long-term Provisions"): {"account_category": "Long-term Provisions"},
				_("Employee Benefits Obligation"): {"account_category": "Other Non-current Liabilities"},
				"is_group": 1,
			},
			"root_type": "Liability",
		},
		_("Equity"): {
			_("Capital Stock"): {"account_type": "Equity", "account_category": "Share Capital"},
			_("Dividends Paid"): {"account_type": "Equity", "account_category": "Reserves and Surplus"},
			_("Opening Balance Equity"): {
				"account_type": "Equity",
				"account_category": "Reserves and Surplus",
			},
			_("Retained Earnings"): {"account_type": "Equity", "account_category": "Reserves and Surplus"},
			_("Revaluation Surplus"): {"account_type": "Equity", "account_category": "Reserves and Surplus"},
			"root_type": "Equity",
		},
	}
