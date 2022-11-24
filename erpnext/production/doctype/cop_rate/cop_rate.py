# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class COPRate(Document):
	pass

@frappe.whitelist()
def get_cop_rate(item_code,posting_date,cop_list,uom=None):
	if not cop_list:
		frappe.throw('COP List is mandatory')
	return frappe.db.sql('''select rate
					from `tabCOP Rate` where disabled=0 
					and item_code = '{item_code}'
					and valid_from <= '{posting_date}' 
					and (case when valid_up_to then valid_up_to >= '{posting_date}' else '{posting_date}' <= '2099-12-31' end)
					and (case when '{uom}' then uom = '{uom}' else 1 = 1 end)
					and cop_list = '{cop_list}'
					order by valid_from desc
					limit 1
					'''.format(item_code = item_code, posting_date = posting_date, uom=uom, cop_list=cop_list),as_dict=1)