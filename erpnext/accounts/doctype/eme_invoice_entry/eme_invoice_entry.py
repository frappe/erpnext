# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, cint, flt, money_in_words
from frappe import _
from erpnext.accounts.party import get_party_account

class EMEInvoiceEntry(Document):
	def validate(self):
		self.check_date()

	def check_date(self):
		if self.from_date > self.to_date:
			frappe.throw("From date cannot be grater than To Date")
	def on_submit(self):
		pass
	@frappe.whitelist()
	def create_eme_invoice(self):
		if frappe.db.exists("EME Invoice",{"eme_invoice_entry":self.name}):
			frappe.throw("EME Invoice already created")
		self.check_permission('write')
		owner_list = self.get_owner_list()
		if owner_list:
			args = frappe._dict({
				"eme_invoice_entry":self.name,
				"branch":self.branch,
				"cost_center":self.cost_center,
				"posting_date":nowdate(),
				"from_date":self.from_date,
				"to_date":self.to_date,
				"tds_percent":self.tds_percent,
				"tds_account":self.tds_account,
				"company":self.company,
				"currency":self.currency
			})
			frappe.enqueue(create_eme_invoice_for_owner, owner_list = owner_list, args = args)
		
	def get_owner_list(self):
		owner = []
		for item in self.items:
			if item.supplier not in owner:
				owner.append(item.supplier)
		return owner

	@frappe.whitelist()
	def get_supplier_with_equipment(self):
		if not self.from_date or not self.to_date:
			frappe.throw("From date or to date is missing")
		if self.from_date > self.to_date:
			frappe.throw("From Date cannot be ealier than to Date")
		else:
			data = frappe.db.sql("""
					select supplier, equipment, name as equipment_hiring_form, start_date, end_date
					from 
						`tabEquipment Hiring Form`
					where 
					'{0}' between start_date and end_date
					and '{1}' between start_date and end_date
					and docstatus = 1
					and cost_center = '{2}'
			""".format(self.from_date, self.to_date, self.cost_center), as_dict=True)
			if data:
				self.set("items",[])
				for x in data:
					row = self.append("items",{})
					row.update(x)

	@frappe.whitelist()
	def apply_eme_invice(self):
		frappe.enqueue(apply_eme_invice_entries, doc = self, timeout=600)

	@frappe.whitelist()
	def post_to_account(self):
		flg = 0
		for e in self.successful_transaction:
			eme_invoice = frappe.get_doc("EME Invoice",e.eme_invoice)
			if eme_invoice.docstatus != 1:
				frappe.throw(_("EME Invoice is not submitted {}".format(frappe.get_desk_link("EME Invoice", eme_invoice.name))))
		frappe.enqueue(post_accounting_entries, doc = self, timeout=600)

@frappe.whitelist()
def post_accounting_entries(doc,  publish_progress = True):
	count=0
	successful = 0
	failed = 0
	refresh_interval = 25
	total_count = cint(doc.successful)
	if not doc.payable_amount:
		frappe.throw(_("Payable Amount should be greater than zero"))
	r = []
	if doc.remarks:
		r.append(_("Note: {0}").format(doc.remarks))

	remarks = ("").join(r) #User Remarks is not mandatory
	bank_account = frappe.db.get_value("Company", doc.company, "default_bank_account")
	if not bank_account:
		frappe.throw(_("Default bank account is not set in company {}".format(frappe.bold(doc.company))))
	# Posting Journal Entry
	je = frappe.new_doc("Journal Entry")
	je.flags.ignore_permissions=1
	je.update({
		"doctype": "Journal Entry",
		"voucher_type": "Bank Entry",
		"naming_series": "Bank Payment Voucher",
		"title": "EME Payment "+ str(doc.branch),
		"user_remark": "Note: " + "EME Payment - " + str(doc.remarks),
		"posting_date": doc.posting_date,
		"company":doc.company,
		"total_amount_in_words": money_in_words(doc.payable_amount),
		"branch": doc.branch,
	})
	for e in doc.successful_transaction:
		if e.eme_invoice:
			error = None
			eme_invoice = frappe.get_doc("EME Invoice",e.eme_invoice)
			credit_account = eme_invoice.credit_account
			if not credit_account:
				credit_account = get_party_account("Supplier", eme_invoice.supplier, eme_invoice.company)
			try:				
				je.append("accounts",{
					"account": credit_account,
					"debit_in_account_currency": eme_invoice.payable_amount,
					"cost_center": doc.cost_center,
					"party_check": 1,
					"party_type": "Supplier",
					"party": eme_invoice.supplier,
					"reference_type": "EME Invoice",
					"reference_name": eme_invoice.name
				})
				
				#Set a reference to the claim journal entry
				eme_invoice.db_set("journal_entry",je.name)
				successful += 1
			except Exception as e:
				error = str(e)
				failed += 1
			if error:
				doc.append("failed_transaction",{
						"owner":owner,
						"error_message":error
					})
			count+=1
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
						description = " Processing {}: ".format(eme_invoice.name if eme_invoice else e.eme_invoice) + "["+str(count)+"/"+str(total_count)+"]"
						frappe.publish_progress(count*100/total_count,
							title = _("Posting Accounting Entry..."),
							description = description)
	je.append("accounts",{
				"account": bank_account,
				"credit_in_account_currency": doc.payable_amount,
				"cost_center": doc.cost_center
				})
	je.insert()
	doc.db_set("posted_to_account",1 if successful else 0)
	doc.save()
	frappe.msgprint(_('Journal Entry {0} posted to accounts').format(frappe.get_desk_link("Journal Entry",je.name)))
	doc.reload()

