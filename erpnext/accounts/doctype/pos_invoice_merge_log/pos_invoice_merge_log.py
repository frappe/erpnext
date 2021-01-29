# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model import default_fields
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate
from frappe.utils.background_jobs import enqueue
from frappe.model.mapper import map_doc, map_child_doc
from frappe.utils.scheduler import is_scheduler_inactive
from frappe.core.page.background_jobs.background_jobs import get_info

from six import iteritems

class POSInvoiceMergeLog(Document):
	def validate(self):
		self.validate_customer()
		self.validate_pos_invoice_status()

	def validate_customer(self):
		for d in self.pos_invoices:
			if d.customer != self.customer:
				frappe.throw(_("Row #{}: POS Invoice {} is not against customer {}").format(d.idx, d.pos_invoice, self.customer))

	def validate_pos_invoice_status(self):
		for d in self.pos_invoices:
			status, docstatus, is_return, return_against = frappe.db.get_value(
				'POS Invoice', d.pos_invoice, ['status', 'docstatus', 'is_return', 'return_against'])
			
			bold_pos_invoice = frappe.bold(d.pos_invoice)
			bold_status = frappe.bold(status)
			if docstatus != 1:
				frappe.throw(_("Row #{}: POS Invoice {} is not submitted yet").format(d.idx, bold_pos_invoice))
			if status == "Consolidated":
				frappe.throw(_("Row #{}: POS Invoice {} has been {}").format(d.idx, bold_pos_invoice, bold_status))
			if is_return and return_against and return_against not in [d.pos_invoice for d in self.pos_invoices]:
				bold_return_against = frappe.bold(return_against)
				return_against_status = frappe.db.get_value('POS Invoice', return_against, "status")
				if return_against_status != "Consolidated":
					# if return entry is not getting merged in the current pos closing and if it is not consolidated
					bold_unconsolidated = frappe.bold("not Consolidated")
					msg = (_("Row #{}: Original Invoice {} of return invoice {} is {}. ")
								.format(d.idx, bold_return_against, bold_pos_invoice, bold_unconsolidated))
					msg += _("Original invoice should be consolidated before or along with the return invoice.")
					msg += "<br><br>"
					msg += _("You can add original invoice {} manually to proceed.").format(bold_return_against)
					frappe.throw(msg)

	def on_submit(self):
		pos_invoice_docs = [frappe.get_doc("POS Invoice", d.pos_invoice) for d in self.pos_invoices]

		returns = [d for d in pos_invoice_docs if d.get('is_return') == 1]
		sales = [d for d in pos_invoice_docs if d.get('is_return') == 0]

		sales_invoice, credit_note = "", ""
		if sales:
			sales_invoice = self.process_merging_into_sales_invoice(sales)
		
		if returns:
			credit_note = self.process_merging_into_credit_note(returns)

		self.save() # save consolidated_sales_invoice & consolidated_credit_note ref in merge log

		self.update_pos_invoices(pos_invoice_docs, sales_invoice, credit_note)

	def on_cancel(self):
		pos_invoice_docs = [frappe.get_doc("POS Invoice", d.pos_invoice) for d in self.pos_invoices]

		self.update_pos_invoices(pos_invoice_docs)
		self.cancel_linked_invoices()

	def process_merging_into_sales_invoice(self, data):
		sales_invoice = self.get_new_sales_invoice()
		
		sales_invoice = self.merge_pos_invoice_into(sales_invoice, data)

		sales_invoice.is_consolidated = 1
		sales_invoice.save()
		sales_invoice.submit()
		self.consolidated_invoice = sales_invoice.name

		return sales_invoice.name

	def process_merging_into_credit_note(self, data):
		credit_note = self.get_new_sales_invoice()
		credit_note.is_return = 1

		credit_note = self.merge_pos_invoice_into(credit_note, data)

		credit_note.is_consolidated = 1
		# TODO: return could be against multiple sales invoice which could also have been consolidated?
		# credit_note.return_against = self.consolidated_invoice
		credit_note.save()
		credit_note.submit()
		self.consolidated_credit_note = credit_note.name

		return credit_note.name
	
	def merge_pos_invoice_into(self, invoice, data):
		items, payments, taxes = [], [], []
		loyalty_amount_sum, loyalty_points_sum = 0, 0
		for doc in data:
			map_doc(doc, invoice, table_map={ "doctype": invoice.doctype })
			
			if doc.redeem_loyalty_points:
				invoice.loyalty_redemption_account = doc.loyalty_redemption_account
				invoice.loyalty_redemption_cost_center = doc.loyalty_redemption_cost_center
				loyalty_points_sum += doc.loyalty_points
				loyalty_amount_sum += doc.loyalty_amount
			
			for item in doc.get('items'):
				found = False
				for i in items:
					if (i.item_code == item.item_code and not i.serial_no and not i.batch_no and
						i.uom == item.uom and i.net_rate == item.net_rate):
						found = True
						i.qty = i.qty + item.qty
				if not found:
					item.rate = item.net_rate
					item.price_list_rate = 0
					si_item = map_child_doc(item, invoice, {"doctype": "Sales Invoice Item"})
					items.append(si_item)
			
			for tax in doc.get('taxes'):
				found = False
				for t in taxes:
					if t.account_head == tax.account_head and t.cost_center == tax.cost_center:
						t.tax_amount = flt(t.tax_amount) + flt(tax.tax_amount_after_discount_amount)
						t.base_tax_amount = flt(t.base_tax_amount) + flt(tax.base_tax_amount_after_discount_amount)
						found = True
				if not found:
					tax.charge_type = 'Actual'
					tax.included_in_print_rate = 0
					tax.tax_amount = tax.tax_amount_after_discount_amount
					tax.base_tax_amount = tax.base_tax_amount_after_discount_amount
					taxes.append(tax)

			for payment in doc.get('payments'):
				found = False
				for pay in payments:
					if pay.account == payment.account and pay.mode_of_payment == payment.mode_of_payment:
						pay.amount = flt(pay.amount) + flt(payment.amount)
						pay.base_amount = flt(pay.base_amount) + flt(payment.base_amount)
						found = True
				if not found:
					payments.append(payment)

		if loyalty_points_sum:
			invoice.redeem_loyalty_points = 1
			invoice.loyalty_points = loyalty_points_sum
			invoice.loyalty_amount = loyalty_amount_sum

		invoice.set('items', items)
		invoice.set('payments', payments)
		invoice.set('taxes', taxes)
		invoice.additional_discount_percentage = 0
		invoice.discount_amount = 0.0
		invoice.taxes_and_charges = None
		invoice.ignore_pricing_rule = 1

		return invoice
	
	def get_new_sales_invoice(self):
		sales_invoice = frappe.new_doc('Sales Invoice')
		sales_invoice.customer = self.customer
		sales_invoice.is_pos = 1
		# date can be pos closing date?
		sales_invoice.posting_date = getdate(nowdate())

		return sales_invoice
	
	def update_pos_invoices(self, invoice_docs, sales_invoice='', credit_note=''):
		for doc in invoice_docs:
			doc.load_from_db()
			doc.update({ 'consolidated_invoice': None if self.docstatus==2 else (credit_note if doc.is_return else sales_invoice) })
			doc.set_status(update=True)
			doc.save()

	def cancel_linked_invoices(self):
		for si_name in [self.consolidated_invoice, self.consolidated_credit_note]:
			if not si_name: continue
			si = frappe.get_doc('Sales Invoice', si_name)
			si.flags.ignore_validate = True
			si.cancel()

