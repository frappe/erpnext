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
from frappe.utils import flt, cint, money_in_words

class CoalRaisingInvoice(AccountsController):
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_data()
		self.cal_total_amount()
		self.set_status()

	def on_submit(self):
		self.make_gl_entry()
		self.post_journal_entry()

	def on_cancel(self):
		self.make_gl_entry()

	def set_status(self, update=False, status=None, update_modified=True):
		return
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
				AND NOT EXISTS (SELECT crp.name,crp.branch FROM `tabCoal Raising Invoice` crp
					INNER JOIN `tabCoal Raising Payment Items` cri
					ON crp.name = cri.parent
					WHERE crp.branch = '{0}' AND crp.docstatus = 1
					AND crp.from_date BETWEEN '{1}' AND '{2}'
					AND crp.to_date BETWEEN '{1}' AND '{2}'
					AND cri.mineral_raising_group = '{3}' AND cri.tier = '{4}')
				AND warehouse = '{5}'
			""".format(self.branch,self.from_date,self.to_date,self.mineral_raising_group,self.tier, self.warehouse),as_dict=True)
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

	@frappe.whitelist()
	def post_journal_entry(self):
		if self.journal_entry and frappe.db.exists("Journal Entry",{"name":self.journal_entry,"docstatus":("!=",2)}):
			frappe.msgprint(_("Journal Entry Already Exists {}".format(frappe.get_desk_link("Journal Entry",self.journal_entry))))
		if not self.total_amount:
			frappe.throw(_("Payable Amount should be greater than zero"))
			
		# default_ba = get_default_ba()

		credit_account = self.credit_account
	
		if not credit_account:
			frappe.throw("Expense Account is mandatory")
		r = []
		if self.remarks:
			r.append(_("Note: {0}").format(self.remarks))

		remarks = ("").join(r) #User Remarks is not mandatory
		bank_account = frappe.db.get_value("Company",self.company, "default_bank_account")
		if not bank_account:
			frappe.throw(_("Default bank account is not set in company {}".format(frappe.bold(self.company))))
		# Posting Journal Entry
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"naming_series": "Bank Payment Voucher",
			"title": "Coal Raising Payment "+ self.supplier,
			"user_remark": "Note: " + "Transporter Payment - " + self.supplier,
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.total_amount),
			"branch": self.branch,
			"reference_type":self.doctype,
			"referece_doctype":self.name
		})
		je.append("accounts",{
			"account": credit_account,
			"debit_in_account_currency": self.total_amount,
			"cost_center": self.cost_center,
			"party_check": 1,
			"party_type": "Supplier",
			"party": self.supplier,
			"reference_type": self.doctype,
			"reference_name": self.name
		})
		je.append("accounts",{
			"account": bank_account,
			"credit_in_account_currency": self.total_amount,
			"cost_center": self.cost_center
		})

		je.insert()
		#Set a reference to the claim journal entry
		self.db_set("journal_entry",je.name)
		frappe.msgprint(_('Journal Entry {0} posted to accounts').format(frappe.get_desk_link("Journal Entry",je.name)))

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