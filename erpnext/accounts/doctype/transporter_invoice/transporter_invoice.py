# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe import _, qb, throw
from erpnext.custom_utils import check_future_date
from erpnext.controllers.accounts_controller import AccountsController
from pypika import Case, functions as fn
from erpnext.production.doctype.transporter_rate.transporter_rate import get_transporter_rate
from frappe.utils import flt, cint
from erpnext.accounts.utils import get_tds_account,get_account_type
from erpnext.accounts.general_ledger import (
	get_round_off_account_and_cost_center,
	make_gl_entries,
	make_reverse_gl_entries,
	merge_similar_entries,
)
import operator, math
from erpnext.accounts.party import get_party_account

class TransporterInvoice(AccountsController):
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_dates()
		self.calculate_total()
		self.set_status()

	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		self.make_gl_entries()

	def validate_dates(self):
		if self.from_date > self.to_date:
			throw("From Date cannot be grater than To Date",title="Invalid Dates")
		if not self.remarks:
			self.remarks = "Payment for {0}".format(self.equipment)
		
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
				if outstanding_amount > 0 and self.amount_payable > outstanding_amount:
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

	def make_gl_entries(self):
		gl_entries = []
		self.make_supplier_gl_entry(gl_entries)
		self.make_item_gl_entries(gl_entries)
		self.unloading_gl_entries(gl_entries)
		self.deduction_gl_entries(gl_entries)
		gl_entries = merge_similar_entries(gl_entries)
		make_gl_entries(gl_entries,update_outstanding="No",cancel=self.docstatus == 2)
	def make_supplier_gl_entry(self, gl_entries):
		if flt(self.amount_payable) > 0:
			# Did not use base_grand_total to book rounding loss gle
			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_account,
					"credit": self.amount_payable,
					"credit_in_account_currency": self.amount_payable,
					"against_voucher": self.name,
					"party_type": "Supplier",
					"party": self.supplier,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center,
					"voucher_type":self.doctype,
					"voucher_no":self.name
				}, self.currency))

	def make_item_gl_entries(self, gl_entries):
		items = self.get_expense_gl()

		for k,v in items.items():
			party_type = party = ''
			if  get_account_type( k, self.company) in ["Receivable","Payable"]:
				party_type = "Supplier"
				party = self.supplier

			gl_entries.append(
				self.get_gl_dict({
						"account":  k,
						"debit": flt(v),
						"debit_in_account_currency": flt(v),
						"against_voucher": self.name,
						"against_voucher_type": self.doctype,
						"party_type": party_type,
						"party": party,
						"cost_center": self.cost_center,
						"voucher_type":self.doctype,
						"voucher_no":self.name
				}, self.currency)
			)

	def unloading_gl_entries(self,gl_entries):
		if flt(self.unloading_amount):
			party = party_type = None
			account_type = get_account_type("Account", self.unloading_account)
			if account_type == "Receivable" or account_type == "Payable":
				party = self.supplier
				party_type = "Supplier"

			gl_entries.append(
				self.get_gl_dict({
					"account":  self.unloading_account,
					"debit": self.unloading_amount,
					"debit_in_account_currency": self.unloading_amount,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"party_type": party_type,
					"party": party,
					"cost_center": self.cost_center,
					"reference_no": self.cheque_no,
					"reference_date": self.cheque_date,
					"equipment_number": self.registration_no
				}, self.currency)
			)
	def deduction_gl_entries(self,gl_entries):
		for d in self.deductions:
			party_type = party = ''
			if  get_account_type( d.account, self.company) in ["Receivable","Payable"]:
				party_type = "Supplier"
				party = self.supplier
			gl_entries.append(
				self.get_gl_dict({
					"account":  d.account,
					"credit": d.amount,
					"credit_in_account_currency": d.amount,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"party_type": party_type,
					"party": party,
					"cost_center": self.cost_center,
					"voucher_type":self.doctype,
					"voucher_no":self.name
				}, self.currency)
			)

	def get_expense_gl(self):
		items = {}
		total_transportation_amount = 0
		for i in self.get("items"): 
			if str(i.expense_account) in items:
				items[str(i.expense_account)] = flt(items[str(i.expense_account)]) + flt(i.transportation_amount)
			else:
				items.setdefault(str(i.expense_account),flt(i.transportation_amount))
			total_transportation_amount += flt(i.transportation_amount)

		# pro-rate POL expenses against each expense GL
		if flt(total_transportation_amount) and flt(self.pol_amount):
				deduct_pct  = 0
				deduct_amt  = 0
				balance_amt = flt(self.pol_amount)
				counter     = 0
				for k,v in sorted(items.items(), key=operator.itemgetter(1)):
					counter += 1
					if counter == len(items):
						deduct_amt = balance_amt
					else:
						deduct_pct = math.floor((flt(v)/flt(total_transportation_amount))*0.01)
						deduct_amt = math.floor(flt(self.pol_amount)*deduct_pct*0.01)
						balance_amt= balance_amt - deduct_amt

					items[k] -= flt(deduct_amt)
		return items

	@frappe.whitelist()
	def get_payment_details(self):
		self.set('items', [])
		self.set('pols', [])
		# get stock enteris 
		stock_transfer = self.get_stock_entries()
		# get delivery note
		delivery_note = self.get_delivery_notes() 
		# get trip log data
		within_warehouse_trips = self.get_trip_log()

		# get Trips from production location based
		production_location = self.get_production_transportation("Location")

		# get Trips from production warehouse based
		production_warehouse = self.get_production_transportation("Warehouse")
		entries = stock_transfer + delivery_note + production_warehouse
		if not entries and not within_warehouse_trips and not production_location:
			frappe.throw("No Transportation Detail(s) for Equipment <b>{0} </b> ".format(self.equipment))
		self.total_trip = len(entries)
		trans_amount    = unload_amount = pol_amount = 0

		# populate items
		for d in entries:
			if d.transporter_rate_ref:
				d.transportation_rate 	= d.rate
				d.unloading_amount 		= 0
				d.transporter_rate 		= d.transporter_rate_reference
			else:
				tr = get_transporter_rate(d.from_warehouse, d.receiving_warehouse, d.posting_date, self.equipment_type, d.item_code)
				d.transporter_rate_ref = tr.name

				if cint(self.total_trip) > flt(tr.threshold_trip):
					d.transportation_rate = flt(tr.higher_rate)
				else:
					d.transportation_rate = flt(tr.lower_rate)

				d.unloading_rate  = tr.unloading_rate
				if d.unloading_by == "Transporter":
					d.unloading_amount = round(flt(d.unloading_rate) * flt(d.qty), 2)
				else:
					d.unloading_amount = 0
				d.expense_account 	= tr.expense_account
				
			d.transportation_amount = round(flt(d.transportation_rate) * flt(d.qty), 2)
			d.total_amount 		= flt(d.unloading_amount) + flt(d.transportation_amount)
			trans_amount 		+= flt(d.transportation_amount)
			unload_amount 		+= flt(d.unloading_amount)
			row = self.append('items', {})
			row.update(d)

		# populate items from Transporter Trips Log
		for d in within_warehouse_trips:
			d.total_amount 		= flt(d.transportation_amount)
			trans_amount 		+= flt(d.transportation_amount)
			row 				= self.append('items', {})
			row.update(d)
		
		# populate items from Production 
		for d in production_location:
			d.total_amount 	= flt(d.transportation_amount)
			trans_amount 	+= flt(d.transportation_amount)
			row = self.append('items', {})
			row.update(d)

		#POL Details
		for a in frappe.db.sql("""select posting_date, name as pol_receive, pol_type as item_code, 
										item_name, qty, rate, total_amount as amount, 
										total_amount as allocated_amount,
										fuelbook_branch
									from `tabPOL Receive`  p
									where docstatus = 1 
									and posting_date between '{}' and '{}' and equipment = '{}'
									and NOT EXISTS(select 1 from `tabTransporter Invoice` ti inner join `tabTransporter Invoice Pol` tip 
											on ti.name = tip.parent 
											where ti.docstatus != 2 and ti.name != '{}')
									""".format(self.from_date, self.to_date, self.equipment,self.name), as_dict=1):
			row = self.append('pols', {})
			row.update(a)
		self.calculate_total()
	
	@frappe.whitelist()
	def calculate_total(self):
		if not self.credit_account:
			self.credit_account = get_party_account("Supplier",self.supplier,self.company)
		# transfer and delivery charges
		transfer_charges = 0
		delivery_charges = 0
		total_transporter_amount = 0
		unloading_amount = 0
		trip_log_charges = 0
		within_trip_count = 0
		production_transport_charges = 0
		production_trip_count = 0
		for i in self.items:
			if i.reference_type == 'Stock Entry':
				transfer_charges += flt(i.transportation_amount)

			if i.reference_type == 'Delivery Note':
				delivery_charges += flt(i.transportation_amount)

			if i.reference_type == 'Trip Log':
				trip_log_charges += flt(i.transportation_amount)
				within_trip_count += 1

			if i.reference_type == 'Production':
				production_transport_charges += flt(i.transportation_amount)
				production_trip_count += 1
				
			total_transporter_amount += flt(i.transportation_amount)
			unloading_amount += flt(i.unloading_amount)
			
		self.transfer_charges 	= flt(transfer_charges)
		self.delivery_charges  	= flt(delivery_charges)
		self.transportation_amount = flt(total_transporter_amount)
		self.within_warehouse_trip = within_trip_count
		self.production_trip_count = production_trip_count
		self.within_warehouse_amount = flt(trip_log_charges)
		self.unloading_amount 	= flt(unloading_amount)
		self.production_transport_amount = flt(production_transport_charges)
		self.gross_amount 	= flt(self.transportation_amount) + flt(self.unloading_amount)

		# pol
		pol_amount = 0
		for j in self.pols:
			if not flt(j.allocated_amount):
				j.allocated_amount = flt(j.amount)
			pol_amount += flt(j.allocated_amount)

		self.pol_amount  	= flt(pol_amount)

		# unloading
		if self.unloading_amount:
			self.unloading_account = frappe.db.get_value("Company", self.company, "default_unloading_account")
			if not self.unloading_account:
				frappe.throw(_("GL for {} is not set under {}")\
					.format(frappe.bold("Default Unloading Account"), frappe.bold("Company's Production Account Settings")))

		self.tds_amount = self.security_deposit_amount = self.weighbridge_amount = self.clearing_amount = other_deductions = 0
		for d in self.get("deductions"):
			# tds and security deposite
			if d.deduction_type in ["Security Deposit","TDS Deduction"]:
				if flt(d.percent) < 1:
					throw("Deduction Percent is required at row {} for deduction type {}".format(bold(d.idx),bold(d.deduction_type)))
				d.amount = flt(self.gross_amount) * flt(d.percent) / 100
				if d.deduction_type == "TDS Deduction":
					self.tds_amount += flt(d.amount)
					d.account = get_tds_account(d.percent, self.company)
					if not d.account:
						frappe.throw(_("GL for {} is not set under {}")\
						.format(frappe.bold("TDS Account"), frappe.bold("Company's Accounts Settings")))
				elif d.deduction_type == "Security Deposit":
					d.account = frappe.db.get_value("Company", self.company, "security_deposit_account")
					self.security_deposit_amount += flt(d.amount)
					if not d.account:
						frappe.throw(_("GL for {} is not set under {}")\
							.format(frappe.bold("Security Deposit Received"), frappe.bold("Company's Accounts Settings")))
							
			elif d.deduction_type in ["Weighbridge Charge/Trip","Clearing Charge/Trip"]:
				d.account = frappe.db.get_value("Company", self.company, "weighbridge_account")
				d.amount = flt(self.total_trip) * flt(d.charge_amount)
				if d.deduction_type == "Weighbridge Charge/Trip":
					self.weighbridge_amount += flt(d.amount)
					if not d.account:
						frappe.throw(_("GL for {} is not set under {}")\
						.format(frappe.bold("Income from Weighbridge Account"), frappe.bold("Company's Accounts Settings")))
				elif d.deduction_type == "Clearing Charge/Trip":
					self.clearing_amount += flt(d.amount)
					if not d.account:
						frappe.throw(_("GL for {} is not set under {}")\
							.format(frappe.bold("Income from Clearing Account"), frappe.bold("Company's Accounts Settings")))
			else:
				other_deductions += flt(d.amount)
		self.total_trip = len(self.get("items"))
		self.other_deductions 	= flt(other_deductions) + flt(self.tds_amount) + flt(self.security_deposit_amount) + flt(self.weighbridge_amount) + flt(self.clearing_amount)	
		self.net_payable 	= flt(self.gross_amount) - flt(self.pol_amount) - flt(self.other_deductions)
		self.amount_payable = self.outstanding_amount 	= flt(self.net_payable)		
		self.grand_total 		= self.gross_amount

	def get_production_transportation(self, rate_base_on):
		return frappe.db.sql("""
					select
						b.name as reference_row,
						a.posting_date,
						'Production' as reference_type,
						a.name as reference_name,
						b.item_code,
						b.item_name,
						b.rate as transportation_rate,
						b.amount as transportation_amount,
						b.qty,
						b.unloading_by,
						b.equipment,
						a.warehouse as from_warehouse,
						if(a.transfer = 1, a.to_warehouse, a.warehouse) as receiving_warehouse,
						b.equipment,
						b.transporter_rate as transporter_rate_ref,
						b.transportation_expense_account as expense_account 
						from
						`tabProduction` a inner join `tabProduction Product Item` b 
						on a.name = b.parent
					where a.docstatus = 1 
						and a.posting_date between "{0}" and "{1}" 
						and b.equipment = "{2}" 
						and a.branch = '{3}' 
						and b.transporter_payment_eligible = 1 
						and a.transporter_rate_base_on = '{4}' 
						and NOT EXISTS
						(
							select 1 
							from `tabTransporter Invoice` p, `tabTransporter Invoice Item` i
							where p.name = i.parent 
							and i.reference_name = a.name
							and p.docstatus != 2
							and p.name != '{5}'
						)""".format(self.from_date, self.to_date, self.equipment, self.branch, rate_base_on, self.name), as_dict = True)

	def get_delivery_notes(self):
		return frappe.db.sql("""
				SELECT b.name as reference_row, a.posting_date, 
					'Delivery Note' as reference_type, a.name as reference_name, 
					b.item_code, b.item_name, 
					b.warehouse as from_warehouse, a.customer as receiving_warehouse, 
					b.qty as qty, '' as unloading_by, b.equipment,
					b.transporter_rate as rate, b.transporter_rate_ref,
					b.transporter_rate_expense_account as expense_account
				FROM `tabDelivery Note` a INNER JOIN `tabDelivery Note Item` b 
				ON b.parent = a.name
				WHERE a.docstatus = 1 AND a.posting_date BETWEEN "{0}" and "{1}" 
				AND b.equipment = "{2}" AND b.cost_center = "{3}" 
				AND b.others_equipment = 0
				AND NOT EXISTS(
					select 1 
					from `tabTransporter Invoice` p, `tabTransporter Invoice Item` i
					where p.name = i.parent 
					and i.reference_name = a.name
					and p.docstatus != 2
					and p.name != '{4}'
				)
				""".format(self.from_date, self.to_date, self.equipment, self.cost_center,self.name), as_dict = True)

	def get_stock_entries(self):
		return frappe.db.sql("""
			SELECT
				b.name as reference_row, a.posting_date, 
				'Stock Entry' as reference_type, a.name as reference_name, 
				b.item_code, b.item_name,b.s_warehouse as from_warehouse, 
				b.t_warehouse as receiving_warehouse, b.received_qty as qty, b.equipment,
				b.unloading_by
				FROM `tabStock Entry` a INNER JOIN `tabStock Entry Detail` b ON b.parent = a.name 
				WHERE a.docstatus = 1  
				AND a.purpose = 'Material Transfer' 
				AND a.posting_date between "{0}" and "{1}" 
				AND b.equipment = "{2}"
				AND b.cost_center = "{3}"
				AND NOT EXISTS(
					select 1 
					from `tabTransporter Invoice` p, `tabTransporter Invoice Item` i
					where p.name = i.parent 
					and p.docstatus != 2 
					and p.name != '{4}'
					and i.reference_name = a.name
				)
				""".format(self.from_date, self.to_date, self.equipment, self.cost_center,self.name), as_dict = True)

	def get_trip_log(self):
		return frappe.db.sql("""select b.name as reference_row, a.posting_date, 
					'Trip Log' as reference_type, a.name as reference_name, 
					b.item as item_code, b.item_name, b.amount as transportation_amount,
					a.warehouse as from_warehouse, a.warehouse as receiving_warehouse, 
					b.qty as qty, b.equipment, b.transporter_rate as transporter_rate_ref, 
					b.rate as transportation_rate, b.expense_account
				from `tabTrip Log` a, `tabTrip Log Item` b
				where a.name = b.parent 
				and a.docstatus = 1 
				and a.posting_date between "{0}" and "{1}" 
				and b.equipment = "{2}" 
				and a.cost_center = "{3}"
				and b.eligible_for_transporter_payment = 1
				and NOT EXISTS(
					select 1 
					from `tabTransporter Invoice` p, `tabTransporter Invoice Item` i
					where p.name = i.parent 
					and p.docstatus != 2
					and i.reference_row = b.name
					and p.name != '{4}')
				""".format(self.from_date, self.to_date, self.equipment, self.cost_center, self.name), as_dict = True)
# query permission
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return

	return """(
		exists(select 1
			from `tabEmployee` as e
			where e.branch = `tabTransporter Invoice`.branch
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabTransporter Invoice`.branch)
	)""".format(user=user)