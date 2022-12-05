# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint
from frappe.model.document import Document
from erpnext.custom_utils import check_future_date
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

class CoalRaisingPayment(Document):
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_data()
		self.cal_total_amount()
		# if self.workflow_state != "Approved":
		# 	notify_workflow_states(self)

	def on_submit(self):
		self.post_journal_entry()
		# notify_workflow_states(self)

	def validate_data(self):
		if self.from_date > self.to_date:
			frappe.throw('From Date cannot be after To Date')

	def before_cancel(self):
		cl_status = frappe.db.get_value("Journal Entry", self.claim_journal, "docstatus")
		if flt(cl_status) < 2:
			frappe.throw("You need to cancel the claim journal entry first!")

	@frappe.whitelist()
	def get_coal_raising_details(self):
		data = []
		for d in frappe.db.sql("""
			SELECT
				DISTINCT mineral_raising_group,tier
			FROM `tabProduction` 
			WHERE branch = '{}' 
			AND posting_date 
			BETWEEN '{}' AND '{}' 
			AND docstatus = 1 
			AND (coal_raising_type != '' or coal_raising_type is not null)
			AND ( mineral_raising_group !='' or mineral_raising_group is not null)
		""".format(self.branch,self.from_date,self.to_date),as_dict=True):
			if d.mineral_raising_group:
				data1 = frappe.db.sql("""
						SELECT coal_raising_type,
							no_of_labours,amount,machine_payable,
							machine_hours,product_qty,grand_amount,penalty_amount
						FROM `tabProduction`
						WHERE branch = '{0}' AND docstatus = 1
						AND posting_date BETWEEN '{1}' AND '{2}'
						AND mineral_raising_group = '{3}' AND tier = '{4}'
						AND NOT EXISTS (SELECT crp.name,crp.branch FROM `tabCoal Raising Payment` crp
							INNER JOIN `tabCoal Raising Payment Items` cri
							ON crp.name = cri.parent
							WHERE crp.branch = '{0}' AND crp.docstatus = 1
							AND crp.from_date BETWEEN '{1}' AND '{2}'
							AND crp.to_date BETWEEN '{1}' AND '{2}'
							AND cri.group_name = '{3}' AND cri.tier = '{4}')
					""".format(self.branch,self.from_date,self.to_date,d.mineral_raising_group,d.tier),as_dict=True)
				if data1:
					data.append(self.calculation(data1,d.mineral_raising_group,d.tier))

		if not data:
			frappe.throw("Payment for Groups involved in production within <b>{0}</b> and <b>{1}</b> is already done".format(self.from_date,self.to_date))

		items = self.set('items',[])
		for d in data:
			row = self.append('items',{})
			row.update(d)

	def calculation(self, data, mineral_raising_group, tier):
		row = {}
		row['total_amount'] 		= 0
		row['manual_qty'] 			= 0
		row['machine_qty'] 			= 0
		row['machine_sharing_qty'] 	= 0
		row['machine_payable'] 		= 0
		row['no_labour'] 			= 0
		row['total_penalty'] 		= 0
		row['grand_total'] 			= 0
		amount = 0
		for d in data:

			if d.coal_raising_type == 'Manual':
				row['no_labour'] 		+= flt(d.no_of_labours)
				row['manual_qty'] 		+= flt(d.product_qty)
				amount 					+= flt(d.amount)
				row['total_penalty'] 	+= flt(d.penalty_amount)
				row['grand_total'] 		+= flt(d.grand_amount)

			elif d.coal_raising_type == 'Machine Sharing':
				row['no_labour'] 			+= flt(d.no_of_labours)
				row['machine_sharing_qty'] 	+= flt(d.product_qty)
				row['machine_payable'] 		+= flt(d.machine_payable)
				amount 						+= flt(d.amount)
				row['total_penalty'] 		+= flt(d.penalty_amount)
				row['grand_total'] 			+= flt(d.grand_amount)

			elif d.coal_raising_type == 'SMCL Machine':
				row['machine_qty'] += flt(d.product_qty)

		row['total_amount'] 			+= flt(amount)
		row['mineral_raising_group'] 	= mineral_raising_group		
		row['tier'] 					= tier
		row['total_quantity'] 			= flt(row['manual_qty']) + flt(row['machine_qty']) + flt(row['machine_sharing_qty'])
		return row

	def cal_total_amount(self):
		total_production = total_amount = grand_total = total_penalty = deduction_amount = 0
		for item in self.items:
			# deduction_amount = flt(item.deduction_amount)
			# item.total_amount = flt(item.total_amount) - flt(item.deduction_amount)
			total_production += flt(item.total_quantity)
			total_amount += flt(item.total_amount)
			grand_total += flt(item.grand_total)
			total_penalty += flt(item.total_penalty)

		self.total_production = total_production
		self.total_amount = total_amount
		self.total_cost = flt(total_amount) / flt(total_production)
		self.grand_total = grand_total
		self.total_penalty = total_penalty
		# self.total_deduction= deduction_amount

	def post_journal_entry(self):
		credit_acc,debit_acc,penalty_acc = frappe.db.get_value('Company',self.company,['coal_raising_penalty_account','coal_raising_expense_account','coal_raising_penalty_account'])
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		je.title = "Coal Raising Payment (" + self.branch + "  " + self.name + ")"
		je.voucher_type = 'Bank Entry'
		je.naming_series = 'Bank Payment Voucher'
		je.remark = 'Claim payment against : ' + self.name
		je.posting_date = self.posting_date
		je.branch = self.branch

		je.append("accounts", {
				"account": debit_acc,
				"reference_type": "Coal Raising Payment",
				"reference_name": self.name,
				"cost_center": self.cost_center,
				"debit_in_account_currency": flt(self.grand_total),
				"debit": flt(self.grand_total)
			})

		je.append("accounts", {
				"account": credit_acc,
				# "party_type": "Employee",
				# "party": self.employee,
				"reference_type": "Coal Raising Payment",
				"reference_name": self.name,
				"cost_center": self.cost_center,
				"credit_in_account_currency": flt(self.total_amount),
				"credit": flt(self.total_amount)
			})
		if self.total_penalty:
			je.append("accounts", {
				"account": penalty_acc,
				"reference_type": "Coal Raising Payment",
				"reference_name": self.name,
				"cost_center": self.cost_center,
				"credit_in_account_currency": flt(self.total_penalty),
				"credit": flt(self.total_penalty),
			})

		je.insert()
		#Set a reference to the claim journal entry
		self.db_set("claim_journal",je.name)