def get_all_unconsolidated_invoices():
	filters = {
		'consolidated_invoice': [ 'in', [ '', None ]],
		'status': ['not in', ['Consolidated']],
		'docstatus': 1
	}
	pos_invoices = frappe.db.get_all('POS Invoice', filters=filters,
		fields=["name as pos_invoice", 'posting_date', 'grand_total', 'customer'])
	
	return pos_invoices

def get_invoice_customer_map(pos_invoices):
	# pos_invoice_customer_map = { 'Customer 1': [{}, {}, {}], 'Custoemr 2' : [{}] }
	pos_invoice_customer_map = {}
	for invoice in pos_invoices:
		customer = invoice.get('customer')
		pos_invoice_customer_map.setdefault(customer, [])
		pos_invoice_customer_map[customer].append(invoice)
	
	return pos_invoice_customer_map

def consolidate_pos_invoices(pos_invoices=[], closing_entry={}):
	invoices = pos_invoices or closing_entry.get('pos_transactions') or get_all_unconsolidated_invoices()
	invoice_by_customer = get_invoice_customer_map(invoices)

	if len(invoices) >= 5 and closing_entry:
		enqueue_job(create_merge_logs, invoice_by_customer, closing_entry)
		closing_entry.set_status(update=True, status='Queued')
	else:
		create_merge_logs(invoice_by_customer, closing_entry)

def unconsolidate_pos_invoices(closing_entry):
	merge_logs = frappe.get_all(
		'POS Invoice Merge Log',
		filters={ 'pos_closing_entry': closing_entry.name },
		pluck='name'
	)

	if len(merge_logs) >= 5:
		enqueue_job(cancel_merge_logs, merge_logs, closing_entry)
		closing_entry.set_status(update=True, status='Queued')
	else:
		cancel_merge_logs(merge_logs, closing_entry)

def create_merge_logs(invoice_by_customer, closing_entry={}):
	for customer, invoices in iteritems(invoice_by_customer):
		merge_log = frappe.new_doc('POS Invoice Merge Log')
		merge_log.posting_date = getdate(nowdate())
		merge_log.customer = customer
		merge_log.pos_closing_entry = closing_entry.get('name', None)

		merge_log.set('pos_invoices', invoices)
		merge_log.save(ignore_permissions=True)
		merge_log.submit()
	
	if closing_entry:
		closing_entry.set_status(update=True, status='Submitted')
		closing_entry.update_opening_entry()

def cancel_merge_logs(merge_logs, closing_entry={}):
	for log in merge_logs:
		merge_log = frappe.get_doc('POS Invoice Merge Log', log)
		merge_log.flags.ignore_permissions = True
		merge_log.cancel()

	if closing_entry:
		closing_entry.set_status(update=True, status='Cancelled')
		closing_entry.update_opening_entry(for_cancel=True)

def enqueue_job(job, invoice_by_customer, closing_entry):
	check_scheduler_status()

	job_name = closing_entry.get("name")
	if not job_already_enqueued(job_name):
		enqueue(
			job,
			queue="long",
			timeout=10000,
			event="processing_merge_logs",
			job_name=job_name,
			closing_entry=closing_entry,
			invoice_by_customer=invoice_by_customer,
			now=frappe.conf.developer_mode or frappe.flags.in_test
		)

		if job == create_merge_logs:
			msg = _('POS Invoices will be consolidated in a background process')
		else:
			msg = _('POS Invoices will be unconsolidated in a background process')

		frappe.msgprint(msg, alert=1)

def check_scheduler_status():
	if is_scheduler_inactive() and not frappe.flags.in_test:
		frappe.throw(_("Scheduler is inactive. Cannot enqueue job."), title=_("Scheduler Inactive"))

def job_already_enqueued(job_name):
	enqueued_jobs = [d.get("job_name") for d in get_info()]
	if job_name in enqueued_jobs:
		return True