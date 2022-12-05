# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, nowdate, getdate, date_diff

class COP(Document):
	def validate(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw("From Date Cannot be greater than To Date")	
		self.check_duplicate()

	def check_duplicate(self):
		cop_list = frappe.db.sql("""select count(name) tot 
				from `tabCOP` 
				where cost_center = "{0}" 
				and name != '{3}' 
				and ('{1}' between from_date 
				and to_date or '{2}' between from_date 
				and to_date or ('{1}' > from_date 
				and '{2}' < to_date) or ('{1}' < from_date and '{2}' > to_date)) 
			""".format(self.cost_center, self.from_date, self.to_date, self.name), as_dict = 1)
			
		if cint(cop_list[0].tot) > 0:
			frappe.throw("COP for '{0}' Already exists".format(self.cost_center))
		found = []
		to_remove = []
		tot = 0.0
		for a in self.get('items'):
			tot = flt(a.mining_expenses) + flt(a.crushing_plant_expenses1) + flt(a.crushing_plant_expenses2) + flt(a.washed_expenses) + flt(a.transportation) + flt(a.s_and_d)
			if flt(tot) > 100:
				frappe.throw("Sum Of Percent Cannot Exceed 100%")
			if flt(a.mining_expenses)  > 100 \
				or flt(a.crushing_plant_expenses1) > 100 \
				or flt(a.crushing_plant_expenses2) > 100 \
				or flt(a.washed_expenses) > 100 \
				or flt(a.transportation)> 100 \
				or flt(a.s_and_d) > 100:
				frappe.throw("Percent Cannot Exceed 100% at Row '{0}'".format(a.idx))

			if a.account in found:
				frappe.throw("Duplicate Account '{0}' Entered at Row <b> {1} </b>".format(a.account, a.idx))
			# else:
			# 	found.append(a.account)
			# 	if flt(tot) == 0.0:
			# 		to_remove.append(a)
        	# if to_remove:
			# 	[self.remove(d) for d in to_remove]

	@frappe.whitelist()
	def get_accounts(self):
		query = "select name as account from `tabAccount` where account_type = 'Expense Account' and is_group = 0 and company = \'" + str(self.company) + "\' and (freeze_account is null or freeze_account != 'Yes') order by name ASC"
		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', [])

		for d in entries:
			row = self.append('items', {})
			row.update(d)