# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe import _


def get():
	return {
		_("Application of Funds (Assets)"): {
			_("Current Assets"): {
				_("Accounts Receivable"): {
					_("Debtors"): {"account_type": "Receivable", "account_number": "1310"},
					"account_number": "1300",
				},
				_("Bank Accounts"): {"account_type": "Bank", "is_group": 1, "account_number": "1200"},
				_("Cash In Hand"): {
					_("Cash"): {"account_type": "Cash", "account_number": "1110"},
					"account_type": "Cash",
					"account_number": "1100",
				},
				_("Loans and Advances (Assets)"): {
					_("Employee Advances"): {"account_number": "1610"},
					"account_number": "1600",
				},
				_("Securities and Deposits"): {
					_("Earnest Money"): {"account_number": "1651"},
					"account_number": "1650",
				},
				_("Stock Assets"): {
					_("Stock In Hand"): {"account_type": "Stock", "account_number": "1410"},
					"account_type": "Stock",
					"account_number": "1400",
				},
				_("Tax Assets"): {"is_group": 1, "account_number": "1500"},
				"account_number": "1100-1600",
			},
			_("Fixed Assets"): {
				_("Capital Equipment"): {"account_type": "Fixed Asset", "account_number": "1710"},
				_("Electronic Equipment"): {"account_type": "Fixed Asset", "account_number": "1720"},
				_("Furniture and Fixtures"): {"account_type": "Fixed Asset", "account_number": "1730"},
				_("Office Equipment"): {"account_type": "Fixed Asset", "account_number": "1740"},
				_("Plants and Machineries"): {"account_type": "Fixed Asset", "account_number": "1750"},
				_("Buildings"): {"account_type": "Fixed Asset", "account_number": "1760"},
				_("Software"): {"account_type": "Fixed Asset", "account_number": "1770"},
				_("Accumulated Depreciation"): {
					"account_type": "Accumulated Depreciation",
					"account_number": "1780",
				},
				_("CWIP Account"): {"account_type": "Capital Work in Progress", "account_number": "1790"},
				"account_number": "1700",
			},
			_("Investments"): {"is_group": 1, "account_number": "1800"},
			_("Temporary Accounts"): {
				_("Temporary Opening"): {"account_type": "Temporary", "account_number": "1910"},
				"account_number": "1900",
			},
			"root_type": "Asset",
			"account_number": "1000",
		},
		_("Expenses"): {
			_("Direct Expenses"): {
				_("Stock Expenses"): {
					_("Cost of Goods Sold"): {"account_type": "Cost of Goods Sold", "account_number": "5111"},
					_("Expenses Included In Asset Valuation"): {
						"account_type": "Expenses Included In Asset Valuation",
						"account_number": "5112",
					},
					_("Expenses Included In Valuation"): {
						"account_type": "Expenses Included In Valuation",
						"account_number": "5118",
					},
					_("Stock Adjustment"): {"account_type": "Stock Adjustment", "account_number": "5119"},
					"account_number": "5110",
				},
				"account_number": "5100",
			},
			_("Indirect Expenses"): {
				_("Administrative Expenses"): {"account_number": "5201"},
				_("Commission on Sales"): {"account_number": "5202"},
				_("Depreciation"): {"account_type": "Depreciation", "account_number": "5203"},
				_("Entertainment Expenses"): {"account_number": "5204"},
				_("Freight and Forwarding Charges"): {"account_type": "Chargeable", "account_number": "5205"},
				_("Legal Expenses"): {"account_number": "5206"},
				_("Marketing Expenses"): {"account_type": "Chargeable", "account_number": "5207"},
				_("Office Maintenance Expenses"): {"account_number": "5208"},
				_("Office Rent"): {"account_number": "5209"},
				_("Postal Expenses"): {"account_number": "5210"},
				_("Print and Stationery"): {"account_number": "5211"},
				_("Round Off"): {"account_type": "Round Off", "account_number": "5212"},
				_("Salary"): {"account_number": "5213"},
				_("Sales Expenses"): {"account_number": "5214"},
				_("Telephone Expenses"): {"account_number": "5215"},
				_("Travel Expenses"): {"account_number": "5216"},
				_("Utility Expenses"): {"account_number": "5217"},
				_("Write Off"): {"account_number": "5218"},
				_("Exchange Gain/Loss"): {"account_number": "5219"},
				_("Gain/Loss on Asset Disposal"): {"account_number": "5220"},
				_("Miscellaneous Expenses"): {"account_type": "Chargeable", "account_number": "5221"},
				"account_number": "5200",
			},
			"root_type": "Expense",
			"account_number": "5000",
		},
		_("Income"): {
			_("Direct Income"): {
				_("Sales"): {"account_number": "4110"},
				_("Service"): {"account_number": "4120"},
				"account_number": "4100",
			},
			_("Indirect Income"): {"is_group": 1, "account_number": "4200"},
			"root_type": "Income",
			"account_number": "4000",
		},
		_("Source of Funds (Liabilities)"): {
			_("Current Liabilities"): {
				_("Accounts Payable"): {
					_("Creditors"): {"account_type": "Payable", "account_number": "2110"},
					_("Payroll Payable"): {"account_number": "2120"},
					"account_number": "2100",
				},
				_("Stock Liabilities"): {
					_("Stock Received But Not Billed"): {
						"account_type": "Stock Received But Not Billed",
						"account_number": "2210",
					},
					_("Asset Received But Not Billed"): {
						"account_type": "Asset Received But Not Billed",
						"account_number": "2211",
					},
					"account_number": "2200",
				},
				_("Duties and Taxes"): {
					_("TDS Payable"): {"account_number": "2310"},
					"account_type": "Tax",
					"is_group": 1,
					"account_number": "2300",
				},
				_("Loans (Liabilities)"): {
					_("Secured Loans"): {"account_number": "2410"},
					_("Unsecured Loans"): {"account_number": "2420"},
					_("Bank Overdraft Account"): {"account_number": "2430"},
					"account_number": "2400",
				},
				"account_number": "2100-2400",
			},
			"root_type": "Liability",
			"account_number": "2000",
		},
		_("Equity"): {
			_("Capital Stock"): {"account_type": "Equity", "account_number": "3100"},
			_("Dividends Paid"): {"account_type": "Equity", "account_number": "3200"},
			_("Opening Balance Equity"): {"account_type": "Equity", "account_number": "3300"},
			_("Retained Earnings"): {"account_type": "Equity", "account_number": "3400"},
			"root_type": "Equity",
			"account_number": "3000",
		},
	}
