# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe import _


def get():
	return {
		_("Application of Funds (Assets)"): {
			_("Current Assets"): {
				_("Accounts Receivable"): {
					_("Debtors"): {
						"account_type": "Receivable",
						"account_number": "1310",
						"account_category": "Trade Receivables",
					},
					"account_number": "1300",
				},
				_("Bank Accounts"): {
					"account_type": "Bank",
					"is_group": 1,
					"account_number": "1200",
					"account_category": "Cash and Cash Equivalents",
				},
				_("Cash In Hand"): {
					_("Cash"): {
						"account_type": "Cash",
						"account_number": "1110",
						"account_category": "Cash and Cash Equivalents",
					},
					"account_type": "Cash",
					"account_number": "1100",
					"account_category": "Cash and Cash Equivalents",
				},
				_("Loans and Advances (Assets)"): {
					_("Employee Advances"): {
						"account_number": "1610",
						"account_type": "Payable",
						"account_category": "Other Receivables",
					},
					"account_number": "1600",
				},
				_("Securities and Deposits"): {
					_("Earnest Money"): {
						"account_number": "1651",
						"account_category": "Other Current Assets",
					},
					"account_number": "1650",
				},
				_("Prepaid Expenses"): {
					"account_number": "1660",
					"account_category": "Other Current Assets",
				},
				_("Short-term Investments"): {
					"account_number": "1670",
					"account_category": "Short-term Investments",
				},
				_("Stock Assets"): {
					_("Stock In Hand"): {
						"account_type": "Stock",
						"account_number": "1410",
						"account_category": "Stock Assets",
					},
					"account_type": "Stock",
					"account_number": "1400",
					"account_category": "Stock Assets",
				},
				_("Tax Assets"): {
					"is_group": 1,
					"account_number": "1500",
					"account_category": "Other Current Assets",
				},
				"account_number": "1100-1600",
			},
			_("Fixed Assets"): {
				_("Capital Equipment"): {
					"account_type": "Fixed Asset",
					"account_number": "1710",
					"account_category": "Tangible Assets",
				},
				_("Electronic Equipment"): {
					"account_type": "Fixed Asset",
					"account_number": "1720",
					"account_category": "Tangible Assets",
				},
				_("Furniture and Fixtures"): {
					"account_type": "Fixed Asset",
					"account_number": "1730",
					"account_category": "Tangible Assets",
				},
				_("Office Equipment"): {
					"account_type": "Fixed Asset",
					"account_number": "1740",
					"account_category": "Tangible Assets",
				},
				_("Plants and Machineries"): {
					"account_type": "Fixed Asset",
					"account_number": "1750",
					"account_category": "Tangible Assets",
				},
				_("Buildings"): {
					"account_type": "Fixed Asset",
					"account_number": "1760",
					"account_category": "Tangible Assets",
				},
				_("Software"): {
					"account_type": "Fixed Asset",
					"account_number": "1770",
					"account_category": "Intangible Assets",
				},
				_("Accumulated Depreciation"): {
					"account_type": "Accumulated Depreciation",
					"account_number": "1780",
					"account_category": "Tangible Assets",
				},
				_("CWIP Account"): {
					"account_type": "Capital Work in Progress",
					"account_number": "1790",
					"account_category": "Tangible Assets",
				},
				"account_number": "1700",
			},
			_("Investments"): {
				"is_group": 1,
				"account_number": "1800",
				"account_category": "Long-term Investments",
			},
			_("Temporary Accounts"): {
				_("Temporary Opening"): {
					"account_type": "Temporary",
					"account_number": "1910",
					"account_category": "Other Non-current Assets",
				},
				"account_number": "1900",
			},
			"root_type": "Asset",
			"account_number": "1000",
		},
		_("Expenses"): {
			_("Direct Expenses"): {
				_("Stock Expenses"): {
					_("Cost of Goods Sold"): {
						"account_type": "Cost of Goods Sold",
						"account_number": "5111",
						"account_category": "Cost of Goods Sold",
					},
					_("Expenses Included In Asset Valuation"): {
						"account_type": "Expenses Included In Asset Valuation",
						"account_number": "5112",
						"account_category": "Other Direct Costs",
					},
					_("Expenses Included In Valuation"): {
						"account_type": "Expenses Included In Valuation",
						"account_number": "5118",
						"account_category": "Other Direct Costs",
					},
					_("Stock Adjustment"): {
						"account_type": "Stock Adjustment",
						"account_number": "5119",
						"account_category": "Other Direct Costs",
					},
					"account_number": "5110",
				},
				"account_number": "5100",
			},
			_("Indirect Expenses"): {
				_("Administrative Expenses"): {
					"account_number": "5201",
					"account_category": "Operating Expenses",
				},
				_("Commission on Sales"): {
					"account_number": "5202",
					"account_category": "Operating Expenses",
				},
				_("Depreciation"): {
					"account_type": "Depreciation",
					"account_number": "5203",
					"account_category": "Operating Expenses",
				},
				_("Entertainment Expenses"): {
					"account_number": "5204",
					"account_category": "Operating Expenses",
				},
				_("Freight and Forwarding Charges"): {
					"account_type": "Chargeable",
					"account_number": "5205",
					"account_category": "Operating Expenses",
				},
				_("Legal Expenses"): {"account_number": "5206", "account_category": "Operating Expenses"},
				_("Marketing Expenses"): {
					"account_type": "Chargeable",
					"account_number": "5207",
					"account_category": "Operating Expenses",
				},
				_("Office Maintenance Expenses"): {
					"account_number": "5208",
					"account_category": "Operating Expenses",
				},
				_("Office Rent"): {"account_number": "5209", "account_category": "Operating Expenses"},
				_("Postal Expenses"): {"account_number": "5210", "account_category": "Operating Expenses"},
				_("Print and Stationery"): {
					"account_number": "5211",
					"account_category": "Operating Expenses",
				},
				_("Round Off"): {
					"account_type": "Round Off",
					"account_number": "5212",
					"account_category": "Operating Expenses",
				},
				_("Salary"): {"account_number": "5213", "account_category": "Operating Expenses"},
				_("Sales Expenses"): {"account_number": "5214", "account_category": "Operating Expenses"},
				_("Telephone Expenses"): {"account_number": "5215", "account_category": "Operating Expenses"},
				_("Travel Expenses"): {"account_number": "5216", "account_category": "Operating Expenses"},
				_("Utility Expenses"): {"account_number": "5217", "account_category": "Operating Expenses"},
				_("Write Off"): {"account_number": "5218", "account_category": "Operating Expenses"},
				_("Exchange Gain/Loss"): {"account_number": "5219", "account_category": "Operating Expenses"},
				_("Interest Expense"): {"account_number": "5220", "account_category": "Finance Costs"},
				_("Bank Charges"): {"account_number": "5221", "account_category": "Finance Costs"},
				_("Gain/Loss on Asset Disposal"): {
					"account_number": "5222",
					"account_category": "Other Operating Income",
				},
				_("Miscellaneous Expenses"): {
					"account_type": "Chargeable",
					"account_number": "5223",
					"account_category": "Operating Expenses",
				},
				_("Impairment"): {"account_number": "5224", "account_category": "Operating Expenses"},
				_("Tax Expense"): {"account_number": "5225", "account_category": "Tax Expense"},
				"account_number": "5200",
			},
			"root_type": "Expense",
			"account_number": "5000",
		},
		_("Income"): {
			_("Direct Income"): {
				_("Sales"): {"account_number": "4110", "account_category": "Revenue from Operations"},
				_("Service"): {"account_number": "4120", "account_category": "Revenue from Operations"},
				"account_number": "4100",
			},
			_("Indirect Income"): {
				_("Interest Income"): {"account_number": "4210", "account_category": "Investment Income"},
				_("Interest on Fixed Deposits"): {
					"account_number": "4220",
					"account_category": "Investment Income",
				},
				"is_group": 1,
				"account_number": "4200",
			},
			"root_type": "Income",
			"account_number": "4000",
		},
		_("Source of Funds (Liabilities)"): {
			_("Current Liabilities"): {
				_("Accounts Payable"): {
					_("Creditors"): {
						"account_type": "Payable",
						"account_number": "2110",
						"account_category": "Trade Payables",
					},
					_("Payroll Payable"): {"account_number": "2120", "account_category": "Other Payables"},
					"account_number": "2100",
				},
				_("Accrued Expenses"): {
					"account_number": "2150",
					"account_category": "Other Current Liabilities",
				},
				_("Customer Advances"): {
					"account_number": "2160",
					"account_category": "Other Current Liabilities",
				},
				_("Stock Liabilities"): {
					_("Stock Received But Not Billed"): {
						"account_type": "Stock Received But Not Billed",
						"account_number": "2210",
						"account_category": "Trade Payables",
					},
					_("Asset Received But Not Billed"): {
						"account_type": "Asset Received But Not Billed",
						"account_number": "2211",
						"account_category": "Trade Payables",
					},
					"account_number": "2200",
				},
				_("Duties and Taxes"): {
					_("TDS Payable"): {
						"account_number": "2310",
						"account_category": "Current Tax Liabilities",
					},
					"account_type": "Tax",
					"is_group": 1,
					"account_number": "2300",
					"account_category": "Current Tax Liabilities",
				},
				_("Short-term Provisions"): {
					"account_number": "2350",
					"account_category": "Short-term Provisions",
				},
				_("Loans (Liabilities)"): {
					_("Secured Loans"): {
						"account_number": "2410",
						"account_category": "Long-term Borrowings",
					},
					_("Unsecured Loans"): {
						"account_number": "2420",
						"account_category": "Long-term Borrowings",
					},
					_("Bank Overdraft Account"): {
						"account_number": "2430",
						"account_category": "Short-term Borrowings",
					},
					"account_number": "2400",
				},
				"account_number": "2100-2400",
			},
			_("Non-Current Liabilities"): {
				_("Long-term Provisions"): {
					"account_number": "2510",
					"account_category": "Long-term Provisions",
				},
				_("Employee Benefits Obligation"): {
					"account_number": "2520",
					"account_category": "Other Non-current Liabilities",
				},
				"is_group": 1,
				"account_number": "2500",
			},
			"root_type": "Liability",
			"account_number": "2000",
		},
		_("Equity"): {
			_("Capital Stock"): {
				"account_type": "Equity",
				"account_number": "3100",
				"account_category": "Share Capital",
			},
			_("Dividends Paid"): {
				"account_type": "Equity",
				"account_number": "3200",
				"account_category": "Reserves and Surplus",
			},
			_("Opening Balance Equity"): {
				"account_type": "Equity",
				"account_number": "3300",
				"account_category": "Reserves and Surplus",
			},
			_("Retained Earnings"): {
				"account_type": "Equity",
				"account_number": "3400",
				"account_category": "Reserves and Surplus",
			},
			_("Revaluation Surplus"): {
				"account_type": "Equity",
				"account_number": "3500",
				"account_category": "Reserves and Surplus",
			},
			"root_type": "Equity",
			"account_number": "3000",
		},
	}
