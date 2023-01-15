# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, nowdate
from frappe import _, bold

class TransporterInvoiceEntry(Document):
	def validate(self):
		self.valid_account_for_other_charges()
	def valid_account_for_other_charges(self):
		if len(self.items) == 0:
			frappe.msgprint(_("No equipments pulled"), raise_exception = True)
		for a in self.items:
			if flt(a.amount) > 0 and not a.account:
				frappe.msgprint(_("Select account for other charge at row {}".format(bold(a.idx))), raise_exception = True)

	@frappe.whitelist()
	def create_transporter_invoice(self):
		self.check_permission('write')
		# self.created = 1
		args = frappe._dict({
			"transporter_invoice_entry":self.name,
			"doctype":"Transporter Invoice",
			"branch":self.branch,
			"cost_center":self.cost_center,
			"from_date":self.from_date,
			"to_date":self.to_date,
			"posting_date":self.posting_date,
			"company":self.company
		})
		# frappe.enqueue(crate_invoice_entries, timeout=600, args=args)
		if cint(self.invoice_created) == 0 :
			crate_invoice_entries(args=args)
	
	@frappe.whitelist()
	def submit_transporter_invoice(self):
		self.check_permission('write')
		if cint(self.invoice_submitted) == 0 and cint(self.invoice_created) == 1 :
			args = frappe._dict({
				"transporter_invoice_entry":self.name
				})
			submit_invoice_entries(args=args)

	@frappe.whitelist()
	def get_equipment(self):
		self.set("items",[])
		for d in frappe.db.sql('''
			select name, equipment_category, equipment_type, supplier 
				from `tabEquipment` 
				where hired_equipment = 1 and branch = '{}' and equipment_category = '{}' and enabled = 1
			'''.format(self.branch, self.equipment_category), as_dict= True):
			self.append("items",{
				"equipment": d.name,
				"equipment_category": d.equipment_category,
				"equipment_type": d.equipment_type,
				"supplier":d.supplier
			})
	@frappe.whitelist()
	def cancel_transporter_invoice(self):
		self.check_permission('write')
		if cint(self.invoice_submitted) == 1 and cint(self.invoice_created) == 1 :
			args = frappe._dict({
				"transporter_invoice_entry":self.name
				})
			cancel_invoice_entries(args=args)

	@frappe.whitelist()
	def post_to_account(self):
		self.check_permission('write')
		if cint(self.invoice_submitted) == 1 and cint(self.invoice_created) == 1 and cint(self.posted_to_account) == 0:
			args = frappe._dict({
				"transporter_invoice_entry":self.name
				})
			post_accounting_entries(args=args)

