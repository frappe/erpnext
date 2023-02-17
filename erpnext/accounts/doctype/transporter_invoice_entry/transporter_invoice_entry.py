# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, nowdate, money_in_words
from frappe import _, bold
from erpnext.accounts.party import get_party_account
class TransporterInvoiceEntry(Document):
	def validate(self):
		self.allocate_deductions()
		self.valid_account_for_other_charges()

	def on_update_after_submit(self):
		self.allocate_deductions()
	def before_cancel(self):
		if frappe.db.exists("Transporter Invoice",{"transporter_invoice_entry":self.name,"doctstaus":("!=",2)}):
			frappe.throw("Cannot cancel this document as it is linked with Transporter Invoice")
	def valid_account_for_other_charges(self):
		if len(self.items) == 0:
			frappe.msgprint(_("No equipments pulled"), raise_exception = True)
		for a in self.items:
			if flt(a.amount) > 0 and not a.account:
				frappe.msgprint(_("Select account for other charge at row {}".format(bold(a.idx))), raise_exception = True)
	def allocate_deductions(self):
		for i in self.items:
			if flt(self.tds):
				i.tds = self.tds
			if flt(self.security_percent) :
				i.security_percent = self.security_percent
				i.security_deposit_amount = 0
			elif flt(self.security_deposit_amount) > 0:
				i.security_deposit_amount = self.security_deposit_amount
			if flt(self.clearing_charge_amount) > 0:
				i.clearing_charge_amount = self.clearing_charge_amount
			if flt(self.weighbridge_charge_amount) > 0:
				i.weighbridge_charge_amount = self.weighbridge_charge_amount
			if flt(self.amount) > 0 :
				if not self.account :
					frappe.throw(_("You need to select account for other deductions"))
				i.amount = self.amount
				i.account = self.account

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
			"company":self.company,
			"status":"Draft",
		})
		if cint(self.invoice_created) == 0 :
			frappe.enqueue(crate_invoice_entries,invoice_entry= self, timeout=600, args=args)
			# crate_invoice_entries(args=args)
	
	@frappe.whitelist()
	def submit_transporter_invoice(self):
		self.check_permission('write')
		if cint(self.invoice_submitted) == 0 and cint(self.invoice_created) == 1 :
			args = frappe._dict({
				"transporter_invoice_entry":self.name
				})
			frappe.enqueue(submit_invoice_entries, timeout=600, args = args)
			# submit_invoice_entries(args=args)

	@frappe.whitelist()
	def get_equipment(self):
		self.set("items",[])
		for d in frappe.db.sql('''
			select name, equipment_category, equipment_type, supplier, company
				from `tabEquipment` e
				where hired_equipment = 1 and branch = '{}' and equipment_category = '{}' and enabled = 1
				and exists(select 1 from `tabSupplier` where name = e.supplier and supplier_type ='{}')
			'''.format(self.branch, self.equipment_category, self.supplier_type), as_dict= True):
			credit_account = get_party_account("Supplier",d.supplier, d.company)
			self.append("items",{
				"equipment": d.name,
				"equipment_category": d.equipment_category,
				"equipment_type": d.equipment_type,
				"supplier":d.supplier,
				"credit_account":credit_account
			})
	@frappe.whitelist()
	def cancel_transporter_invoice(self):
		self.check_permission('write')
		if cint(self.invoice_submitted) == 1 and cint(self.invoice_created) == 1 :
			args = frappe._dict({
				"transporter_invoice_entry":self.name
				})
			frappe.enqueue(cancel_invoice_entries, timeout=600, args = args)
			
			# cancel_invoice_entries(args=args)

	@frappe.whitelist()
	def post_to_account(self):
		je_id = frappe.db.sql("select journal_entry from `tabTransporter Invoice` where transporter_invoice_entry = '{}' and docstatus = 1 limit 1".format(self.name), as_dict=True)
		if je_id[0].journal_entry:
			je = frappe.get_doc("Journal Entry", je_id[0].journal_entry)
			if je.docstatus != 2:
				frappe.throw("{} already exists against this entry".format(frappe.get_desk_link("Journal Entry",je.name)))
		self.check_permission('write')
		if cint(self.invoice_submitted) == 1 and cint(self.invoice_created) == 1 :
			args = frappe._dict({
					"transporter_invoice_entry":self.name,
					"doctype":"Transporter Invoice",
					"branch":self.branch,
					"cost_center":self.cost_center,
					"from_date":self.from_date,
					"to_date":self.to_date,
					"posting_date":self.posting_date,
					"company":self.company,
					"payable_amount":self.payable_amount,
					"remarks":self.remarks
				})
			post_accounting_entries(args=args)

