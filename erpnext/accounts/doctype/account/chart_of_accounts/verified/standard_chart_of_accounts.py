# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

from frappe import _


def get():
	return {
	    _("Application of Funds (Assets)"): {
	        _("Current Assets"): {
	            _("Accounts Receivable"): {
	                _("Debtors"): {
	                    "account_type": "Receivable"
	                }
	            },
	            _("Bank Accounts"): {
	                "account_type": "Bank",
					"is_group": 1
	            },
	            _("Cash In Hand"): {
	                _("Cash"): {
	                    "account_type": "Cash"
	                },
	                "account_type": "Cash"
	            },
	            _("Loans and Advances (Assets)"): {
                    	_("Employee Advances"): {
                    	},
	            },
	            _("Securities and Deposits"): {
	                _("Earnest Money"): {}
	            },
	            _("Stock Assets"): {
	                _("Stock In Hand"): {
	                    "account_type": "Stock"
	                },
	                "account_type": "Stock",
	            },
	            _("Tax Assets"): {
					"is_group": 1
				}
	        },
	        _("Fixed Assets"): {
	            _("Capital Equipments"): {
	                "account_type": "Fixed Asset"
	            },
	            _("Electronic Equipments"): {
	                "account_type": "Fixed Asset"
	            },
	            _("Furnitures and Fixtures"): {
	                "account_type": "Fixed Asset"
	            },
	            _("Office Equipments"): {
	                "account_type": "Fixed Asset"
	            },
	            _("Plants and Machineries"): {
	                "account_type": "Fixed Asset"
	            },
				_("Buildings"): {
					"account_type": "Fixed Asset"
				},
				_("Softwares"): {
					"account_type": "Fixed Asset"
				},
	            _("Accumulated Depreciation"): {
	            	"account_type": "Accumulated Depreciation"
	            },
                _("CWIP Account"): {
                    "account_type": "Capital Work in Progress",
                }
	        },
	        _("Investments"): {
	        	"is_group": 1
	        },
	        _("Temporary Accounts"): {
	            _("Temporary Opening"): {
	            	"account_type": "Temporary"
	            }
	        },
			"root_type": "Asset"
	    },
	    _("Expenses"): {
	        _("Direct Expenses"): {
	            _("Stock Expenses"): {
	                _("Cost of Goods Sold"): {
	                    "account_type": "Cost of Goods Sold"
	                },
                    _("Expenses Included In Asset Valuation"): {
                        "account_type": "Expenses Included In Asset Valuation"
                    },
	                _("Expenses Included In Valuation"): {
	                    "account_type": "Expenses Included In Valuation"
	                },
	                _("Stock Adjustment"): {
	                    "account_type": "Stock Adjustment"
	                }
	            },
	        },
	        _("Indirect Expenses"): {
	            _("Administrative Expenses"): {},
	            _("Commission on Sales"): {},
	            _("Depreciation"): {
	                "account_type": "Depreciation"
	            },
	            _("Entertainment Expenses"): {},
	            _("Freight and Forwarding Charges"): {
	                "account_type": "Chargeable"
	            },
	            _("Legal Expenses"): {},
	            _("Marketing Expenses"): {
	                "account_type": "Chargeable"
	            },
	            _("Miscellaneous Expenses"): {
	                "account_type": "Chargeable"
	            },
	            _("Office Maintenance Expenses"): {},
	            _("Office Rent"): {},
	            _("Postal Expenses"): {},
	            _("Print and Stationery"): {},
	            _("Round Off"): {
	                "account_type": "Round Off"
	            },
	            _("Salary"): {},
	            _("Sales Expenses"): {},
	            _("Telephone Expenses"): {},
	            _("Travel Expenses"): {},
	            _("Utility Expenses"): {},
				_("Write Off"): {},
				_("Exchange Gain/Loss"): {},
				_("Gain/Loss on Asset Disposal"): {}
	        },
			"root_type": "Expense"
	    },
	    _("Income"): {
	        _("Direct Income"): {
	            _("Sales"): {},
	            _("Service"): {}
	        },
	        _("Indirect Income"): {
				"is_group": 1
	        },
	        "root_type": "Income"
	    },
	    _("Source of Funds (Liabilities)"): {
	        _("Current Liabilities"): {
			    _("Accounts Payable"): {
			        _("Creditors"): {
			            "account_type": "Payable"
			        },
			        _("Payroll Payable"): {},
			    },
			    _("Stock Liabilities"): {
				    _("Stock Received But Not Billed"): {
				        "account_type": "Stock Received But Not Billed"
				    },
                    _("Asset Received But Not Billed"): {
                        "account_type": "Asset Received But Not Billed"
                    }
			    },
				_("Duties and Taxes"): {
					"account_type": "Tax",
					"is_group": 1
				},
				_("Loans (Liabilities)"): {
					_("Secured Loans"): {},
					_("Unsecured Loans"): {},
					_("Bank Overdraft Account"): {},
				},
	        },
			"root_type": "Liability"
	    },
		_("Equity"): {
	        _("Capital Stock"): {
	            "account_type": "Equity"
	        },
	        _("Dividends Paid"): {
	            "account_type": "Equity"
	        },
	        _("Opening Balance Equity"): {
	            "account_type": "Equity"
	        },
	        _("Retained Earnings"): {
	            "account_type": "Equity"
	        },
			"root_type": "Equity"
		}
	}
