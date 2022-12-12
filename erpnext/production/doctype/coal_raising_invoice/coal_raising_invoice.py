# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.utils import flt, cint
from frappe.model.document import Document
from erpnext.custom_utils import check_future_date
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
from erpnext.controllers.accounts_controller import AccountsController

class CoalRaisingInvoice(AccountsController):
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_data()
		self.cal_total_amount()
		self.set_status()

	def on_submit(self):
		self.make_gl_entry()
	def on_cancel(self):
		self.make_gl_entry()

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get("amended_from"):
				self.status = "Draft"
			return

		outstanding_amount = flt(self.outstanding_amount, self.precision("outstanding_amount"))
		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if outstanding_amount > 0 and self.total_amount > outstanding_amount:
					self.status = "Partly Paid"
				elif outstanding_amount > 0 :
					self.status = "Unpaid"
				elif outstanding_amount <= 0:
					self.status = "Paid"
				else:
					self.status = "Submitted"
			else:
				self.status = "Draft"

		if update:
			self.db_set("status", self.status, update_modified=update_modified)

	def validate_data(self):
		if self.from_date > self.to_date:
			frappe.throw('From Date cannot be after To Date')

	@frappe.whitelist()
	def get_coal_raising_details(self):
		data = []
		if not self.mineral_raising_group or not self.tier:
			frappe.throw(_("Mineral Raising Group or Tier is Missing"))
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
			""".format(self.branch,self.from_date,self.to_date,self.mineral_raising_group,self.tier),as_dict=True)
		if data1:
			data.append(self.calculation(data1,self.mineral_raising_group,self.tier))

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
			total_production += flt(item.total_quantity)
			total_amount += flt(item.total_amount)
			grand_total += flt(item.grand_total)
			total_penalty += flt(item.total_penalty)

		self.total_production = total_production
		self.outstanding_amount = self.total_amount = total_amount
		self.total_cost = flt(total_amount) / flt(total_production)
		self.grand_total = grand_total
		self.total_penalty = total_penalty

	def make_gl_entry(self):
		from erpnext.accounts.general_ledger import make_gl_entries
		gl_entries = []
		ba = get_default_ba()

		debit_acc,penalty_acc = frappe.db.get_value('Company',self.company,['coal_raising_expense_account','coal_raising_penalty_account'])
		gl_entries.append(
			self.get_gl_dict({
				"account": debit_acc,
				"debit": flt(self.grand_total,2),
				"debit_in_account_currency": flt(self.grand_total,2),
				"voucher_no": self.name,
				"voucher_type": self.doctype,
				"cost_center": self.cost_center,
				"business_activity": ba,
			}, self.currency)
		)
		gl_entries.append(
			self.get_gl_dict({
				"account": self.credit_account,
				"party_type": "Supplier",
				"party": self.supplier,
				"credit": flt(self.total_amount,2),
				"credit_in_account_currency": flt(self.total_amount,2),
				"business_activity": ba,
				"cost_center": self.cost_center,
				"voucher_no":self.name,
				"voucher_type":self.doctype,
				"against_voucher":self.name,
				"against_voucher_type":self.doctype
			}, self.currency)
		)
		if self.total_penalty:
			gl_entries.append(
				self.get_gl_dict({
					"account": penalty_acc,
					"credit": flt(self.total_penalty,2),
					"credit_in_account_currency": flt(self.total_penalty,2),
					"business_activity": ba,
					"cost_center": self.cost_center,
					"voucher_no":self.name,
					"voucher_type":self.doctype,
					"against_voucher":self.name,
					"against_voucher_type":self.doctype
				}, self.currency)
			)
		make_gl_entries(gl_entries, update_outstanding="No", cancel=(self.docstatus == 2), merge_entries=False)