@frappe.whitelist()
def apply_eme_invice_entries(doc, publish_progress = True):
	count=0
	successful = 0
	failed = 0
	refresh_interval = 25
	total_count = cint(doc.successful)
	for d in doc.successful_transaction:
		error = None
		ref_doc = frappe.get_doc("EME Invoice", d.eme_invoice)
		try:
			if ref_doc.workflow_state == "Draft":
				ref_doc.workflow_state = "Waiting Supervisor Approval"
				ref_doc.save()
			successful += 1
		except Exception as e:
			error = str(e)
			failed += 1
		count+=1
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
					description = " Processing {}: ".format(ref_doc.name if ref_doc else d.eme_invoice) + "["+str(count)+"/"+str(total_count)+"]"
					frappe.publish_progress(count*100/total_count,
						title = _("Applying EME Invoice..."),
						description = description)
					pass
	doc.reload()
def create_eme_invoice_for_owner(owner_list, args, publish_progress = True):
	payable_amount = total_deduction = 0
	count=0
	successful = 0
	failed = 0
	refresh_interval = 25
	total_count = len(set(owner_list))
	existing_eme_invoice = get_existing_eme_invoice(owner_list, args)
	doc = frappe.get_doc("EME Invoice Entry", args.get("eme_invoice_entry"))
	doc.set("failed_transaction",[])
	doc.set("successful_transaction",[])
	for owner in owner_list:
		credit_account = get_party_account("Supplier", owner, args.get("company"))
		if owner not in existing_eme_invoice:
			error = None
			args.update({
				"doctype": "EME Invoice",
				"supplier": owner,
				"credit_account":credit_account
			})
			try:
				emi = frappe.get_doc(args)
				emi.get_logbooks()
				emi.set("deduct_items",[])
				for d in doc.deductions:
					if d.supplier == owner:
						emi.append("deduct_items",{
							"account":d.account,
							"amount":d.amount,
							"remarks":d.remarks
						})
				emi.insert()
				successful += 1
			except Exception as e:
				error = str(e)
				failed += 1
			if error:
				doc.append("failed_transaction",{
					"owner":owner,
					"error_message":error
				})
			else:
				doc.append("successful_transaction",{
					"supplier": emi.supplier,
					"eme_invoice": emi.name,
					"credit_account": emi.credit_account,
					"total_payable": emi.payable_amount,
					"total_deduction": emi.total_deduction,
				})
				payable_amount += flt(emi.payable_amount)
				total_deduction += flt(emi.total_deduction)
		count+=1
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
					description = " Processing {}: ".format(emi.name if emi else owner) + "["+str(count)+"/"+str(total_count)+"]"
					frappe.publish_progress(count*100/total_count,
						title = _("Creating EME Invoice..."),
						description = description)
					pass
	doc.db_set("successful", successful)
	doc.db_set("failed", failed)
	doc.db_set("payable_amount", payable_amount)
	doc.db_set("total_deduction", total_deduction)
	doc.db_set("invoice_created", 1 if successful > 0 else 0)

	doc.save()
	doc.reload()

def get_existing_eme_invoice(owner_list, args):
	return frappe.db.sql_list("""
		select distinct supplier from `tabEME Invoice`
		where docstatus!= 2 and company = %s
			and from_date >= %s and to_date <= %s
			and supplier in (%s)
	""" % ('%s', '%s', '%s', ', '.join(['%s']*len(owner_list))),
		[args.company, args.from_date, args.to_date] + owner_list)