@frappe.whitelist()
def crate_invoice_entries(args, publish_progress=True):
	count=0
	successful = 0
	failed = 0
	invoice_entry = frappe.get_doc("Transporter Invoice Entry", args.get("transporter_invoice_entry"))
	invoice_entry.set("failed_transaction",[])
	refresh_interval = 25
	total_count = len(invoice_entry.items)
	for e in invoice_entry.items:
		args.update({
			"equipment":e.equipment,
			"equipment_category":e.equipment_category,
			"equipment_type":e.equipment_type,
			"supplier":e.supplier
		})
		error = None
		try:
			transporter_invoice = frappe.get_doc(args)
			transporter_invoice.get_payment_details()
			# assign deductions
			transporter_invoice.set("deductions",[])
			if flt(e.tds):
				transporter_invoice.append("deductions",{
					"deduction_type":"TDS Deduction",
					"percent":e.tds
				})
			if flt(e.security_percent):
				transporter_invoice.append("deductions",{
					"deduction_type":"Security Deposit",
					"percent":e.security_percent
				})
			if flt(e.weighbridge_charge_amount) > 0:
				transporter_invoice.append("deductions",{
					"deduction_type":"Weighbridge Charge/Trip",
					"charge_amount":e.weighbridge_charge_amount
				})
			if flt(e.clearing_charge_amount) > 0:
				transporter_invoice.append("deductions",{
					"deduction_type":"Clearing Charge/Trip",
					"charge_amount":e.clearing_charge_amount
				})
			if flt(e.amount) > 0:
				transporter_invoice.append("deductions",{
					"deduction_type":"Other Deductions",
					"amount":e.amount,
					"account":e.account
				})
			transporter_invoice.insert()
			successful += 1
		except Exception as e:
			error = str(e)
			failed += 1
		count+=1
		invoice_entry_item = frappe.get_doc("Transporter Invoice Entry Item",{"parent":args.get("transporter_invoice_entry"), "equipment":transporter_invoice.equipment})
		invoice_entry_item.db_set("reference",transporter_invoice.name)
		if error:
			invoice_entry_item.db_set("creation_status", "Failed")
			invoice_entry_item.db_set("error_msg", error)
		else:
			invoice_entry_item.db_set("creation_status", "Success")
			invoice_entry_item.db_set("tds_amount", transporter_invoice.tds_amount)
			invoice_entry_item.db_set("clearing_charge_amount",transporter_invoice.clearing_amount)
			invoice_entry_item.db_set("weighbridge_charge_amount",transporter_invoice.weighbridge_amount)
			invoice_entry_item.db_set("security_deposit_amount",transporter_invoice.security_deposit_amount)
			invoice_entry_item.db_set("total_trip",transporter_invoice.total_trip)
			invoice_entry_item.db_set("total_payable_amount", transporter_invoice.amount_payable)
			invoice_entry_item.db_set("pol_amount", transporter_invoice.pol_amount)
			
		if publish_progress:
				show_progress = 0
				if count <= refresh_interval:
					show_progress = 1
				elif refresh_interval > total_count:
					show_progress = 1
				elif count%refresh_interval == 0:
					show_progress = 1
				elif count > total_count-refresh_interval:
					show_progress = 1
				
				if show_progress:
					description = " Processing {}: ".format(transporter_invoice.name if transporter_invoice else e.equipment) + "["+str(count)+"/"+str(total_count)+"]"
					frappe.publish_progress(count*100/total_count,
						title = _("Creating Transporter Invoice..."),
						description = description)
					pass

	if failed > 0 and failed < successful :
		invoice_entry.db_set("invoice_created",1)
	elif failed == 0 and successful > 0:
		invoice_entry.db_set("invoice_created",1)
	elif successful == 0 and failed > 0:
		invoice_entry.db_set("invoice_created",0)

	invoice_entry.db_set("successful",successful)
	invoice_entry.db_set("failed",failed)
	invoice_entry.reload()

@frappe.whitelist()
def submit_invoice_entries(args,publish_progress=True):
	count=0
	successful = 0
	failed = 0
	invoice_entry = frappe.get_doc("Transporter Invoice Entry", args.get("transporter_invoice_entry"))
	invoice_entry.set("failed_transaction",[])
	refresh_interval = 25
	total_count = cint(invoice_entry.successful)
	for e in invoice_entry.items:
		if e.reference:
			error = None
			try:
				transporter_invoice = frappe.get_doc("Transporter Invoice",e.reference)
				transporter_invoice.submit()
				successful += 1
			except Exception as e:
				error = str(e)
				failed += 1
			count+=1
			invoice_entry_item = frappe.get_doc("Transporter Invoice Entry Item",{"parent":args.get("transporter_invoice_entry"), "equipment":transporter_invoice.equipment})
			if error:
				invoice_entry_item.db_set("error_msg", error)
				invoice_entry_item.db_set("submission_status", "Failed")
			else:
				invoice_entry_item.db_set("submission_status", "Submitted")
				
			if publish_progress:
					show_progress = 0
					if count <= refresh_interval:
						show_progress = 1
					elif refresh_interval > total_count:
						show_progress = 1
					elif count%refresh_interval == 0:
						show_progress = 1
					elif count > total_count-refresh_interval:
						show_progress = 1
					
					if show_progress:
						description = " Processing {}: ".format(transporter_invoice.name if transporter_invoice else e.equipment) + "["+str(count)+"/"+str(total_count)+"]"
						frappe.publish_progress(count*100/total_count,
							title = _("Submitting Transporter Invoice..."),
							description = description)
						pass

	if failed > 0 and failed < successful :
		invoice_entry.db_set("invoice_submitted",1)
	elif failed == 0 and successful > 0:
		invoice_entry.db_set("invoice_submitted",1)
	elif successful == 0 and failed > 0:
		invoice_entry.db_set("invoice_submitted",0)
	
	invoice_entry.db_set("submission_successful",successful)
	invoice_entry.db_set("submission_failed",failed)
	invoice_entry.reload()

