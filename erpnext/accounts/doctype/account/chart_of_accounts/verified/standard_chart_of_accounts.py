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
	            	"is_group": 1
	            },
	            _("Securities and Deposits"): {
	                _("Earnest Money"): {}
	            },
	            _("Stock Assets"): {
	                "account_type": "Stock",
					"is_group": 1
	            },
	            _("Tax Assets"): {
					"is_group": 1
				}
	        },
	        _("Fixed Assets"): {
	            _("Capital Equipments"): {
	                "account_type": "Fixed Asset"
	            },
	            _("Computers"): {
	                "account_type": "Fixed Asset"
	            },
	            _("Furniture and Fixture"): {
	                "account_type": "Fixed Asset"
	            },
	            _("Office Equipments"): {
	                "account_type": "Fixed Asset"
	            },
	            _("Plant and Machinery"): {
	                "account_type": "Fixed Asset"
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
	                    "account_type": "Expense Account"
	                },
	                _("Expenses Included In Valuation"): {
	                    "account_type": "Expenses Included In Valuation"
	                },
	                _("Stock Adjustment"): {
	                    "account_type": "Stock Adjustment"
	                },
	                "account_type": "Expense Account"
	            },
	            "account_type": "Expense Account"
	        },
	        _("Indirect Expenses"): {
	            _("Administrative Expenses"): {
	                "account_type": "Expense Account"
	            },
	            _("Commission on Sales"): {
	                "account_type": "Expense Account"
	            },
	            _("Depreciation"): {
	                "account_type": "Expense Account"
	            },
	            _("Entertainment Expenses"): {
	                "account_type": "Expense Account"
	            },
	            _("Freight and Forwarding Charges"): {
	                "account_type": "Chargeable"
	            },
	            _("Legal Expenses"): {
	                "account_type": "Expense Account"
	            },
	            _("Marketing Expenses"): {
	                "account_type": "Chargeable"
	            },
	            _("Miscellaneous Expenses"): {
	                "account_type": "Chargeable"
	            },
	            _("Office Maintenance Expenses"): {
	                "account_type": "Expense Account"
	            },
	            _("Office Rent"): {
	                "account_type": "Expense Account"
	            },
	            _("Postal Expenses"): {
	                "account_type": "Expense Account"
	            },
	            _("Print and Stationary"): {
	                "account_type": "Expense Account"
	            },
	            _("Round Off"): {
	                "account_type": "Round Off"
	            },
	            _("Salary"): {
	                "account_type": "Expense Account"
	            },
	            _("Sales Expenses"): {
	                "account_type": "Expense Account"
	            },
	            _("Telephone Expenses"): {
	                "account_type": "Expense Account"
	            },
	            _("Travel Expenses"): {
	                "account_type": "Expense Account"
	            },
	            _("Utility Expenses"): {
	                "account_type": "Expense Account"
	            },
	            "account_type": "Expense Account"
	        },
			"root_type": "Expense"
	    },
	    _("Income"): {
	        _("Direct Income"): {
	            _("Sales"): {
	                "account_type": "Income Account"
	            },
	            _("Service"): {
	                "account_type": "Income Account"
	            },
	            "account_type": "Income Account"
	        },
	        _("Indirect Income"): {
	            "account_type": "Income Account",
				"is_group": 1
	        },
			"root_type": "Income"
	    },
	    _("Source of Funds (Liabilities)"): {
	        _("Current Liabilities"): {
			    _("Accounts Payable"): {
			        _("Creditors"): {
			            "account_type": "Payable"
			        }
			    },
			    _("Stock Liabilities"): {
				    _("Stock Received But Not Billed"): {
				        "account_type": "Stock Received But Not Billed"
				    },
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
