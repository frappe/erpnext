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
"""
	All master data in one place, can be created by 1 function call

"""

import webnotes
from webnotes.model.doc import Document


master_groups = {
	# Company
	#----------------------------------
	'company': Document(
		fielddata={
			'doctype':'Company',
			'abbr': 'co',
			'company_name' : 'comp',
			'name': 'comp'
		}
	),
	
	# Customer Group
	#----------------------------------
	'customer_group':  Document(
		fielddata={
			'doctype':'Customer Group',
			'customer_group_name' : 'cg',
			'name': 'cg',
			'is_group': 'No',
			'parent_customer_group':'', 
			'lft' : 1,
			'rgt': 2
		}
	),
	
	# Item Group
	#----------------------------------
	'item_group': Document(
		fielddata = {
			'doctype': 'Item Group',
			'item_group_name': 'ig',
			'lft': 1,
			'rgt': 2,
			'parent_item_group' : '',
			'is_group': 'No',
			'name': 'ig'
		}
	),
	
	# Warehouse Type
	#-----------------------------
	'warehouse_type' : Document(
		fielddata = {
			'doctype' : 'Warehouse Type',
			'name': 'normal',
			'warehouse_type' : 'normal'
		}
	),
	
	# Supplier Type
	#-----------------------------
	'supplier_type' : Document(
		fielddata = {
			'doctype': 'Supplier Type',
			'supplier_type': 'stype'
		}
	)

}


main_masters = {
	# Customer
	#----------------------------------
	'customer': Document(
		fielddata={
			'doctype':'Customer',
			'docstatus':0,
			'customer_name' : 'cust',
			'company' : 'comp',
			'customer_group' : '',
			'name': 'cust'
		}
	),


	# Supplier
	#----------------------------------
	'supplier': Document(
		fielddata = {
			'doctype': 'Supplier',
			'supplier_name': 'supp',
			'name': 'supp',	
			'supplier_type' : 'stype'
		}
	),
	
	# Customer Account
	#----------------------------------
	'customer_acc': Document(
		fielddata={
			'doctype':'Account',
			'docstatus':0,
			'account_name' : 'cust',
			'debit_or_credit': 'Debit',
			'company' : 'comp',
			'lft': 1,
			'rgt': 2,
			'group_or_ledger' : 'Ledger',
			'is_pl_account': 'No',
			'name' : 'cust - co'
		}
	),
	
	# Customer Account
	#----------------------------------
	'supplier_acc': Document(
		fielddata={
			'doctype':'Account',
			'docstatus':0,
			'account_name' : 'supp',
			'debit_or_credit': 'Credit',
			'company' : 'comp',
			'lft': 5,
			'rgt': 6,
			'group_or_ledger' : 'Ledger',
			'is_pl_account': 'No',
			'name' : 'supp - co'
		}
	),	

	# Bank Account
	#----------------------------------
	'bank_acc': Document(
		fielddata={
			'doctype':'Account',
			'docstatus':0,
			'account_name' : 'icici',
			'parent_account': '',
			'debit_or_credit': 'Debit',
			'company' : 'comp',
			'lft': 3,
			'rgt': 4,
			'group_or_ledger' : 'Ledger',
			'is_pl_account': 'No',
			'name' : 'icici - co'
		}
	),

	# Income Account
	#----------------------------------
	'income_acc': Document(
		fielddata={
			'doctype':'Account',
			'docstatus':0,
			'account_name' : 'income',
			'debit_or_credit': 'Credit',
			'company' : 'comp',
			'lft': 7,
			'rgt': 8,
			'group_or_ledger' : 'Ledger',
			'is_pl_account': 'Yes',
			'name' : 'income - co'
		}
	),
	
	# Expense Account
	#----------------------------------
	'expense_acc': Document(
		fielddata={
			'doctype':'Account',
			'docstatus':0,
			'account_name' : 'expense',
			'debit_or_credit': 'Debit',
			'company' : 'comp',
			'lft': 9,
			'rgt': 10,
			'group_or_ledger' : 'Ledger',
			'is_pl_account': 'Yes',
			'name' : 'expense - co'
		}
	),

	# Cost Center
	#----------------------------------
	'cost_center': Document(
		fielddata={
			'doctype':'Cost Center',
			'docstatus':0,
			'cost_center_name' : 'cc',
			'lft': 1,
			'rgt': 2,
			'group_or_ledger' : 'Ledger',
			'name' : 'cc'
		}
	),

	# Item
	#----------------------------------
	# Stock item / non-serialized

	'item': [
		Document(
			fielddata = {
				'doctype': 'Item',
				'docstatus': 0,
				'name': 'it',
				'item_name': 'it',
				'item_code': 'it',
				'item_group': 'ig',
				'is_stock_item': 'Yes',
				'has_serial_no': 'Yes',
				'stock_uom': 'Nos',
				'is_sales_item': 'Yes',
				'is_purchase_item': 'Yes',
				'is_service_item': 'No',
				'is_sub_contracted_item': 'No',
				'is_pro_applicable': 'Yes',
				'is_manufactured_item': 'Yes'		
			}
		),
		Document(
			fielddata = {
				'doctype': 'Item Price',
				'parentfield': 'ref_rate_details',
				'parenttype': 'Item',
				'parent' : 'it',
				'price_list_name': 'pl',
				'ref_currency': 'INR',
				'ref_rate': 100
			}
		),
		Document(
			fielddata = {
				'doctype': 'Item Tax',
				'parentfield': 'item_tax',
				'parenttype': 'Item',
				'parent' : 'it',
				'tax_type' : 'Tax1',
				'tax_rate': 10
			}
		)
	],
	
	# Warehouse
	#-----------------------------
	'warehouse': [
		Document(
			fielddata = {
				'doctype': 'Warehouse',
				'name' : 'wh1',
				'warehouse_name' : 'wh1',
				'warehouse_type': 'normal',
				'company': 'comp'
			}
		),
		Document(
			fielddata = {
				'doctype': 'Warehouse',
				'name' : 'wh2',
				'warehouse_name' : 'wh2',
				'warehouse_type': 'normal',
				'company': 'comp'
			}
		)
	]
}



# Save all master records
#----------------------------------
def create_master_records():
	for m in master_groups.keys():
		master_groups[m].save(1)

	for m in main_masters.keys():
		if type(main_masters[m]) == list:
			for each in main_masters[m]:
				each.save(1)
		else:
			main_masters[m].save(1)