@frappe.whitelist()
def crate_invoice_entries( invoice_entry, args, publish_progress=True):
	count = 0
	successful = 0
	failed = 0
	invoice_entry.set("failed_transaction",[])
	refresh_interval = 25
	total_payable_amount = other_deductions = 0
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
			elif flt(e.security_deposit_amount) > 0:
				transporter_invoice.append("deductions",{
					"deduction_type":"Security Deposit",
					"charge_amount":e.security_deposit_amount
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
		invoice_entry_item = frappe.get_doc("Transporter Invoice Entry Item",{"parent":invoice_entry.name, "equipment":transporter_invoice.equipment})
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
			total_payable_amount += flt(transporter_invoice.amount_payable)
			other_deductions += flt(transporter_invoice.other_deductions)
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

	invoice_entry.db_set("payable_amount",total_payable_amount)
	invoice_entry.db_set("total_deduction",other_deductions)
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
	for e in frappe.db.sql("select name as reference, equipment from `tabTransporter Invoice` where docstatus = 0 and transporter_invoice_entry = '{}'".format(args.get("transporter_invoice_entry")),as_dict=True):
		if e.reference:
			error = None
			try:
				transporter_invoice = frappe.get_doc("Transporter Invoice",e.reference)
				if transporter_invoice.docstatus != 2:
					transporter_invoice.submit()
				successful += 1
			except Exception as er:
				error = str(er)
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
	for e in frappe.db.sql("select name as reference from `tabTransporter Invoice` where docstatus = 1 and status = 'Unpaid' and transporter_invoice_entry = '{}'".format(args.get("transporter_invoice_entry")),as_dict=True):
		if e.reference:
			error = None
			try:
				transporter_invoice = frappe.get_doc("Transporter Invoice",e.reference)
				if transporter_invoice.docstatus == 1:
					transporter_invoice.cancel()
				successful += 1
			except Exception as er:
				error = str(er)
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
	count=0
	successful = 0
	failed = 0
	payable_amount = 0
	invoice_entry = frappe.get_doc("Transporter Invoice Entry", args.get("transporter_invoice_entry"))
	refresh_interval = 25
	total_count = cint(invoice_entry.successful)
	if not args.get("payable_amount"):
		frappe.throw(_("Payable Amount should be greater than zero"))
	r = []
	if args.get("remarks"):
		r.append(_("Note: {0}").format(args.get("remarks")))

	remarks = ("").join(r) #User Remarks is not mandatory
	bank_account = frappe.db.get_value("Company",args.get("company"), "default_bank_account")
	if not bank_account:
		frappe.throw(_("Default bank account is not set in company {}".format(frappe.bold(self.company))))
	# Posting Journal Entry
	je = frappe.new_doc("Journal Entry")
	je.flags.ignore_permissions=1
	je.update({
		"doctype": "Journal Entry",
		"voucher_type": "Bank Entry",
		"naming_series": "Bank Payment Voucher",
		"title": "Transporter Payment "+ str(args.get("branch")),
		"user_remark": "Note: " + "Transporter Payment - " + str(remarks),
		"posting_date": args.get("posting_date"),
		"company": args.get("company"),
		"total_amount_in_words": money_in_words(args.get("payable_amount")),
		"branch": args.get("branch"),
	})
	for e in frappe.db.sql("select name as reference, equipment from `tabTransporter Invoice` where docstatus = 1 and status = 'Unpaid' and transporter_invoice_entry = '{}'".format(args.get("transporter_invoice_entry")),as_dict=True):
		if e.reference:
			equipment = e.equipment
			error = None
			transporter_invoice = frappe.get_doc("Transporter Invoice",e.reference)
			credit_account = transporter_invoice.credit_account
			if not credit_account:
				credit_account = get_party_account("Supplier", transporter_invoice.supplier, transporter_invoice.company)
			try:				
				je.append("accounts",{
					"account": credit_account,
					"debit_in_account_currency": flt(transporter_invoice.amount_payable,2),
					"cost_center": transporter_invoice.cost_center,
					"party_check": 1,
					"party_type": "Supplier",
					"party": transporter_invoice.supplier,
					"reference_type": "Transporter Invoice",
					"reference_name": transporter_invoice.name
				})
				payable_amount += flt(transporter_invoice.amount_payable,2)
				successful += 1
			except Exception as er:
				error = str(er)
				failed += 1
			count+=1
			invoice_entry_item = frappe.get_doc("Transporter Invoice Entry Item",{"parent":args.get("transporter_invoice_entry"), "equipment": equipment})
			if error:
				invoice_entry_item.db_set("error_msg", error)	
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
	je.append("accounts",{
					"account": bank_account,
					"credit_in_account_currency": flt(payable_amount,2),
					"cost_center": args.get("cost_center")
				})
	je.update({
		"total_amount_in_words": money_in_words(payable_amount),
	})
	je.insert()

	for e in invoice_entry.items:
		if e.reference:
			transporter_invoice = frappe.get_doc("Transporter Invoice",e.reference)
			#Set a reference to the claim journal entry
			transporter_invoice.db_set("journal_entry",je.name)
			
	invoice_entry.db_set("posted_to_account", 1 if successful > 0 else 0)
	frappe.msgprint(_('Journal Entry {0} posted to accounts').format(frappe.get_desk_link("Journal Entry",je.name)))
	invoice_entry.reload()