@frappe.whitelist()
def cancel_invoice_entries(args,publish_progress=True):
	count=0
	successful = 0
	failed = 0
	invoice_entry = frappe.get_doc("Transporter Invoice Entry", args.get("transporter_invoice_entry"))
	invoice_entry.set("failed_transaction",[])
	refresh_interval = 25
	total_count = cint(invoice_entry.submission_successful)
	for e in invoice_entry.items:
		if e.reference:
			error = None
			try:
				transporter_invoice = frappe.get_doc("Transporter Invoice",e.reference)
				transporter_invoice.cancel()
				successful += 1
			except Exception as e:
				error = str(e)
				failed += 1
			count+=1
			invoice_entry_item = frappe.get_doc("Transporter Invoice Entry Item",{"parent":args.get("transporter_invoice_entry"), "equipment":transporter_invoice.equipment})
			if error:
				invoice_entry_item.db_set("submission_status", "Failed")
				invoice_entry_item.db_set("error_msg", error)
			else:
				invoice_entry_item.db_set("submission_status", "Cancelled")
				
			if publish_progress:
					show_progress = 0
					if count <= refresh_interval:
						show_progress = 1
					elif refresh_interval > total_count:
						show_progress = 1
					elif count%refresh_interval == 0:
						show_progress = 1
					elif count > total_count-refresh_interval:
						show_progress = 1
					
					if show_progress:
						description = " Processing {}: ".format(transporter_invoice.name if transporter_invoice else e.equipment) + "["+str(count)+"/"+str(total_count)+"]"
						frappe.publish_progress(count*100/total_count,
							title = _("Cancelling Transporter Invoice..."),
							description = description)
						pass
	
	invoice_entry.db_set("submission_successful",invoice_entry.submission_successful - successful )
	invoice_entry.db_set("submission_failed",failed)
	invoice_entry.db_set("invoice_submitted",0)
	invoice_entry.reload()

@frappe.whitelist()
def post_accounting_entries(args,publish_progress=True):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
	count=0
	successful = 0
	failed = 0
	invoice_entry = frappe.get_doc("Transporter Invoice Entry", args.get("transporter_invoice_entry"))
	refresh_interval = 25
	total_count = cint(invoice_entry.successful)
	for e in invoice_entry.items:
		if e.reference:
			equipment = e.equipment
			error = None
			transporter_invoice = frappe.get_doc("Transporter Invoice",e.reference)
			
			try:
				pe = get_payment_entry(dt= "Transporter Invoice", dn= e.reference)
				pe.insert(ignore_mandatory=True)
				successful += 1
			except Exception as e:
				error = str(e)
				failed += 1
			count+=1
			invoice_entry_item = frappe.get_doc("Transporter Invoice Entry Item",{"parent":args.get("transporter_invoice_entry"), "equipment": equipment})
			if error:
				invoice_entry_item.db_set("error_msg", error)
			# else:
			# 	invoice_entry_item.db_set("submission_status", "Submitted")
				
			if publish_progress:
					show_progress = 0
					if count <= refresh_interval:
						show_progress = 1
					elif refresh_interval > total_count:
						show_progress = 1
					elif count%refresh_interval == 0:
						show_progress = 1
					elif count > total_count-refresh_interval:
						show_progress = 1
					
					if show_progress:
						description = " Processing {}: ".format(transporter_invoice.name if transporter_invoice else e.equipment) + "["+str(count)+"/"+str(total_count)+"]"
						frappe.publish_progress(count*100/total_count,
							title = _("Posting Accounting Entry..."),
							description = description)
		# 				pass
	invoice_entry.db_set("posted_to_account", 1 if successful > 0 else 0)
	invoice_entry.reload()