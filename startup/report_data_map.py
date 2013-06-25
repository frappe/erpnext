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
		"columns": ["name", "account", "posting_date", "cost_center", "debit", "credit", 
			"is_opening", "company", "voucher_type", "voucher_no", "remarks"],
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
		"columns": ["name", "if(item_name=name, '', item_name) as item_name", "description", 
			"item_group as parent_item_group", "stock_uom", "brand", "valuation_method", 
			"re_order_level", "re_order_qty"],
		# "conditions": ["docstatus < 2"],
		"order_by": "name",
		"links": {
			"parent_item_group": ["Item Group", "name"],
			"brand": ["Brand", "name"]
		}
	},
	"Item Group": {
		"columns": ["name", "parent_item_group"],
		# "conditions": ["docstatus < 2"],
		"order_by": "lft"
	},
	"Brand": {
		"columns": ["name"],
		"conditions": ["docstatus < 2"],
		"order_by": "name"
	},
	"Project": {
		"columns": ["name"],
		"conditions": ["docstatus < 2"],
		"order_by": "name"
	},
	"Warehouse": {
		"columns": ["name"],
		"conditions": ["docstatus < 2"],
		"order_by": "name"
	},
	"Stock Ledger Entry": {
		"columns": ["name", "posting_date", "posting_time", "item_code", "warehouse", 
			"actual_qty as qty", "voucher_type", "voucher_no", "project",
			"ifnull(incoming_rate,0) as incoming_rate", "stock_uom", "serial_no"],
		"conditions": ["ifnull(is_cancelled, 'No')='No'"],
		"order_by": "posting_date, posting_time, name",
		"links": {
			"item_code": ["Item", "name"],
			"warehouse": ["Warehouse", "name"],
			"project": ["Project", "name"]
		},
		"force_index": "posting_sort_index"
	},
	"Stock Entry": {
		"columns": ["name", "purpose"],
		"conditions": ["docstatus=1"],
		"order_by": "posting_date, posting_time, name",
	},
	"Production Order": {
		"columns": ["name", "production_item as item_code", 
			"(ifnull(qty, 0) - ifnull(produced_qty, 0)) as qty", 
			"fg_warehouse as warehouse"],
		"conditions": ["docstatus=1", "status != 'Stopped'", "ifnull(fg_warehouse, '')!=''",
			"ifnull(qty, 0) > ifnull(produced_qty, 0)"],
		"links": {
			"item_code": ["Item", "name"],
			"warehouse": ["Warehouse", "name"]
		},
	},
	"Material Request Item": {
		"columns": ["item.name as name", "item_code", "warehouse", 
			"(ifnull(qty, 0) - ifnull(ordered_qty, 0)) as qty"],
		"from": "`tabMaterial Request Item` item, `tabMaterial Request` main",
		"conditions": ["item.parent = main.name", "main.docstatus=1", "main.status != 'Stopped'",
			"ifnull(warehouse, '')!=''", "ifnull(qty, 0) > ifnull(ordered_qty, 0)"],
		"links": {
			"item_code": ["Item", "name"],
			"warehouse": ["Warehouse", "name"]
		},
	},
	"Purchase Order Item": {
		"columns": ["item.name as name", "item_code", "warehouse", 
			"(ifnull(qty, 0) - ifnull(received_qty, 0)) as qty"],
		"from": "`tabPurchase Order Item` item, `tabPurchase Order` main",
		"conditions": ["item.parent = main.name", "main.docstatus=1", "main.status != 'Stopped'", 
			"ifnull(warehouse, '')!=''", "ifnull(qty, 0) > ifnull(received_qty, 0)"],
		"links": {
			"item_code": ["Item", "name"],
			"warehouse": ["Warehouse", "name"]
		},
	},
	
	"Sales Order Item": {
		"columns": ["item.name as name", "item_code", "(ifnull(qty, 0) - ifnull(delivered_qty, 0)) as qty", 
			"reserved_warehouse as warehouse"],
		"from": "`tabSales Order Item` item, `tabSales Order` main",
		"conditions": ["item.parent = main.name", "main.docstatus=1", "main.status != 'Stopped'", 
			"ifnull(reserved_warehouse, '')!=''", "ifnull(qty, 0) > ifnull(delivered_qty, 0)"],
		"links": {
			"item_code": ["Item", "name"],
			"warehouse": ["Warehouse", "name"]
		},
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
		"columns": ["name", "parent", "item_code", "qty", "amount"],
		"conditions": ["docstatus=1", "ifnull(parent, '')!=''"],
		"order_by": "parent",
		"links": {
			"parent": ["Sales Invoice", "name"],
			"item_code": ["Item", "name"]
		}
	},
	"Sales Order": {
		"columns": ["name", "customer", "transaction_date as posting_date", "company"],
		"conditions": ["docstatus=1"],
		"order_by": "transaction_date",
		"links": {
			"customer": ["Customer", "name"],
			"company":["Company", "name"]
		}
	},
	"Sales Order Item[Sales Analytics]": {
		"columns": ["name", "parent", "item_code", "qty", "amount"],
		"conditions": ["docstatus=1", "ifnull(parent, '')!=''"],
		"order_by": "parent",
		"links": {
			"parent": ["Sales Order", "name"],
			"item_code": ["Item", "name"]
		}
	},
	"Delivery Note": {
		"columns": ["name", "customer", "posting_date", "company"],
		"conditions": ["docstatus=1"],
		"order_by": "posting_date",
		"links": {
			"customer": ["Customer", "name"],
			"company":["Company", "name"]
		}
	},
	"Delivery Note Item[Sales Analytics]": {
		"columns": ["name", "parent", "item_code", "qty", "amount"],
		"conditions": ["docstatus=1", "ifnull(parent, '')!=''"],
		"order_by": "parent",
		"links": {
			"parent": ["Delivery Note", "name"],
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
		"columns": ["name", "parent", "item_code", "qty", "amount"],
		"conditions": ["docstatus=1", "ifnull(parent, '')!=''"],
		"order_by": "parent",
		"links": {
			"parent": ["Purchase Invoice", "name"],
			"item_code": ["Item", "name"]
		}
	},
	"Purchase Order": {
		"columns": ["name", "supplier", "transaction_date as posting_date", "company"],
		"conditions": ["docstatus=1"],
		"order_by": "posting_date",
		"links": {
			"supplier": ["Supplier", "name"],
			"company":["Company", "name"]
		}
	},
	"Purchase Order Item[Purchase Analytics]": {
		"columns": ["name", "parent", "item_code", "qty", "amount"],
		"conditions": ["docstatus=1", "ifnull(parent, '')!=''"],
		"order_by": "parent",
		"links": {
			"parent": ["Purchase Order", "name"],
			"item_code": ["Item", "name"]
		}
	},
	"Purchase Receipt": {
		"columns": ["name", "supplier", "posting_date", "company"],
		"conditions": ["docstatus=1"],
		"order_by": "posting_date",
		"links": {
			"supplier": ["Supplier", "name"],
			"company":["Company", "name"]
		}
	},
	"Purchase Receipt Item[Purchase Analytics]": {
		"columns": ["name", "parent", "item_code", "qty", "amount"],
		"conditions": ["docstatus=1", "ifnull(parent, '')!=''"],
		"order_by": "parent",
		"links": {
			"parent": ["Purchase Receipt", "name"],
			"item_code": ["Item", "name"]
		}
	},
	# Support
	"Support Ticket": {
		"columns": ["name","status","creation","resolution_date","first_responded_on"],
		"conditions": ["docstatus < 2"],
		"order_by": "creation"
	}
	
}
