# Copyright(c) 2017, Khairil Zhafri
# License: GNU General Public License v3.See license.txt

from __future__
import unicode_literals
from frappe
import _

def get():
	return {
		_("1000 NON-CURRENT ASSETS"): {
			_("1100 Property, plant and equipment"): {
				_("1101 Freehold land"): {
					"account_type": "Fixed Asset"
				},
				_("1102 Freehold buildings"): {
					"account_type": "Fixed Asset"
				},
				_("1103 Furniture, fittings and equipment"): {
					"account_type": "Fixed Asset"
				},
				_("1104 Machinery and vehicles"): {
					"account_type": "Fixed Asset"
				},
				_("1105 Assets under construction"): {
					"account_type": "Fixed Asset"
				},
				_("11xx Accumulated depreciation"): {
					"account_type": "Accumulated Depreciation"
				},
				"is_group": 1
			},
			_("1200 Investment properties"): {
				"is_group": 1
			},
			_("1300 Intangible assets"): {
				_("1301 Goodwill"): {
					"account_type": "Fixed Asset"
				},
				_("1302 Patents, trademarks and other rights"): {
					"account_type": "Fixed Asset"
				},
				_("1303 Internally generated software"): {
					"account_type": "Fixed Asset"
				},
				_("1304 Customer contracts"): {
					"account_type": "Fixed Asset"
				},
				"is_group": 1
			},
			_("1400 Deferred tax assets"): {
				"is_group": 1
			},
			_("1500 Equity investments"): {
				"is_group": 1
			},
			_("1600 Held-to-maturity investments"): {
				_("1601 Debentures"): {},
				_("1602 Zero-coupon bonds"): {},
				"is_group": 1
			},
			_("1700 Available-for-sale financial assets"): {
				_("1701 Equity securities"): {},
				_("1702 Debentures"): {},
				_("1703 Preference shares"): {},
				"is_group": 1
			},
			_("1800 Derivative financial instruments"): {
				_("1801 Interest rate swap contracts - cash flow hedges"): {},
				"is_group": 1
			},
			_("1900 Receivables"): {
				_("1901 Loans to related parties"): {},
				_("1902 Loans to key management personnel"): {},
				_("1903 Other receivables"): {},
				"account_type": "Receivable",
				"is_group": 1
			},
			"root_type": "Asset"
		},
		_("2000 CURRENT ASSETS"): {
			_("2100 Inventories"): {
				"account_type": "Stock",
				"is_group": 1
			},
			_("2200 Current tax assets"): {
				"account_type": "Receivable",
				"is_group": 1
			},
			_("2300 Trade and other receivables"): {
				_("2301 Trade receivables"): {
					"account_type": "Receivable"
				},
				_("2302 Loans to key management personnel"): {
					"account_type": "Receivable"
				},
				_("2303 Other receivables"): {
					"account_type": "Receivable"
				},
				_("2304 Prepayments"): {
					"account_type": "Receivable"
				},
				"is_group": 1
			},
			_("2400 Derivative financial instruments"): {
				_("2401 Interest rate swap contracts - cash flow hedges"): {
					"account_type": "Receivable"
				},
				_("2402 Forward foreign exchange contracts - cash flow hedges"): {
					"account_type": "Receivable"
				},
				"is_group": 1
			},
			_("2600 Cash"): {
				_("Cash bag 0001"): {
					"account_type": "Cash"
				},
				"account_type": "Cash"
				"is_group": 1
			},
			_("2700 Cash equivalents"): {
				"account_type": "Bank",
				"is_group": 1
			},
			_("2xxx Assets classified as held for sale"): {},
			"root_type": "Asset"
		},
		_("3000 NON-CURRENT LIABILITIES"): {
			_("3100 Borrowings"): {
				_("3101 Bank loans"): {},
				_("3102 Debentures"): {},
				_("3103 Lease liabilities"): {},
				_("3104 Other loans"): {},
				_("3105 Convertible notes"): {},
				_("3106 Redeemable preference shares"): {},
				_("3107 Loans from related parties"): {},
				"is_group": 1
			},
			_("3200 Deferred tax liabilities"): {
				"is_group": 1
			},
			_("3300 Employee benefit obligations"): {
				_("3301 Leave obligations"): {},
				_("3302 Share-appreciation rights"): {},
				_("3303 Defined pension benefits"): {},
				_("3304 Post-employment medical benefits"): {},
				"is_group": 1
			},
			_("3400 Provisions"): {
				_("3304 Post-employment medical benefits"): {},
				"is_group": 1
			},
			"root_type": "Liability"
		},
		_("4000 CURRENT LIABILITIES"): {
			_("4100 Trade and other payables"): {
				_("4101 Trade payables"): {
					"account_type": "Payable"
				},
				_("4102 Payroll tax and other statutory liabilities"): {
					"account_type": "Payable"
				},
				_("4103 Other payables"): {
					"account_type": "Payable"
				},
				_("4104 Bills payable"): {
					"account_type": "Payable"
				},
				_("4105 Goods received not invoiced"): {
					"account_type": "Stock Received But Not Billed"
				},
				"is_group": 1
			},
			_("4200 Current tax liabilities"): {
				"account_type": "Receivable",
				"is_group": 1
			},
			_("4300 Borrowings"): {
				_("4301 Bank overdrafts"): {},
				_("4302 Bank loans"): {},
				_("4303 Debentures"): {},
				_("4304 Lease liabilities"): {},
				_("4305 Other loans"): {},
				"is_group": 1
			},
			_("4400 Derivative financial instruments"): {
				_("4401 Forward foreign exchange contracts - held for trading"): {},
				_("4402 Forward foreign exchange contracts"): {},
				"is_group": 1
			},
			_("4500 Employee benefit obligations"): {
				_("4501 Leave obligations"): {},
				"is_group": 1
			},
			_("4600 Provisions"): {
				_("4601 Make good provision"): {},
				_("4602 Restructuring obligations"): {},
				_("4603 Service warranties"): {},
				_("4604 Volume discounts and returns"): {},
				_("4605 Legal claim"): {},
				_("4606 Contingent liability"): {},
				"is_group": 1
			},
			_("4700 Deferred revenue"): {
				"is_group": 1
			},
			_("4xxx Liabilities directly associated with assets classified as held for sale"): {},
			"root_type": "Liability"
		},
		_("5000 EQUITY"): {
			_("5001 Share capital and share premium"): {
				"account_type": "Equity"
			},
			_("5002 Other equity"): {
				"account_type": "Equity"
			},
			_("5003 Other reserves"): {
				"account_type": "Equity"
			},
			_("5004 Retained earnings"): {
				"account_type": "Equity"
			},
			_("5005 Non-controlling interests"): {
				"account_type": "Equity"
			},
			"root_type": "Equity"
		},
		_("6000 REVENUE"): {
			_("6100 Sale of goods"): {
				_("6101 Merchandising"): {
					"account_type": "Income Account"
				},
				_("6102 Publishing"): {
					"account_type": "Income Account"
				},
				"is_group": 1
			},
			_("6200 Rendering of services"): {
				_("6201 Consulting"): {
					"account_type": "Income Account"
				},
				_("6202 Training"): {
					"account_type": "Income Account"
				},
				"is_group": 1
			},
			_("6300 Other income"): {
				_("6301 Rental and sub-lease rental income"): {
					"account_type": "Income Account"
				},
				_("6302 Dividends"): {
					"account_type": "Income Account"
				},
				_("6303 Interest on financial assets held as investments"): {
					"account_type": "Income Account"
				},
				_("6304 Government grants"): {
					"account_type": "Income Account"
				},
				"is_group": 1
			},
			"root_type": "Income"
		},
		_("7000 EXPENSES"): {
			_("7100 Cost of goods sold"): {
				_("7101 Merchandising"): {
					"account_type": "Cost of Goods Sold"
				},
				_("7102 Publishing"): {
					"account_type": "Cost of Goods Sold"
				},
				_("71xx Inventory adjustment"): {
					"account_type": "Stock Adjustment"
				},
				_("71xx Inventory valuation"): {
					"account_type": "Expenses Included In Valuation"
				},
				"is_group": 1
			},
			_("7200 Cost of services rendered"): {
				_("7201 Consulting"): {
					"account_type": "Cost of Goods Sold"
				},
				_("7202 Training"): {
					"account_type": "Cost of Goods Sold"
				},
				"is_group": 1
			},
			_("7300 Selling and distribution costs"): {
				_("7301 Accommodation"): {
					"account_type": "Chargeable"
				},
				_("7302 Food and beverages"): {
					"account_type": "Chargeable"
				},
				_("7303 Freight and forwarding"): {
					"account_type": "Expense Account"
				},
				_("7304 Marketing and advertising"): {
					"account_type": "Chargeable"
				},
				_("7305 Sales commission"): {
					"account_type": "Expense Account"
				},
				_("7306 Travel and entertainment"): {
					"account_type": "Chargeable"
				},
				_("7307 Warehousing and storage"): {
					"account_type": "Expense Account"
				},
				_("7308 Gifts and donations"): {
					"account_type": "Chargeable"
				},
				_("7309 Insurance"): {
					"account_type": "Chargeable"
				},
				_("73xx Sundry expenses"): {
					"account_type": "Chargeable"
				},
				"is_group": 1
			},
			_("7400 Administrative expenses"): {
				_("7401 Courier and postage"): {
					"account_type": "Expense Account"
				},
				_("7402 Internet and telephone"): {
					"account_type": "Chargeable"
				},
				_("7403 Maintenance and upkeep"): {
					"account_type": "Chargeable"
				},
				_("7404 Printing and stationery"): {
					"account_type": "Chargeable"
				},
				_("7405 Professional fee"): {
					"account_type": "Expense Account"
				},
				_("7406 Rent and rates"): {
					"account_type": "Expense Account"
				},
				_("7407 Staff benefits"): {
					"account_type": "Chargeable"
				},
				_("7408 Staff pay"): {
					"account_type": "Expense Account"
				},
				_("7409 Water and energy"): {
					"account_type": "Chargeable"
				},
				_("74xx Miscellaneous expenses"): {
					"account_type": "Chargeable"
				},
				"is_group": 1
			},
			_("7500 Other expenses"): {
				_("7501 Banking charges"): {
					"account_type": "Expense Account"
				},
				_("7502 Payment processing fee"): {
					"account_type": "Expense Account"
				},
				_("7503 Gain/(loss) on disposal of property, plant and equipment"): {
					"account_type": "Expense Account"
				},
				_("7504 Adjustment to investment property"): {
					"account_type": "Expense Account"
				},
				_("7505 Gains/(losses) on financial assets"): {
					"account_type": "Expense Account"
				},
				_("7506 Gain/(loss) on sale of available-for-sale financial assets"): {
					"account_type": "Expense Account"
				},
				_("7507 Foreign exchange gains/(losses)"): {},
				_("7508 Depreciation expense"): {
					"account_type": "Depreciation"
				},
				_("7509 Write-off expense"): {
					"account_type": "Expense Account"
				},
				_("7510 Round-off expense"): {
					"account_type": "Round Off"
				},
				"is_group": 1
			},
			"root_type": "Expense"
		},
		_("8000 NON-OPERATING INCOME AND EXPENSES"): {
			_("8100 Finance income"): {
				_("8101 Interest from financial assets held for cash management purposes"): {
					"account_type": "Income Account"
				},
				_("8102 Net gain on settlement of debt"): {
					"account_type": "Income Account"
				},
				"is_group": 1
			},
			_("8200 Finance costs"): {
				_("8201 Interest and finance charges"): {
					"account_type": "Expense Account"
				},
				_("8202 Provisions for unwinding of discount"): {
					"account_type": "Expense Account"
				},
				"is_group": 1
			},
			_("8300 Share of net profit of associates and joint ventures"): {},
			"root_type": "Expense"
		},
		_("9000 INCOME TAX"): {
			_("9001 Income tax benefit"): {
				"account_type": "Income Account"
			},
			_("9002 Income tax expense"): {
				"account_type": "Expense Account"
			},
			"root_type": "Expense"
		}
	}
