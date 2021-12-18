# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.core.page.background_jobs.background_jobs import get_info
from frappe.model.document import Document
from frappe.model.mapper import map_child_doc, map_doc
from frappe.utils import flt, getdate, nowdate
from frappe.utils.background_jobs import enqueue
from frappe.utils.scheduler import is_scheduler_inactive


class POSInvoiceMergeLog(Document):
	def validate(self):
		self.validate_customer()
		self.validate_pos_invoice_status()

	def validate_customer(self):
		if self.merge_invoices_based_on == 'Customer Group':
			return

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
					msg = (_("Row #{}: Original Invoice {} of return invoice {} is {}.")
								.format(d.idx, bold_return_against, bold_pos_invoice, bold_unconsolidated))
					msg += " "
					msg += _("Original invoice should be consolidated before or along with the return invoice.")
					msg += "<br><br>"
					msg += _("You can add original invoice {} manually to proceed.").format(bold_return_against)
					frappe.throw(msg)

	def on_submit(self):
		pos_invoice_docs = [frappe.get_doc("POS Invoice", d.pos_invoice) for d in self.pos_invoices]

		sales = [d for d in pos_invoice_docs if d.get('is_return') == 0]
		returns = [d for d in pos_invoice_docs if d.get('is_return') == 1]
		advances, cn_amount_mapping = get_pos_advance_credit_notes(sales, returns)

		sales_invoice, credit_note, advance_credit_note, advance_credit_note_doc = "", "", "", ""
		if returns:
			credit_note = self.process_merging_into_credit_note(returns)

		if advances:
			advance_credit_note = self.process_merging_into_credit_note(advances, is_advance=True)
			advance_credit_note_doc = frappe.get_doc("Sales Invoice", advance_credit_note)

		if sales:
			sales_invoice = self.process_merging_into_sales_invoice(sales, advance=advance_credit_note_doc)

		self.save() # save consolidated_sales_invoice & consolidated_credit_note ref in merge log)

		#reset pos cn outstanding to 0
		if advance_credit_note_doc:
			set_pos_cn_outstanding_value(advances, cn_amount_mapping, set_zero=True)

		self.update_pos_invoices(pos_invoice_docs, sales_invoice, credit_note, advance_credit_note)

	def on_cancel(self):
		pos_invoice_docs = [frappe.get_doc("POS Invoice", d.pos_invoice) for d in self.pos_invoices]

		sales = [d for d in pos_invoice_docs if d.get('is_return') == 0]
		returns = [d for d in pos_invoice_docs if d.get('is_return') == 1]
		advances, cn_amount_mapping = get_pos_advance_credit_notes(sales, returns)

		if cn_amount_mapping:
			self.update_pos_invoices(pos_invoice_docs, cn_amount_mapping=cn_amount_mapping)
		else:
			self.update_pos_invoices(pos_invoice_docs)


		self.cancel_linked_invoices()

	def process_merging_into_sales_invoice(self, data, advance=None):
		sales_invoice = self.get_new_sales_invoice()

		sales_invoice = self.merge_pos_invoice_into(sales_invoice, data, advance=advance)

		sales_invoice.is_consolidated = 1
		sales_invoice.set_posting_time = 1
		sales_invoice.posting_date = getdate(self.posting_date)
		sales_invoice.save()
		# frappe.throw('here')
		sales_invoice.submit()

		self.consolidated_invoice = sales_invoice.name

		return sales_invoice.name

	def process_merging_into_credit_note(self, data, is_advance=False):
		credit_note = self.get_new_sales_invoice()
		credit_note.is_return = 1

		credit_note = self.merge_pos_invoice_into(credit_note, data)

		credit_note.is_consolidated = 1
		credit_note.set_posting_time = 1
		credit_note.posting_date = getdate(self.posting_date)
		# TODO: return could be against multiple sales invoice which could also have been consolidated?
		# credit_note.return_against = self.consolidated_invoice
		credit_note.save()
		credit_note.submit()

		if is_advance:
			self.consolidate_advances_credit_note = credit_note.name
		else:
			self.consolidated_credit_note = credit_note.name

		return credit_note.name

	def merge_pos_invoice_into(self, invoice, data, advance=None):
		items, payments, taxes = [], [], []

		loyalty_amount_sum, loyalty_points_sum = 0, 0

		rounding_adjustment, base_rounding_adjustment = 0, 0
		rounded_total, base_rounded_total = 0, 0

		loyalty_amount_sum, loyalty_points_sum, idx = 0, 0, 1


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
						i.uom == item.uom and i.net_rate == item.net_rate and i.warehouse == item.warehouse):
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
						update_item_wise_tax_detail(t, tax)
						found = True
				if not found:
					tax.charge_type = 'Actual'
					tax.idx = idx
					idx += 1
					tax.included_in_print_rate = 0
					tax.tax_amount = tax.tax_amount_after_discount_amount
					tax.base_tax_amount = tax.base_tax_amount_after_discount_amount
					tax.item_wise_tax_detail = tax.item_wise_tax_detail
					taxes.append(tax)

			for payment in doc.get('payments'):
				found = False
				if payment.type == 'Credit Note' and payment.credit_note:
					found = True
					self.get_advance_pos_credit_notes(invoice, payment, advance)
					continue
				for pay in payments:
					if pay.account == payment.account and pay.mode_of_payment == payment.mode_of_payment:
						pay.amount = flt(pay.amount) + flt(payment.amount)
						pay.base_amount = flt(pay.base_amount) + flt(payment.base_amount)
						found = True
				if not found:
					payments.append(payment)
			rounding_adjustment += doc.rounding_adjustment
			rounded_total += doc.rounded_total
			base_rounding_adjustment += doc.base_rounding_adjustment
			base_rounded_total += doc.base_rounded_total


		if loyalty_points_sum:
			invoice.redeem_loyalty_points = 1
			invoice.loyalty_points = loyalty_points_sum
			invoice.loyalty_amount = loyalty_amount_sum

		invoice.set('items', items)
		invoice.set('payments', payments)
		invoice.set('taxes', taxes)
		invoice.set('rounding_adjustment',rounding_adjustment)
		invoice.set('base_rounding_adjustment',base_rounding_adjustment)
		invoice.set('rounded_total',rounded_total)
		invoice.set('base_rounded_total',base_rounded_total)
		invoice.additional_discount_percentage = 0
		invoice.discount_amount = 0.0
		invoice.taxes_and_charges = None
		invoice.ignore_pricing_rule = 1
		invoice.customer = self.customer

		if self.merge_invoices_based_on == 'Customer Group':
			invoice.flags.ignore_pos_profile = True
			invoice.pos_profile = ''

		return invoice


	def get_advance_pos_credit_notes(self, invoice, payment, advance=None):
		si = advance
		advance_row = {
				"reference_type": "Sales Invoice",
				"reference_name":si.name,
				"advance_amount": flt(abs(si.get("outstanding_amount"))),
				"allocated_amount": flt(payment.get("amount")),
				# "ref_exchange_rate": flt(si.get("exchange_rate")) # exchange_rate of advance entry
			}
		invoice.append("advances",advance_row)


	def get_new_sales_invoice(self):
		sales_invoice = frappe.new_doc('Sales Invoice')
		sales_invoice.customer = self.customer
		sales_invoice.is_pos = 1

		return sales_invoice

	def update_pos_invoices(self, invoice_docs, sales_invoice='', credit_note='', advance_credit_note='', cn_amount_mapping=None):
		advances = []
		if cn_amount_mapping:
			advances = [frappe.get_doc("POS Invoice", cn) for cn in cn_amount_mapping]

		for doc in invoice_docs:
			doc.load_from_db()
			if doc.is_return:
				if doc_is_used_as_cn_mop(doc, invoice_docs):
					cons_inv = advance_credit_note
				else:
					cons_inv = credit_note
			else:
				cons_inv = sales_invoice

			if cn_amount_mapping and self.docstatus == 2:
				# reset the outstanding values on cancellation
				set_pos_cn_outstanding_value(advances, cn_amount_mapping, set_zero=False)

			doc.update({'consolidated_invoice': None if self.docstatus==2 else cons_inv})
			doc.set_status(update=True)
			doc.save()

	def cancel_linked_invoices(self):
		for si_name in [self.consolidated_invoice, self.consolidated_credit_note, self.consolidate_advances_credit_note]:
			if not si_name: continue
			si = frappe.get_doc('Sales Invoice', si_name)
			si.flags.ignore_validate = True
			si.cancel()

