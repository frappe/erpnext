# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

# mappings for table dumps
# "remember to add indexes!"

data_map = {
	"Company": {
		"columns": ["name"],
		"conditions": ["docstatus < 2"]
	},
	"Fiscal Year": {
		"columns": ["name", "year_start_date", 
			"adddate(adddate(year_start_date, interval 1 year), interval -1 day) as year_end_date"],
		"conditions": ["docstatus < 2"],
	},

	# Accounts
	"Account": {
		"columns": ["name", "parent_account", "lft", "rgt", "debit_or_credit", 
			"is_pl_account", "company", "group_or_ledger"],
		"conditions": ["docstatus < 2"],
		"order_by": "lft",
		"links": {
			"company": ["Company", "name"],
		}
		
	},
	"Cost Center": {
		"columns": ["name", "lft", "rgt"],
		"conditions": ["docstatus < 2"],
		"order_by": "lft"
	},
	"GL Entry": {
		"columns": ["account", "posting_date", "cost_center", "debit", "credit", "is_opening",
			"company", "voucher_type", "voucher_no", "remarks"],
		"conditions": ["ifnull(is_cancelled, 'No')='No'"],
		"order_by": "posting_date, account",
		"links": {
			"account": ["Account", "name"],
			"company": ["Company", "name"],
			"cost_center": ["Cost Center", "name"]
		}
	},

	# Stock
	"Item": {
		"columns": ["name", "if(item_name=name, '', item_name) as item_name", 
			"item_group as parent_item_group", "stock_uom", "brand", "valuation_method"],
		"conditions": ["docstatus < 2"],
		"order_by": "name",
		"links": {
			"parent_item_group": ["Item Group", "name"],
		}
	},
	"Item Group": {
		"columns": ["name", "parent_item_group"],
		"conditions": ["docstatus < 2"],
		"order_by": "lft"
	},
	"Warehouse": {
		"columns": ["name"],
		"conditions": ["docstatus < 2"],
		"order_by": "name"
	},
	"Stock Ledger Entry": {
		"columns": ["posting_date", "posting_time", "item_code", "warehouse", "actual_qty as qty",
			"voucher_type", "voucher_no", "ifnull(incoming_rate,0) as incoming_rate"],
		"conditions": ["ifnull(is_cancelled, 'No')='No'"],
		"order_by": "posting_date, posting_time, name",
		"links": {
			"item_code": ["Item", "name"],
			"warehouse": ["Warehouse", "name"]
		},
		"force_index": "posting_sort_index"		
	},

	# Sales
	"Customer": {
		"columns": ["name", "if(customer_name=name, '', customer_name) as customer_name", 
			"customer_group as parent_customer_group", "territory as parent_territory"],
		"conditions": ["docstatus < 2"],
		"order_by": "name",
		"links": {
			"parent_customer_group": ["Customer Group", "name"],
			"parent_territory": ["Territory", "name"],
		}
	},
	"Customer Group": {
		"columns": ["name", "parent_customer_group"],
		"conditions": ["docstatus < 2"],
		"order_by": "lft"
	},
	"Territory": {
		"columns": ["name", "parent_territory"],
		"conditions": ["docstatus < 2"],
		"order_by": "lft"
	},
	"Sales Invoice": {
		"columns": ["name", "customer", "posting_date", "company"],
		"conditions": ["docstatus=1"],
		"order_by": "posting_date",
		"links": {
			"customer": ["Customer", "name"],
			"company":["Company", "name"]
		}
	},
	"Sales Invoice Item": {
		"columns": ["parent", "item_code", "qty", "amount"],
		"conditions": ["docstatus=1", "ifnull(parent, '')!=''"],
		"order_by": "parent",
		"links": {
			"parent": ["Sales Invoice", "name"],
			"item_code": ["Item", "name"]
		}
	},
	"Supplier": {
		"columns": ["name", "if(supplier_name=name, '', supplier_name) as supplier_name", 
			"supplier_type as parent_supplier_type"],
		"conditions": ["docstatus < 2"],
		"order_by": "name",
		"links": {
			"parent_supplier_type": ["Supplier Type", "name"],
		}
	},
	"Supplier Type": {
		"columns": ["name"],
		"conditions": ["docstatus < 2"],
		"order_by": "name"
	},
	"Purchase Invoice": {
		"columns": ["name", "supplier", "posting_date", "company"],
		"conditions": ["docstatus=1"],
		"order_by": "posting_date",
		"links": {
			"supplier": ["Supplier", "name"],
			"company":["Company", "name"]
		}
	},
	"Purchase Invoice Item": {
		"columns": ["parent", "item_code", "qty", "amount"],
		"conditions": ["docstatus=1", "ifnull(parent, '')!=''"],
		"order_by": "parent",
		"links": {
			"parent": ["Purchase Invoice", "name"],
			"item_code": ["Item", "name"]
		}
	}
	
}
