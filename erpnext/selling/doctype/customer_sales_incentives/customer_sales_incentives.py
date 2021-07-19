# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CustomerSalesIncentives(Document):
	@frappe.whitelist()
	def get_item_list(self):
		a=[]
		doc=frappe.db.sql("""select i.item_code from `tabItem` i where i.is_sales_item=1""",as_dict=1)
		for i in doc:
			a.append(i.item_code)
		return a