def get_pos_advance_credit_notes(sales, returns):
	advances = []
	cn_amount_mapping = {}
	for doc in sales:
		found = 0
		for p in doc.payments:
			if found:
				break
			if p.type == "Credit Note":
				found = 1
				ret = remove_from_returns_list(returns, p.credit_note)
				if ret:
					cn_amount_mapping[ret.name] = p.amount
					advances.append(ret)

	set_pos_cn_outstanding_value(advances, cn_amount_mapping)

	return advances, cn_amount_mapping

def remove_from_returns_list(returns,doc):
	for pos_inv in returns:
		if pos_inv.get('name') == doc:
			return returns.pop(returns.index(pos_inv))

def set_pos_cn_outstanding_value(advances, cn_amount_mapping, set_zero=False):
	for cn in advances:
		cn.load_from_db()
		cn.flags.ignore_validate_update_after_submit = True
		cn.outstanding_amount = flt(cn_amount_mapping[cn.name]) if not set_zero else 0.0
		cn.save()
		cn.flags.ignore_validate_update_after_submit = False


def update_item_wise_tax_detail(consolidate_tax_row, tax_row):
	consolidated_tax_detail = json.loads(consolidate_tax_row.item_wise_tax_detail)
	tax_row_detail = json.loads(tax_row.item_wise_tax_detail)

	if not consolidated_tax_detail:
		consolidated_tax_detail = {}

	for item_code, tax_data in tax_row_detail.items():
		if consolidated_tax_detail.get(item_code):
			consolidated_tax_data = consolidated_tax_detail.get(item_code)
			consolidated_tax_detail.update({
				item_code: [consolidated_tax_data[0], consolidated_tax_data[1] + tax_data[1]]
			})
		else:
			consolidated_tax_detail.update({
				item_code: [tax_data[0], tax_data[1]]
			})

	consolidate_tax_row.item_wise_tax_detail = json.dumps(consolidated_tax_detail, separators=(',', ':'))

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
	# pos_invoice_customer_map = { 'Customer 1': [{}, {}, {}], 'Customer 2' : [{}] }
	pos_invoice_customer_map = {}
	for invoice in pos_invoices:
		customer = invoice.get('customer')
		pos_invoice_customer_map.setdefault(customer, [])
		pos_invoice_customer_map[customer].append(invoice)

	return pos_invoice_customer_map

