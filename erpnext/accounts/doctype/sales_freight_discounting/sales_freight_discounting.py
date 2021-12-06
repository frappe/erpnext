# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import print_function
from frappe import _, msgprint, scrub
from warnings import filters
from dateutil.relativedelta import relativedelta
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_to_date, getdate

class SalesFreightDiscounting(Document):
	def on_submit(self):
		self.make_journal_entry()


	@frappe.whitelist()
	def get_invoices(self):

		conditions = ""
		if self.company:
			conditions += "AND DN.company = %s" % frappe.db.escape(self.company)

		if self.operating_unit:
			conditions += "AND DN.cost_center = %s" % frappe.db.escape(self.operating_unit)

		if self.start_date:
			conditions += "AND DN.posting_date >= '%s'" % self.start_date

		if self.end_date:
			conditions += "AND DN.posting_date <= '%s'" % self.end_date

		get_invoice = frappe.db.sql(
			"""
			SELECT DISTINCT DN.company, DN.lr_date, DN.transporter, DN.rounded_total,DN.posting_date, DN.lr_no, DN.total_qty, DN.sales_freight_checkbox, DN.transporter,DN.grand_total, SOI.parent,
			DN.name, DN.total_net_weight, DN.customer,DN.customer_name, DN.cost_center FROM `tabDelivery Note` as DN
			inner join `tabSales Invoice Item` as SOI on DN.name = SOI.delivery_note
			inner join `tabSales Invoice` as SO on SOI.parent = SO.name
			where DN.docstatus = 1 and SO.docstatus = 1 and DN.sales_freight_checkbox = 0
			{conditions}""".format(conditions=conditions), as_dict=1)

		if get_invoice:

			for i in get_invoice:
			
				add = self.append('delivery_details')
				add.customer = i.customer 
				add.sales_invoice = i.parent
				add.customer_name = i.customer_name
				add.delivery_note = i.name
				add.weight_for_shipping = i.total_net_weight
				add.weight = i.total_qty
				add.number_of_packages = i.total_qty
				add.carrier = i.transporter
				add.vehical_no = i.vehical_no
				add.transporter = i.lr_no
				add.transport_receipt_date = i.lr_date
			
			return True

		else:
			frappe.msgprint("Delivery Notes Not Found") 

	@frappe.whitelist()
	def add_amount_for_total_freight(self):
		value = 0	
		for amt in self.delivery_details:
			value += amt.amount
		self.total_freight = value
		return True

	def make_journal_entry(self):
		doc = frappe.new_doc('Journal Entry')
		doc.voucher_type = 'Journal Entry'
		doc.company = self.company
		doc.cheque_no = self.name
		doc.posting_date = self.posting_date
		doc.cost_center = self.operating_unit
		doc.append('accounts',{
			"account": self.freight_account, 
			"debit_in_account_currency": self.total_freight,
			"cost_center": self.operating_unit
		})
		
		if not self.company:
			frappe.throw(_("Please select a Company"))
		for i in self.delivery_details:
			if not i.customer:
				return

			account = frappe.db.get_value("Party Account",
				{"parenttype": "Customer", "parent": i.customer, "company": self.company}, "account")

			if not account:
				group = frappe.get_cached_value("Customer", i.customer, scrub("Customer Group"))
				account = frappe.db.get_value("Party Account",
					{"parenttype": "Customer Group", "parent": group, "company": self.company}, "account")

			if not account:
				default_account_name = "default_receivable_account"
					
				account = frappe.get_cached_value('Company',  self.company,  default_account_name)				
			doc.append('accounts',{
				"account": account,
				"party_type": "Customer",
				"party": i.customer,
				"credit_in_account_currency": i.amount
			})		
		doc.cheque_date = self.posting_date
		doc.save()
		doc.submit()
		frappe.db.set_value('Sales Freight Discounting', self.name, 'journal_entry_name', doc.name)
		frappe.db.commit()
		self.reload()
	
		# Setting True value for delivery note.
		if self.journal_entry_name:
			var = frappe.get_all('Delivery Details', filters={'parent': self.name}, fields=['delivery_note'])
			
			for val in var:
				frappe.db.set_value('Delivery Note', val.delivery_note, 'sales_freight_checkbox', 1)

		frappe.msgprint("Journal Entry Created Please Check")
		return True

	def on_cancel(self):
		doc = frappe.get_doc('Journal Entry', self.journal_entry_name)	
		doc.cancel()
		frappe.msgprint("Sales Freight Discounting And Journal Entry Cancelled")
		
		for val in self.delivery_details:
			frappe.db.set_value('Delivery Note', val.delivery_note, 'sales_freight_checkbox', 0)		
			doc = frappe.get_doc("Delivery Note", val.delivery_note)
			doc.reload()
		self.db_set('journal_entry_name', "")
				