def consolidate_pos_invoices(pos_invoices=None, closing_entry=None):
	invoices = pos_invoices or (closing_entry and closing_entry.get('pos_transactions'))
	if frappe.flags.in_test and not invoices:
		invoices = get_all_unconsolidated_invoices()

	invoice_by_customer = get_invoice_customer_map(invoices)

	if len(invoices) >= 100 and closing_entry:
		closing_entry.set_status(update=True, status='Queued')
		enqueue_job(create_merge_logs, invoice_by_customer=invoice_by_customer, closing_entry=closing_entry)
	else:
		create_merge_logs(invoice_by_customer, closing_entry)

def unconsolidate_pos_invoices(closing_entry):
	merge_logs = frappe.get_all(
		'POS Invoice Merge Log',
		filters={ 'pos_closing_entry': closing_entry.name },
		pluck='name'
	)

	if len(merge_logs) >= 100:
		closing_entry.set_status(update=True, status='Queued')
		enqueue_job(cancel_merge_logs, merge_logs=merge_logs, closing_entry=closing_entry)
	else:
		cancel_merge_logs(merge_logs, closing_entry)

def create_merge_logs(invoice_by_customer, closing_entry=None):
	try:
		for customer, invoices in invoice_by_customer.items():
			merge_log = frappe.new_doc('POS Invoice Merge Log')
			merge_log.posting_date = getdate(closing_entry.get('posting_date')) if closing_entry else nowdate()
			merge_log.customer = customer
			merge_log.pos_closing_entry = closing_entry.get('name') if closing_entry else None

			merge_log.set('pos_invoices', invoices)
			merge_log.save(ignore_permissions=True)
			merge_log.submit()

		if closing_entry:
			closing_entry.set_status(update=True, status='Submitted')
			closing_entry.db_set('error_message', '')
			closing_entry.update_opening_entry()

	except Exception as e:
		frappe.db.rollback()
		message_log = frappe.message_log.pop() if frappe.message_log else str(e)
		error_message = safe_load_json(message_log)

		if closing_entry:
			closing_entry.set_status(update=True, status='Failed')
			closing_entry.db_set('error_message', error_message)
		raise

	finally:
		frappe.db.commit()
		frappe.publish_realtime('closing_process_complete', {'user': frappe.session.user})

def cancel_merge_logs(merge_logs, closing_entry=None):
	try:
		for log in merge_logs:
			merge_log = frappe.get_doc('POS Invoice Merge Log', log)
			merge_log.flags.ignore_permissions = True
			merge_log.cancel()

		if closing_entry:
			closing_entry.set_status(update=True, status='Cancelled')
			closing_entry.db_set('error_message', '')
			closing_entry.update_opening_entry(for_cancel=True)

	except Exception as e:
		frappe.db.rollback()
		message_log = frappe.message_log.pop() if frappe.message_log else str(e)
		error_message = safe_load_json(message_log)

		if closing_entry:
			closing_entry.set_status(update=True, status='Submitted')
			closing_entry.db_set('error_message', error_message)
		raise

	finally:
		frappe.db.commit()
		frappe.publish_realtime('closing_process_complete', {'user': frappe.session.user})

def enqueue_job(job, **kwargs):
	check_scheduler_status()

	closing_entry = kwargs.get('closing_entry') or {}

	job_name = closing_entry.get("name")
	if not job_already_enqueued(job_name):
		enqueue(
			job,
			**kwargs,
			queue="long",
			timeout=10000,
			event="processing_merge_logs",
			job_name=job_name,
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

def safe_load_json(message):
	try:
		json_message = json.loads(message).get('message')
	except Exception:
		json_message = message

	return json_message

def doc_is_used_as_cn_mop(doc, invoice_docs):
	for doc in invoice_docs:
		for p in doc.payments:
			if p.type == 'Credit Note' and p.credit_note == doc.name:
				return True