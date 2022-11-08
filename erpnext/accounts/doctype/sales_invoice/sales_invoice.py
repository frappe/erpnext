# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
import frappe.defaults
from frappe.utils import cint, flt, getdate, add_days, cstr, nowdate
from frappe import _, msgprint, throw
from erpnext.accounts.party import get_party_account, get_due_date
from erpnext.controllers.stock_controller import update_gl_entries_for_reposted_stock_vouchers
from frappe.model.mapper import get_mapped_doc
from erpnext.accounts.doctype.sales_invoice.pos import update_multi_mode_option
from frappe.model.naming import set_name_by_naming_series
from erpnext.controllers.selling_controller import SellingController
from erpnext.accounts.utils import get_account_currency
from erpnext.stock.doctype.delivery_note.delivery_note import update_indirectly_billed_qty_for_dn_against_so,\
	update_directly_billed_qty_for_dn
from erpnext.projects.doctype.timesheet.timesheet import get_projectwise_timesheet_data
from erpnext.assets.doctype.asset.depreciation import get_disposal_account_and_cost_center,\
	get_gl_entries_on_asset_disposal
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos, get_delivery_note_serial_no
from erpnext.setup.doctype.company.company import update_company_current_month_sales
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.accounts.doctype.loyalty_program.loyalty_program import get_loyalty_program_details_with_points,\
	validate_loyalty_points
from erpnext.accounts.deferred_revenue import validate_service_stop_date
from erpnext.erpnext_integrations.fbr_pos_integration import validate_fbr_pos_invoice, before_cancel_fbr_pos_invoice,\
	on_submit_fbr_pos_invoice

from erpnext.healthcare.utils import manage_invoice_submit_cancel

from six import iteritems

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}


class SalesInvoice(SellingController):
	def __init__(self, *args, **kwargs):
		super(SalesInvoice, self).__init__(*args, **kwargs)

	def autoname(self):
		if self.has_stin:
			set_name_by_naming_series(self, 'stin')

	def onload(self):
		super(SalesInvoice, self).onload()
		self.set_can_make_vehicle_gate_pass()

	def validate(self):
		self.validate_posting_time()
		super(SalesInvoice, self).validate()

		self.validate_order_required()
		self.validate_stin()
		self.validate_project_customer()
		self.validate_pos_return()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.check_sales_order_on_hold_or_close()
		self.validate_debit_to_acc()
		self.validate_return_against()
		self.clear_unallocated_advances("Sales Invoice Advance", "advances")
		self.validate_write_off_account()
		self.validate_account_for_change_amount()
		self.validate_fixed_asset()
		self.set_income_account_for_fixed_assets()
		validate_inter_company_party(self.doctype, self.customer, self.company, self.inter_company_reference)

		if cint(self.is_pos):
			self.validate_pos()

		if cint(self.update_stock):
			self.validate_dropship_item()
			self.validate_item_code()
			self.validate_warehouse()
			self.update_current_stock()
			self.validate_delivery_note_if_update_stock()

		self.validate_update_stock_mandatory()

		# validate service stop date to lie in between start and end date
		validate_service_stop_date(self)

		if not self.is_opening:
			self.is_opening = 'No'

		if self.redeem_loyalty_points:
			lp = frappe.get_doc('Loyalty Program', self.loyalty_program)
			self.loyalty_redemption_account = lp.expense_account if not self.loyalty_redemption_account else self.loyalty_redemption_account
			self.loyalty_redemption_cost_center = lp.cost_center if not self.loyalty_redemption_cost_center else self.loyalty_redemption_cost_center

		self.set_against_income_account()
		self.validate_c_form()
		self.validate_time_sheets_are_submitted()
		if not self.is_return:
			self.validate_serial_numbers()
		self.update_packing_list()
		self.set_billing_hours_and_amount()
		self.update_timesheet_billing_for_project()

		# validate amount in mode of payments for returned invoices for pos must be negative
		if self.is_pos and not self.is_return:
			self.verify_payment_amount_is_positive()
		if self.is_pos and self.is_return:
			self.verify_payment_amount_is_negative()

		if self.redeem_loyalty_points and self.loyalty_program and self.loyalty_points:
			validate_loyalty_points(self, self.loyalty_points)

		self.validate_with_previous_doc()
		self.set_delivery_status()
		self.set_returned_status()
		self.set_status()
		self.set_title()

		validate_fbr_pos_invoice(self)

	def before_save(self):
		set_account_for_mode_of_payment(self)

	def on_update(self):
		self.set_paid_amount()

	def on_submit(self):
		self.validate_pos_paid_amount()
		self.validate_tax_id_mandatory()

		if not self.auto_repeat:
			frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
				self.company, self.base_grand_total, self)

		self.validate_previous_docstatus()
		self.update_previous_doc_status()

		self.clear_unallocated_mode_of_payments()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		if self.update_stock == 1:
			self.update_stock_ledger()

		self.validate_vehicle_registration_order()

		# this sequence because outstanding may get -ve
		self.make_gl_entries()

		if not self.is_return:
			self.check_credit_limit()

		self.update_serial_no()

		if not cint(self.is_pos) == 1 and not self.is_return:
			self.update_against_document_in_jv()

		self.update_time_sheet(self.name)

		if frappe.get_cached_value('Selling Settings', None, 'sales_update_frequency') == "Each Transaction":
			update_company_current_month_sales(self.company)

		update_linked_doc(self.doctype, self.name, self.inter_company_reference)

		# create the loyalty point ledger entry if the customer is enrolled in any loyalty program
		if not self.is_return and self.loyalty_program:
			self.make_loyalty_point_entry()
		elif self.is_return and self.return_against and self.loyalty_program:
			against_si_doc = frappe.get_doc("Sales Invoice", self.return_against)
			against_si_doc.delete_loyalty_point_entry()
			against_si_doc.make_loyalty_point_entry()
		if self.redeem_loyalty_points and self.loyalty_points:
			self.apply_loyalty_points()

		self.validate_zero_outstanding()

		# Healthcare Service Invoice.
		if "Healthcare" in frappe.get_active_domains():
			manage_invoice_submit_cancel(self, "on_submit")

		on_submit_fbr_pos_invoice(self)

	def before_cancel(self):
		self.update_time_sheet(None)
		before_cancel_fbr_pos_invoice(self)

	def on_cancel(self):
		super(SalesInvoice, self).on_cancel()

		self.update_previous_doc_status()

		if not self.is_return:
			self.update_serial_no(in_cancel=True)

		self.validate_c_form_on_cancel()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		if self.update_stock == 1:
			self.update_stock_ledger()

		self.make_gl_entries_on_cancel()
		frappe.db.set(self, 'status', 'Cancelled')

		if frappe.get_cached_value('Selling Settings', None, 'sales_update_frequency') == "Each Transaction":
			update_company_current_month_sales(self.company)

		if not self.is_return and self.loyalty_program:
			self.delete_loyalty_point_entry()
		elif self.is_return and self.return_against and self.loyalty_program:
			against_si_doc = frappe.get_doc("Sales Invoice", self.return_against)
			against_si_doc.delete_loyalty_point_entry()
			against_si_doc.make_loyalty_point_entry()

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_reference)

		# Healthcare Service Invoice.
		if "Healthcare" in frappe.get_active_domains():
			manage_invoice_submit_cancel(self, "on_cancel")

	def set_indicator(self):
		"""Set indicator for portal"""
		if self.outstanding_amount < 0:
			self.indicator_title = _("Credit Note Issued")
			self.indicator_color = "darkgrey"
		elif self.outstanding_amount > 0 and getdate(self.due_date) >= getdate(nowdate()):
			self.indicator_color = "orange"
			self.indicator_title = _("Unpaid")
		elif self.outstanding_amount > 0 and getdate(self.due_date) < getdate(nowdate()):
			self.indicator_color = "red"
			self.indicator_title = _("Overdue")
		elif cint(self.is_return) == 1:
			self.indicator_title = _("Return")
			self.indicator_color = "darkgrey"
		else:
			self.indicator_color = "green"
			self.indicator_title = _("Paid")

	def set_title(self):
		if self.get('bill_to') and self.bill_to != self.customer:
			self.title = "{0} ({1})".format(self.bill_to_name or self.bill_to, self.customer_name or self.customer)
		else:
			self.title = self.customer_name or self.customer

	def validate_previous_docstatus(self):
		for d in self.get('items'):
			if d.sales_order and frappe.db.get_value("Sales Order", d.sales_order, "docstatus", cache=1) != 1:
				frappe.throw(_("Row #{0}: Sales Order {1} is not submitted").format(d.idx, d.sales_order))

			if d.delivery_note and frappe.db.get_value("Delivery Note", d.delivery_note, "docstatus", cache=1) != 1:
				frappe.throw(_("Row #{0}: Delivery Note {1} is not submitted").format(d.idx, d.delivery_note))

			if self.return_against and frappe.db.get_value("Sales Invoice", self.return_against, "docstatus", cache=1) != 1:
				frappe.throw(_("Return Against Sales Invoice {0} is not submitted").format(self.return_against))

	def update_previous_doc_status(self):
		# Update Quotations
		quotations = []
		for d in self.items:
			if d.quotation and d.quotation not in quotations:
				quotations.append(d.quotation)

		for name in quotations:
			doc = frappe.get_doc("Quotation", name)
			doc.set_ordered_status(update=True)
			doc.update_opportunity()
			doc.set_status(update=True)
			doc.notify_update()

		# Update Sales Orders
		sales_orders = set()
		sales_order_row_names_without_dn = set()
		for d in self.items:
			if d.sales_order:
				sales_orders.add(d.sales_order)
			if d.sales_order_item and not d.delivery_note:
				sales_order_row_names_without_dn.add(d.sales_order_item)

		for name in sales_orders:
			doc = frappe.get_doc("Sales Order", name)
			doc.set_billing_status(update=True)
			doc.set_delivery_status(update=True)

			doc.validate_billed_qty(from_doctype=self.doctype, row_names=sales_order_row_names_without_dn)
			if self.update_stock:
				doc.validate_delivered_qty(from_doctype=self.doctype, row_names=sales_order_row_names_without_dn)

			doc.set_status(update=True)
			doc.notify_update()

		# Update Delivery Notes
		delivery_notes = set()
		delivery_note_row_names = set()
		updated_delivery_notes = []
		for d in self.items:
			if d.delivery_note:
				delivery_notes.add(d.delivery_note)
			if d.delivery_note_item:
				delivery_note_row_names.add(d.delivery_note_item)

			if d.delivery_note and d.delivery_note_item:
				update_directly_billed_qty_for_dn(d.delivery_note, d.delivery_note_item)
				updated_delivery_notes.append(d.delivery_note)
			if d.sales_order_item:
				updated_delivery_notes += update_indirectly_billed_qty_for_dn_against_so(d.sales_order_item)

		for name in set(updated_delivery_notes):
			doc = frappe.get_doc("Delivery Note", name)
			doc.set_billing_status(update=True)

			if doc.name in delivery_notes:
				doc.validate_billed_qty(from_doctype=self.doctype, row_names=delivery_note_row_names)

			doc.set_status(update=True)
			doc.notify_update()

		# Update Returned Against Sales Invoice
		if self.is_return and self.return_against:
			doc = frappe.get_doc("Sales Invoice", self.return_against)
			doc.set_returned_status(update=True)

			if self.update_stock:
				doc.validate_returned_qty(from_doctype=self.doctype)

		self.update_project_billing_and_sales()

	def set_delivery_status(self, update=False, update_modified=True):
		delivered_qty_map = self.get_delivered_qty_map()

		# update values in rows
		for d in self.items:
			d.delivered_qty = flt(delivered_qty_map.get(d.name))

			if update:
				d.db_set({
					'delivered_qty': d.delivered_qty,
				}, update_modified=update_modified)

	def set_returned_status(self, update=False, update_modified=True):
		data = self.get_returned_status_data()

		# update values in rows
		for d in self.items:
			d.returned_qty = flt(data.returned_qty_map.get(d.name))
			d.base_returned_amount = flt(data.returned_amount_map.get(d.name))

			if update:
				d.db_set({
					'returned_qty': d.returned_qty,
					'base_returned_amount': d.base_returned_amount,
				}, update_modified=update_modified)

	def get_delivered_qty_map(self):
		delivered_qty_map = {}

		if self.update_stock and self.docstatus == 1:
			for d in self.items:
				delivered_qty_map[d.name] = flt(d.qty)

			return delivered_qty_map

		already_delivered_rows = [d.delivery_note_item for d in self.items if d.delivery_note_item]
		deliverable_rows = [d.name for d in self.items if not d.delivery_note_item]

		if already_delivered_rows:
			delivery_note_qty = frappe.db.sql("""
				select i.name, i.qty
				from `tabDelivery Note Item` i
				inner join `tabDelivery Note` p on p.name = i.parent
				where p.docstatus = 1 and i.name in %s
			""", [already_delivered_rows])

			for delivery_note_item, delivered_qty in delivery_note_qty:
				for d in self.items:
					if d.delivery_note_item == delivery_note_item:
						delivered_qty_map[d.name] = delivered_qty

		if deliverable_rows and self.docstatus == 1:
			delivery_note_qty = frappe.db.sql("""
				select i.sales_invoice_item, sum(i.qty)
				from `tabDelivery Note Item` i
				inner join `tabDelivery Note` p on p.name = i.parent
				where p.docstatus = 1 and i.sales_invoice_item in %s
				group by i.sales_invoice_item
			""", [deliverable_rows])

			for sales_invoice_item, delivered_qty in delivery_note_qty:
				delivered_qty_map[sales_invoice_item] = delivered_qty

		return delivered_qty_map

	def get_returned_status_data(self):
		out = frappe._dict()
		out.returned_qty_map = {}
		out.returned_amount_map = {}

		row_names = [d.name for d in self.items]
		if self.docstatus == 1 and row_names:
			returned_with_sales_invoice = frappe.db.sql("""
				select i.sales_invoice_item,
					-1 * sum(i.qty) as qty,
					-1 * sum(i.base_net_amount) as base_net_amount
				from `tabSales Invoice Item` i
				inner join `tabSales Invoice` p on p.name = i.parent
				where p.docstatus = 1 and p.is_return = 1 and (p.update_stock = 1 or p.reopen_order = 1)
					and i.sales_invoice_item in %s
				group by i.sales_invoice_item
			""", [row_names], as_dict=1)

			for d in returned_with_sales_invoice:
				out.returned_qty_map[d.sales_invoice_item] = d.qty
				out.returned_amount_map[d.sales_invoice_item] = d.base_net_amount

		return out

	def validate_delivered_qty(self, from_doctype=None, row_names=None):
		items_without_delivery_note = [d for d in self.items if not d.delivery_note]
		self.validate_completed_qty('delivered_qty', 'qty', items_without_delivery_note,
			allowance_type=None, from_doctype=from_doctype, row_names=row_names)

	def validate_returned_qty(self, from_doctype=None, row_names=None):
		self.validate_completed_qty('returned_qty', 'qty', self.items,
			allowance_type=None, from_doctype=from_doctype, row_names=row_names)

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		previous_status = self.status
		precision = self.precision("outstanding_amount")
		outstanding_amount = flt(self.outstanding_amount, precision)
		due_date = getdate(self.due_date)
		today = getdate()

		discounting_status = None
		if self.is_discounted:
			discounting_status = get_discounting_status(self.name)

		if not status:
			# Cancelled
			if self.docstatus == 2:
				self.status = "Cancelled"

			# Submitted
			elif self.docstatus == 1:
				# Positive Outstanding
				if outstanding_amount > 0:
					# Discounted
					if self.is_discounted and discounting_status == 'Disbursed':
						if due_date < today:
							self.status = "Overdue and Discounted"
						else:
							self.status = "Unpaid and Discounted"

					# Normal / Not Discounted
					else:
						if due_date < today:
							self.status = "Overdue"
						else:
							self.status = "Unpaid"

				# Negative Outstanding
				elif outstanding_amount < 0:
					self.status = "Credit Note Issued"

				# Zero Outstanding
				else:
					if self.is_return:
						self.status = "Return"
					elif frappe.db.get_value('Sales Invoice', {'is_return': 1, 'return_against': self.name, 'docstatus': 1}):
						self.status = "Credit Note Issued"
					else:
						self.status = "Paid"

			# Draft
			else:
				self.status = "Draft"

		self.add_status_comment(previous_status)

		if update:
			self.db_set('status', self.status, update_modified=update_modified)

	def validate_fixed_asset(self):
		for d in self.get("items"):
			if d.is_fixed_asset and d.meta.get_field("asset") and d.asset:
				asset = frappe.get_doc("Asset", d.asset)
				if self.doctype == "Sales Invoice" and self.docstatus == 1:
					if self.update_stock:
						frappe.throw(_("'Update Stock' cannot be checked for fixed asset sale"))

					elif asset.status in ("Scrapped", "Cancelled", "Sold"):
						frappe.throw(_("Row #{0}: Asset {1} cannot be submitted, it is already {2}").format(d.idx, d.asset, asset.status))

	def validate_pos_return(self):
		if self.is_pos and self.is_return:
			total_amount_in_payments = 0
			for payment in self.payments:
				total_amount_in_payments += payment.amount

			total_amount_in_payments += self.write_off_amount

			invoice_total = self.rounded_total or self.grand_total
			if flt(total_amount_in_payments, self.precision('grand_total')) < invoice_total:
				frappe.throw(_("Total payments amount can't be greater than {}".format(frappe.format(-invoice_total, df=self.meta.get_field('grand_total')))))

	def validate_pos_paid_amount(self):
		if self.is_pos:
			if len(self.payments) == 0:
				frappe.throw(_("At least one mode of payment is required for POS Invoice"))

			if not flt(self.paid_amount):
				frappe.throw(_("Paid Amount cannot be zero for POS Invoice"))

	def validate_tax_id_mandatory(self):
		if self.get('has_stin') and not self.get('tax_id') and not self.get('tax_cnic') and not self.get('tax_strn'):
			restricted = frappe.get_cached_value("Accounts Settings", None, 'restrict_sales_tax_invoice_without_tax_id')
			if restricted:
				frappe.throw(_("Customer Tax ID or Identification Number is mandatory for Sales Tax Invoice"))

	def check_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit

		validate_against_credit_limit = False
		bypass_credit_limit_check_at_sales_order = frappe.db.get_value("Customer Credit Limit",
			filters={'parent': self.customer, 'parenttype': 'Customer', 'company': self.company},
			fieldname=["bypass_credit_limit_check"])

		if bypass_credit_limit_check_at_sales_order:
			validate_against_credit_limit = True

		for d in self.get("items"):
			if not (d.sales_order or d.delivery_note):
				validate_against_credit_limit = True
				break
		if validate_against_credit_limit:
			check_credit_limit(self.customer, self.company, bypass_credit_limit_check_at_sales_order)

	def set_missing_values(self, for_validate=False):
		pos = self.set_pos_fields(for_validate)

		if self.claim_billing:
			self.project = None

		if not self.debit_to:
			self.debit_to = get_party_account("Customer", self.customer, self.company,
				transaction_type=self.get('transaction_type'))
			self.party_account_currency = frappe.get_cached_value("Account", self.debit_to, "account_currency")
		if not self.due_date and self.customer:
			self.due_date = get_due_date(self.posting_date, "Customer", self.customer, self.company)

		super(SalesInvoice, self).set_missing_values(for_validate)

		print_format = pos.get("print_format_for_online") if pos else None
		if not print_format and not cint(frappe.db.get_value('Print Format', 'POS Invoice', 'disabled')):
			print_format = 'POS Invoice'

		if pos:
			return {
				"print_format": print_format,
				"allow_edit_rate": pos.get("allow_user_to_edit_rate"),
				"allow_edit_discount": pos.get("allow_user_to_edit_discount"),
				"campaign": pos.get("campaign")
			}

	def update_time_sheet(self, sales_invoice):
		for d in self.timesheets:
			if d.time_sheet:
				timesheet = frappe.get_doc("Timesheet", d.time_sheet)
				self.update_time_sheet_detail(timesheet, d, sales_invoice)
				timesheet.calculate_total_amounts()
				timesheet.calculate_percentage_billed()
				timesheet.flags.ignore_validate_update_after_submit = True
				timesheet.set_status()
				timesheet.save()

	def update_time_sheet_detail(self, timesheet, args, sales_invoice):
		for data in timesheet.time_logs:
			if (self.project and args.timesheet_detail == data.name) or \
				(not self.project and not data.sales_invoice) or \
				(not sales_invoice and data.sales_invoice == self.name):
				data.sales_invoice = sales_invoice

	def set_paid_amount(self):
		paid_amount = 0.0
		base_paid_amount = 0.0
		for data in self.payments:
			data.base_amount = flt(data.amount*self.conversion_rate, self.precision("base_paid_amount"))
			paid_amount += data.amount
			base_paid_amount += data.base_amount

		self.paid_amount = paid_amount
		self.base_paid_amount = base_paid_amount

	def validate_stin(self):
		if self.amended_from:
			prev_has_stin, prev_stin = frappe.db.get_value(self.doctype, self.amended_from, ['has_stin', 'stin'])
			if self.has_stin != prev_has_stin or self.stin != prev_stin:
				frappe.throw(_("Tax Invoice Number must be the same as the cancelled document {0}").format(self.amended_from))

		if not self.has_stin:
			self.stin = 0

	def validate_time_sheets_are_submitted(self):
		for data in self.timesheets:
			if data.time_sheet:
				status = frappe.db.get_value("Timesheet", data.time_sheet, "status")
				if status not in ['Submitted', 'Payslip']:
					frappe.throw(_("Timesheet {0} is already completed or cancelled").format(data.time_sheet))

	def set_pos_fields(self, for_validate=False):
		"""Set retail related fields from POS Profiles"""
		if cint(self.is_pos) != 1:
			return

		from erpnext.stock.get_item_details import get_pos_profile_item_details, get_pos_profile
		if not self.pos_profile:
			pos_profile = get_pos_profile(self.company) or {}
			self.pos_profile = pos_profile.get('name')

		pos = {}
		if self.pos_profile:
			pos = frappe.get_doc('POS Profile', self.pos_profile)

		if not self.get('payments') and not for_validate:
			update_multi_mode_option(self, pos)

		if not self.account_for_change_amount:
			self.account_for_change_amount = frappe.get_cached_value('Company',  self.company,  'default_cash_account')

		if pos:
			self.allow_print_before_pay = pos.allow_print_before_pay

			if not for_validate:
				self.tax_category = pos.get("tax_category")

			if not for_validate and not self.customer:
				self.customer = pos.customer

			self.ignore_pricing_rule = pos.ignore_pricing_rule
			if pos.get('account_for_change_amount'):
				self.account_for_change_amount = pos.get('account_for_change_amount')

			for fieldname in ('territory', 'naming_series', 'currency', 'letter_head', 'tc_name',
				'company', 'select_print_heading', 'cash_bank_account', 'write_off_account', 'taxes_and_charges',
				'write_off_cost_center', 'apply_discount_on', 'cost_center'):
					if (not for_validate) or (for_validate and not self.get(fieldname)):
						self.set(fieldname, pos.get(fieldname))

			if pos.get("company_address"):
				self.company_address = pos.get("company_address")

			if self.customer:
				customer_price_list, customer_group = frappe.get_value("Customer", self.customer, ['default_price_list', 'customer_group'])
				customer_group_price_list = frappe.get_value("Customer Group", customer_group, 'default_price_list')
				selling_price_list = customer_price_list or customer_group_price_list or pos.get('selling_price_list')
			else:
				selling_price_list = pos.get('selling_price_list')

			if selling_price_list:
				self.set('selling_price_list', selling_price_list)

			if not for_validate:
				self.update_stock = cint(pos.get("update_stock"))

			# set pos values in items
			for item in self.get("items"):
				if item.get('item_code'):
					profile_details = get_pos_profile_item_details(pos, frappe._dict(item.as_dict()), pos)
					for fname, val in iteritems(profile_details):
						if (not for_validate) or (for_validate and not item.get(fname)):
							item.set(fname, val)

			# fetch terms
			if self.tc_name and not self.terms:
				self.terms = frappe.db.get_value("Terms and Conditions", self.tc_name, "terms")

			# fetch charges
			if self.taxes_and_charges and not len(self.get("taxes")):
				self.set_taxes_and_charges()

		return pos

	def get_company_abbr(self):
		return frappe.db.sql("select abbr from tabCompany where name=%s", self.company)[0][0]

	def validate_debit_to_acc(self):
		account = frappe.get_cached_value("Account", self.debit_to,
			["account_type", "report_type", "account_currency"], as_dict=True)

		if not account:
			frappe.throw(_("Debit To is required"), title=_("Account Missing"))

		if account.report_type != "Balance Sheet":
			frappe.throw(_("Please ensure {} account is a Balance Sheet account. \
					You can change the parent account to a Balance Sheet account or select a different account.")
				.format(frappe.bold("Debit To")), title=_("Invalid Account"))

		if self.customer and account.account_type != "Receivable":
			frappe.throw(_("Please ensure {} account is a Receivable account. \
					Change the account type to Receivable or select a different account.")
				.format(frappe.bold("Debit To")), title=_("Invalid Account"))

		self.party_account_currency = account.account_currency

	def clear_unallocated_mode_of_payments(self):
		self.set("payments", self.get("payments", {"amount": ["not in", [0, None, ""]]}))

		frappe.db.sql("""delete from `tabSales Invoice Payment` where parent = %s
			and amount = 0""", self.name)

	def validate_with_previous_doc(self):
		sales_order_compare = [["company", "="], ["currency", "="]]
		delivery_note_compare = [["company", "="], ["currency", "="]]

		if not self.get('claim_billing'):
			sales_order_compare += [["customer", "="], ["project", "="]]
			delivery_note_compare += [["customer", "="], ["project", "="]]

		super(SalesInvoice, self).validate_with_previous_doc({
			"Sales Order": {
				"ref_dn_field": "sales_order",
				"compare_fields": sales_order_compare
			},
			"Sales Order Item": {
				"ref_dn_field": "sales_order_item",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
			"Delivery Note": {
				"ref_dn_field": "delivery_note",
				"compare_fields": delivery_note_compare
			},
			"Delivery Note Item": {
				"ref_dn_field": "delivery_note_item",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="], ["vehicle", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
			"Quotation": {
				"ref_dn_field": "quotation",
				"compare_fields": [["company", "="]]
			},
		})

		if not self.get('project'):
			super(SalesInvoice, self).validate_with_previous_doc({
				"Delivery Note": {
					"ref_dn_field": "delivery_note",
					"compare_fields": [["project", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True
				},
				"Sales Order": {
					"ref_dn_field": "sales_order",
					"compare_fields": [["project", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True
				},
			})

		if not self.is_return and cint(frappe.get_cached_value('Selling Settings', None, 'maintain_same_sales_rate')):
			self.validate_rate_with_reference_doc([
				["Sales Order", "sales_order", "sales_order_item"],
				["Delivery Note", "delivery_note", "delivery_note_item"]
			])

	def validate_return_against(self):
		if cint(self.is_return) and self.return_against:
			against_doc = frappe.get_doc("Sales Invoice", self.return_against)
			if not against_doc:
				frappe.throw(_("Return Against Sales Invoice {0} does not exist").format(self.return_against))
			if against_doc.company != self.company:
				frappe.throw(_("Return Against Sales Invoice {0} must be against the same Company").format(self.return_against))
			if against_doc.customer != self.customer and cstr(against_doc.get('bill_to')) != cstr(self.get('bill_to')):
				frappe.throw(_("Return Against Sales Invoice {0} must be against the same Billing Customer").format(self.return_against))
			if against_doc.debit_to != self.debit_to:
				frappe.throw(_("Return Against Sales Invoice {0} must have the same Debit To account").format(self.return_against))

	def set_against_income_account(self):
		"""Set against account for debit to account"""
		against_acc = []
		for d in self.get('items'):
			if d.income_account and d.income_account not in against_acc:
				against_acc.append(d.income_account)
		self.against_income_account = ', '.join(against_acc)

	def validate_order_required(self):
		"""check in manage account if sales order / delivery note required or not."""
		if self.is_return:
			return

		so_required = frappe.get_cached_value("Selling Settings", None, 'so_required') or 'No'
		dn_required = frappe.get_cached_value("Selling Settings", None, 'dn_required') or 'No'

		if so_required and frappe.get_cached_value('Customer', self.customer, 'so_not_required'):
			so_required = 'No'
		if dn_required and frappe.get_cached_value('Customer', self.customer, 'dn_not_required'):
			dn_required = 'No'

		if self.get('transaction_type'):
			tt_so_required = frappe.get_cached_value('Transaction Type', self.get('transaction_type'), 'so_required')
			tt_dn_required = frappe.get_cached_value('Transaction Type', self.get('transaction_type'), 'dn_required')
			if tt_so_required:
				so_required = tt_so_required
			if tt_dn_required:
				dn_required = tt_dn_required

		if so_required == 'No' and dn_required == 'No':
			return

		for d in self.get('items'):
			if not d.item_code:
				continue

			if so_required == 'Yes' and not d.get('sales_order') and not self.get('is_pos'):
				frappe.throw(_("Row #{0}: Sales Order is mandatory for Item {1}").format(d.idx, d.item_code))

			is_stock_item = frappe.get_cached_value('Item', d.item_code, 'is_stock_item')
			skip_dn_check = self.get('is_pos') and self.get('update_stock')
			if is_stock_item and not skip_dn_check:
				if dn_required == 'Yes' and not d.get('delivery_note'):
					frappe.throw(_("Row #{0}: Delivery Note is mandatory for Item {1}").format(d.idx, d.item_code))
				if dn_required == 'Either Delivery Note or Sales Order' and not d.get('delivery_note') and not d.get('sales_order'):
					frappe.throw(_("Row #{0}: Delivery Note or Sales Order is mandatory for Item {1}").format(d.idx, d.item_code))

	def validate_pos(self):
		if self.is_return:
			grand_total = flt(self.rounded_total) or flt(self.grand_total)
			if flt(self.paid_amount) + flt(self.write_off_amount) - grand_total > \
				1.0/(10.0**(self.precision("grand_total") + 1.0)):
					frappe.throw(_("Paid Amount + Write Off Amount can not be greater than Grand Total"))

	def validate_item_code(self):
		for d in self.get('items'):
			if not d.item_code and self.is_opening == "No":
				msgprint(_("Item Code required at Row No {0}").format(d.idx), raise_exception=True)

	def validate_warehouse(self):
		super(SalesInvoice, self).validate_warehouse()

		for d in self.get_item_list():
			if not d.warehouse and d.item_code and frappe.get_cached_value("Item", d.item_code, "is_stock_item"):
				frappe.throw(_("Warehouse required for stock Item {0}").format(d.item_code))

	def validate_delivery_note_if_update_stock(self):
		if not cint(self.is_return) and cint(self.update_stock):
			for d in self.get("items"):
				if d.delivery_note:
					msgprint(_("Stock cannot be updated against Delivery Note {0}").format(d.delivery_note), raise_exception=1)

	def validate_update_stock_mandatory(self):
		if not cint(self.update_stock) and not self.return_against and not cint(frappe.get_cached_value("Accounts Settings", None, "allow_invoicing_without_updating_stock")):
			packed_items = []
			for p in self.get('packed_items'):
				packed_items.append(p.parent_detail_docname)

			for d in self.items:
				if d.item_code:
					is_stock_item = frappe.get_cached_value("Item", d.item_code, "is_stock_item")\
						or self.is_product_bundle_with_stock_item(d.item_code)
					if d.item_code and not d.delivery_note and is_stock_item:
						frappe.throw(_("'Update Stock' must be enabled for stock items if Sales Invoice is not made from Delivery Note."))

	def validate_write_off_account(self):
		if flt(self.write_off_amount) and not self.write_off_account:
			self.write_off_account = frappe.get_cached_value('Company',  self.company,  'write_off_account')

		if flt(self.write_off_amount) and not self.write_off_account:
			msgprint(_("Please enter Write Off Account"), raise_exception=1)

	def validate_account_for_change_amount(self):
		if flt(self.change_amount) and not self.account_for_change_amount:
			msgprint(_("Please enter Account for Change Amount"), raise_exception=1)

	def validate_c_form(self):
		""" Blank C-form no if C-form applicable marked as 'No'"""
		if self.amended_from and self.c_form_applicable == 'No' and self.c_form_no:
			frappe.db.sql("""delete from `tabC-Form Invoice Detail` where invoice_no = %s
					and parent = %s""", (self.amended_from,	self.c_form_no))

			frappe.db.set(self, 'c_form_no', '')

	def validate_c_form_on_cancel(self):
		""" Display message if C-Form no exists on cancellation of Sales Invoice"""
		if self.c_form_applicable == 'Yes' and self.c_form_no:
			msgprint(_("Please remove this Invoice {0} from C-Form {1}")
				.format(self.name, self.c_form_no), raise_exception = 1)

	def validate_dropship_item(self):
		for item in self.items:
			if item.sales_order:
				if frappe.db.get_value("Sales Order Item", item.sales_order_item, "delivered_by_supplier"):
					frappe.throw(_("Could not update stock, invoice contains drop shipping item."))

	def update_current_stock(self):
		for d in self.get('items'):
			if d.item_code and d.warehouse:
				bin = frappe.db.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
				d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0

		for d in self.get('packed_items'):
			bin = frappe.db.sql("select actual_qty, projected_qty from `tabBin` where item_code =	%s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
			d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0
			d.projected_qty = bin and flt(bin[0]['projected_qty']) or 0

	def update_packing_list(self):
		if cint(self.update_stock) == 1:
			from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
			make_packing_list(self)
		else:
			self.set('packed_items', [])

	def set_billing_hours_and_amount(self):
		if not self.project:
			for timesheet in self.timesheets:
				ts_doc = frappe.get_doc('Timesheet', timesheet.time_sheet)
				if not timesheet.billing_hours and ts_doc.total_billable_hours:
					timesheet.billing_hours = ts_doc.total_billable_hours

				if not timesheet.billing_amount and ts_doc.total_billable_amount:
					timesheet.billing_amount = ts_doc.total_billable_amount

	def update_timesheet_billing_for_project(self):
		if not self.timesheets and self.project:
			self.add_timesheet_data()
		else:
			self.calculate_billing_amount_for_timesheet()

	def add_timesheet_data(self):
		self.set('timesheets', [])
		if self.project:
			for data in get_projectwise_timesheet_data(self.project):
				self.append('timesheets', {
						'time_sheet': data.parent,
						'billing_hours': data.billing_hours,
						'billing_amount': data.billing_amt,
						'timesheet_detail': data.name
					})

			self.calculate_billing_amount_for_timesheet()

	def calculate_billing_amount_for_timesheet(self):
		total_billing_amount = 0.0
		for data in self.timesheets:
			if data.billing_amount:
				total_billing_amount += data.billing_amount

		self.total_billing_amount = total_billing_amount

	def get_warehouse(self):
		user_pos_profile = frappe.db.sql("""select name, warehouse from `tabPOS Profile`
			where ifnull(user,'') = %s and company = %s""", (frappe.session['user'], self.company))
		warehouse = user_pos_profile[0][1] if user_pos_profile else None

		if not warehouse:
			global_pos_profile = frappe.db.sql("""select name, warehouse from `tabPOS Profile`
				where (user is null or user = '') and company = %s""", self.company)

			if global_pos_profile:
				warehouse = global_pos_profile[0][1]
			elif not user_pos_profile:
				msgprint(_("POS Profile required to make POS Entry"), raise_exception=True)

		return warehouse

	def set_income_account_for_fixed_assets(self):
		disposal_account = depreciation_cost_center = None
		for d in self.get("items"):
			if d.is_fixed_asset:
				if not disposal_account:
					disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(self.company)

				d.income_account = disposal_account
				if not d.cost_center:
					d.cost_center = depreciation_cost_center

	def make_gl_entries(self, gl_entries=None, repost_future_gle=True, from_repost=False):
		auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)
		if not gl_entries:
			gl_entries = self.get_gl_entries()

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries

			make_gl_entries(gl_entries, cancel=(self.docstatus == 2), merge_entries=False, from_repost=from_repost)

			if (repost_future_gle or self.flags.repost_future_gle) and cint(self.update_stock) and cint(auto_accounting_for_stock):
				update_gl_entries_for_reposted_stock_vouchers(self.doctype, self.name, company=self.company)
		elif self.docstatus == 2 and cint(self.update_stock) \
			and cint(auto_accounting_for_stock):
				from erpnext.accounts.general_ledger import delete_gl_entries
				delete_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	def get_gl_entries(self, warehouse_account=None):
		from erpnext.accounts.general_ledger import merge_similar_entries

		gl_entries = []

		self.make_customer_gl_entry(gl_entries)

		self.make_tax_gl_entries(gl_entries)

		self.make_item_gl_entries(gl_entries)

		# merge gl entries before adding pos entries
		gl_entries = merge_similar_entries(gl_entries)

		self.make_loyalty_point_redemption_gle(gl_entries)
		self.make_pos_gl_entries(gl_entries)
		self.make_gle_for_change_amount(gl_entries)

		self.make_write_off_gl_entry(gl_entries)
		self.make_gle_for_rounding_adjustment(gl_entries)

		return gl_entries

	def make_customer_gl_entry(self, gl_entries):
		grand_total = self.rounded_total or self.grand_total

		if grand_total:
			billing_party_type, billing_party = self.get_billing_party()

			# Didnot use base_grand_total to book rounding loss gle
			grand_total_in_company_currency = flt(grand_total * self.conversion_rate,
				self.precision("grand_total"))

			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"party_type": billing_party_type,
					"party": billing_party,
					"against": self.against_income_account,
					"debit": grand_total_in_company_currency,
					"debit_in_account_currency": grand_total_in_company_currency \
						if self.party_account_currency==self.company_currency else grand_total,
					"against_voucher": self.return_against if cint(self.is_return) and self.return_against else None,
					"against_voucher_type": self.doctype if cint(self.is_return) and self.return_against else None,
					"cost_center": self.cost_center,
					"project": self.project
				}, self.party_account_currency, item=self)
			)

	def make_tax_gl_entries(self, gl_entries):
		billing_party_type, billing_party, billing_party_name = self.get_billing_party(with_name=True)

		for tax in self.get("taxes"):
			if flt(tax.base_tax_amount_after_discount_amount):
				account_currency = get_account_currency(tax.account_head)
				gl_entries.append(
					self.get_gl_dict({
						"account": tax.account_head,
						"against": billing_party_name or billing_party,
						"credit": flt(tax.base_tax_amount_after_discount_amount,
							tax.precision("tax_amount_after_discount_amount")),
						"credit_in_account_currency": (flt(tax.base_tax_amount_after_discount_amount,
							tax.precision("base_tax_amount_after_discount_amount")) if account_currency==self.company_currency else
							flt(tax.tax_amount_after_discount_amount, tax.precision("tax_amount_after_discount_amount"))),
						"cost_center": tax.cost_center or self.cost_center
					}, account_currency, item=tax)
				)

	def make_item_gl_entries(self, gl_entries):
		billing_party_type, billing_party, billing_party_name = self.get_billing_party(with_name=True)

		# income account gl entries
		for item in self.get("items"):
			if flt(item.base_net_amount, item.precision("base_net_amount")):
				if item.is_fixed_asset:
					asset = frappe.get_doc("Asset", item.asset)

					if (len(asset.finance_books) > 1 and not item.finance_book
						and asset.finance_books[0].finance_book):
						frappe.throw(_("Select finance book for the item {0} at row {1}")
							.format(item.item_code, item.idx))

					fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(asset,
						item.base_net_amount, item.finance_book)

					for gle in fixed_asset_gl_entries:
						gle["against"] = billing_party_name or billing_party
						gl_entries.append(self.get_gl_dict(gle, item=item))

					asset.db_set("disposal_date", self.posting_date)
					asset.set_status("Sold" if self.docstatus==1 else None)
				else:
					income_account = (item.income_account
						if (not item.enable_deferred_revenue or self.is_return) else item.deferred_revenue_account)

					account_currency = get_account_currency(income_account)
					gl_entries.append(
						self.get_gl_dict({
							"account": income_account,
							"against": billing_party_name or billing_party,
							"credit": flt(item.base_net_amount, item.precision("base_net_amount")),
							"credit_in_account_currency": (flt(item.base_net_amount, item.precision("base_net_amount"))
								if account_currency==self.company_currency
								else flt(item.net_amount, item.precision("net_amount"))),
							"cost_center": item.cost_center or self.cost_center,
							"project": item.get('project') or self.project
						}, account_currency, item=item)
					)

		# expense account gl entries
		if cint(self.update_stock) and \
			erpnext.is_perpetual_inventory_enabled(self.company):
			gl_entries += super(SalesInvoice, self).get_gl_entries()

	def make_loyalty_point_redemption_gle(self, gl_entries):
		if cint(self.redeem_loyalty_points):
			billing_party_type, billing_party, billing_party_name = self.get_billing_party(with_name=True)

			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"party_type": billing_party_type,
					"party": billing_party,
					"against": cstr(self.loyalty_redemption_account),
					"credit": self.loyalty_amount,
					"against_voucher": self.return_against if cint(self.is_return) else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center
				}, item=self)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.loyalty_redemption_account,
					"cost_center": self.cost_center or self.loyalty_redemption_cost_center,
					"against": billing_party_name or billing_party,
					"debit": self.loyalty_amount,
					"remark": "Loyalty Points redeemed by the customer"
				}, item=self)
			)

	def make_pos_gl_entries(self, gl_entries):
		if cint(self.is_pos):
			billing_party_type, billing_party, billing_party_name = self.get_billing_party(with_name=True)

			for payment_mode in self.payments:
				if payment_mode.amount:
					# POS, make payment entries
					gl_entries.append(
						self.get_gl_dict({
							"account": self.debit_to,
							"party_type": billing_party_type,
							"party": billing_party,
							"against": payment_mode.account,
							"credit": payment_mode.base_amount,
							"credit_in_account_currency": payment_mode.base_amount \
								if self.party_account_currency==self.company_currency \
								else payment_mode.amount,
							"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
							"against_voucher_type": self.doctype,
							"cost_center": self.cost_center
						}, self.party_account_currency, item=self)
					)

					payment_mode_account_currency = get_account_currency(payment_mode.account)
					gl_entries.append(
						self.get_gl_dict({
							"account": payment_mode.account,
							"against": billing_party_name or billing_party,
							"debit": payment_mode.base_amount,
							"debit_in_account_currency": payment_mode.base_amount \
								if payment_mode_account_currency==self.company_currency \
								else payment_mode.amount,
							"cost_center": self.cost_center
						}, payment_mode_account_currency, item=self)
					)

	def make_gle_for_change_amount(self, gl_entries):
		if cint(self.is_pos) and self.change_amount:
			billing_party_type, billing_party, billing_party_name = self.get_billing_party(with_name=True)

			if self.account_for_change_amount:
				gl_entries.append(
					self.get_gl_dict({
						"account": self.debit_to,
						"party_type": billing_party_type,
						"party": billing_party,
						"against": self.account_for_change_amount,
						"debit": flt(self.base_change_amount),
						"debit_in_account_currency": flt(self.base_change_amount) \
							if self.party_account_currency==self.company_currency else flt(self.change_amount),
						"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
						"against_voucher_type": self.doctype,
						"cost_center": self.cost_center,
						"project": self.project
					}, self.party_account_currency, item=self)
				)

				gl_entries.append(
					self.get_gl_dict({
						"account": self.account_for_change_amount,
						"against": billing_party_name or billing_party,
						"credit": self.base_change_amount,
						"cost_center": self.cost_center
					}, item=self)
				)
			else:
				frappe.throw(_("Select change amount account"), title="Mandatory Field")

	def make_write_off_gl_entry(self, gl_entries):
		# write off entries, applicable if only pos
		if self.write_off_account and flt(self.write_off_amount, self.precision("write_off_amount")):
			billing_party_type, billing_party, billing_party_name = self.get_billing_party(with_name=True)

			write_off_account_currency = get_account_currency(self.write_off_account)
			default_cost_center = frappe.get_cached_value('Company',  self.company,  'cost_center')

			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"party_type": billing_party_type,
					"party": billing_party,
					"against": self.write_off_account,
					"credit": flt(self.base_write_off_amount, self.precision("base_write_off_amount")),
					"credit_in_account_currency": (flt(self.base_write_off_amount,
						self.precision("base_write_off_amount")) if self.party_account_currency==self.company_currency
						else flt(self.write_off_amount, self.precision("write_off_amount"))),
					"against_voucher": self.return_against if cint(self.is_return) else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center,
					"project": self.project
				}, self.party_account_currency, item=self)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.write_off_account,
					"against": billing_party_name or billing_party,
					"debit": flt(self.base_write_off_amount, self.precision("base_write_off_amount")),
					"debit_in_account_currency": (flt(self.base_write_off_amount,
						self.precision("base_write_off_amount")) if write_off_account_currency==self.company_currency
						else flt(self.write_off_amount, self.precision("write_off_amount"))),
					"cost_center": self.cost_center or self.write_off_cost_center or default_cost_center
				}, write_off_account_currency, item=self)
			)

	def make_gle_for_rounding_adjustment(self, gl_entries):
		if flt(self.rounding_adjustment, self.precision("rounding_adjustment")) and self.base_rounding_adjustment:
			billing_party_type, billing_party, billing_party_name = self.get_billing_party(with_name=True)

			round_off_account, round_off_cost_center = \
				get_round_off_account_and_cost_center(self.company)
			round_off_account_currency = get_account_currency(round_off_account)

			gl_entries.append(
				self.get_gl_dict({
					"account": round_off_account,
					"against": billing_party_name or billing_party,
					"credit_in_account_currency": (flt(self.base_rounding_adjustment,
						self.precision('base_rounding_adjustment')) if round_off_account_currency == self.company_currency
						else flt(self.rounding_adjustment, self.precision("rounding_adjustment"))),
					"credit": flt(self.base_rounding_adjustment,
						self.precision("base_rounding_adjustment")),
					"cost_center": self.cost_center or round_off_cost_center,
				}, round_off_account_currency, item=self))

	def on_recurring(self, reference_doc, auto_repeat_doc):
		for fieldname in ("c_form_applicable", "c_form_no", "write_off_amount"):
			self.set(fieldname, reference_doc.get(fieldname))

		self.due_date = None

	def update_serial_no(self, in_cancel=False):
		""" update Sales Invoice refrence in Serial No """
		invoice = None if (in_cancel or self.is_return) else self.name
		if in_cancel and self.is_return:
			invoice = self.return_against

		for item in self.items:
			if not item.serial_no:
				continue

			for serial_no in item.serial_no.split("\n"):
				if serial_no and frappe.db.get_value('Serial No', serial_no, 'item_code') == item.item_code:
					frappe.db.set_value('Serial No', serial_no, 'sales_invoice', invoice)

			if item.vehicle and item.is_vehicle:
				frappe.db.set_value('Vehicle', item.vehicle, 'sales_invoice', invoice)

	def validate_serial_numbers(self):
		"""
			validate serial number agains Delivery Note and Sales Invoice
		"""
		self.set_serial_no_against_delivery_note()
		self.validate_serial_against_delivery_note()
		self.validate_serial_against_sales_invoice()

	def set_serial_no_against_delivery_note(self):
		for item in self.items:
			if item.serial_no and item.delivery_note and \
				item.qty != len(get_serial_nos(item.serial_no)):
				item.serial_no = get_delivery_note_serial_no(item.item_code, item.qty, item.delivery_note)

	def validate_serial_against_delivery_note(self):
		"""
			validate if the serial numbers in Sales Invoice Items are same as in
			Delivery Note Item
		"""

		for item in self.items:
			if not item.delivery_note or not item.delivery_note_item:
				continue

			serial_nos = frappe.db.get_value("Delivery Note Item", item.delivery_note_item, "serial_no") or ""
			dn_serial_nos = set(get_serial_nos(serial_nos))

			serial_nos = item.serial_no or ""
			si_serial_nos = set(get_serial_nos(serial_nos))

			if si_serial_nos - dn_serial_nos:
				frappe.throw(_("Serial Numbers in row {0} does not match with Delivery Note".format(item.idx)))

			if item.serial_no and cint(item.qty) != len(si_serial_nos):
				frappe.throw(_("Row {0}: {1} Serial numbers required for Item {2}. You have provided {3}.".format(
					item.idx, item.qty, item.item_code, len(si_serial_nos))))

	def validate_serial_against_sales_invoice(self):
		""" check if serial number is already used in other sales invoice """
		for item in self.items:
			if not item.serial_no:
				continue

			for serial_no in item.serial_no.split("\n"):
				serial_no_details = frappe.db.get_value("Serial No", serial_no,
					["sales_invoice", "item_code"], as_dict=1)

				if not serial_no_details:
					continue

				if serial_no_details.sales_invoice and serial_no_details.item_code == item.item_code \
					and self.name != serial_no_details.sales_invoice:
					sales_invoice_company = frappe.db.get_value("Sales Invoice", serial_no_details.sales_invoice, "company")
					if sales_invoice_company == self.company:
						frappe.throw(_("Serial Number: {0} is already referenced in Sales Invoice: {1}"
							.format(serial_no, serial_no_details.sales_invoice)))

	def verify_payment_amount_is_positive(self):
		for entry in self.payments:
			if entry.amount < 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be positive").format(entry.idx))

	def verify_payment_amount_is_negative(self):
		for entry in self.payments:
			if entry.amount > 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be negative").format(entry.idx))

	# collection of the loyalty points, create the ledger entry for that.
	def make_loyalty_point_entry(self):
		returned_amount = self.get_returned_amount()
		current_amount = flt(self.grand_total) - cint(self.loyalty_amount)
		eligible_amount = current_amount - returned_amount
		lp_details = get_loyalty_program_details_with_points(self.customer, company=self.company,
			current_transaction_amount=current_amount, loyalty_program=self.loyalty_program,
			expiry_date=self.posting_date, include_expired_entry=True)
		if lp_details and getdate(lp_details.from_date) <= getdate(self.posting_date) and \
			(not lp_details.to_date or getdate(lp_details.to_date) >= getdate(self.posting_date)):

			collection_factor = lp_details.collection_factor if lp_details.collection_factor else 1.0
			points_earned = cint(eligible_amount/collection_factor)

			doc = frappe.get_doc({
				"doctype": "Loyalty Point Entry",
				"company": self.company,
				"loyalty_program": lp_details.loyalty_program,
				"loyalty_program_tier": lp_details.tier_name,
				"customer": self.customer,
				"sales_invoice": self.name,
				"loyalty_points": points_earned,
				"purchase_amount": eligible_amount,
				"expiry_date": add_days(self.posting_date, lp_details.expiry_duration),
				"posting_date": self.posting_date
			})
			doc.flags.ignore_permissions = 1
			doc.save()
			self.set_loyalty_program_tier()

	# valdite the redemption and then delete the loyalty points earned on cancel of the invoice
	def delete_loyalty_point_entry(self):
		lp_entry = frappe.db.sql("select name from `tabLoyalty Point Entry` where sales_invoice=%s",
			(self.name), as_dict=1)

		if not lp_entry: return
		against_lp_entry = frappe.db.sql('''select name, sales_invoice from `tabLoyalty Point Entry`
			where redeem_against=%s''', (lp_entry[0].name), as_dict=1)
		if against_lp_entry:
			invoice_list = ", ".join([d.sales_invoice for d in against_lp_entry])
			frappe.throw(_('''Sales Invoice can't be cancelled since the Loyalty Points earned has been redeemed.
				First cancel the Sales Invoice No {0}''').format(invoice_list))
		else:
			frappe.db.sql('''delete from `tabLoyalty Point Entry` where sales_invoice=%s''', (self.name))
			# Set loyalty program
			self.set_loyalty_program_tier()

	def set_loyalty_program_tier(self):
		lp_details = get_loyalty_program_details_with_points(self.customer, company=self.company,
				loyalty_program=self.loyalty_program, include_expired_entry=True)
		frappe.db.set_value("Customer", self.customer, "loyalty_program_tier", lp_details.tier_name)

	def get_returned_amount(self):
		returned_amount = frappe.db.sql("""
			select sum(grand_total)
			from `tabSales Invoice`
			where docstatus=1 and is_return=1 and ifnull(return_against, '')=%s
		""", self.name)
		return abs(flt(returned_amount[0][0])) if returned_amount else 0

	# redeem the loyalty points.
	def apply_loyalty_points(self):
		from erpnext.accounts.doctype.loyalty_point_entry.loyalty_point_entry \
			import get_loyalty_point_entries, get_redemption_details
		loyalty_point_entries = get_loyalty_point_entries(self.customer, self.loyalty_program, self.company, self.posting_date)
		redemption_details = get_redemption_details(self.customer, self.loyalty_program, self.company)

		points_to_redeem = self.loyalty_points
		for lp_entry in loyalty_point_entries:
			if lp_entry.sales_invoice == self.name:
				continue
			available_points = lp_entry.loyalty_points - flt(redemption_details.get(lp_entry.name))
			if available_points > points_to_redeem:
				redeemed_points = points_to_redeem
			else:
				redeemed_points = available_points
			doc = frappe.get_doc({
				"doctype": "Loyalty Point Entry",
				"company": self.company,
				"loyalty_program": self.loyalty_program,
				"loyalty_program_tier": lp_entry.loyalty_program_tier,
				"customer": self.customer,
				"sales_invoice": self.name,
				"redeem_against": lp_entry.name,
				"loyalty_points": -1*redeemed_points,
				"purchase_amount": self.grand_total,
				"expiry_date": lp_entry.expiry_date,
				"posting_date": self.posting_date
			})
			doc.flags.ignore_permissions = 1
			doc.save()
			points_to_redeem -= redeemed_points
			if points_to_redeem < 1: # since points_to_redeem is integer
				break

	# Healthcare
	def set_healthcare_services(self, checked_values):
		self.set("items", [])
		from erpnext.stock.get_item_details import get_item_details
		for checked_item in checked_values:
			item_line = self.append("items", {})
			price_list, price_list_currency = frappe.db.get_values("Price List", {"selling": 1}, ['name', 'currency'])[0]
			args = {
				'doctype': "Sales Invoice",
				'item_code': checked_item['item'],
				'company': self.company,
				'customer': frappe.db.get_value("Patient", self.patient, "customer"),
				'selling_price_list': price_list,
				'price_list_currency': price_list_currency,
				'plc_conversion_rate': 1.0,
				'conversion_rate': 1.0
			}
			item_details = get_item_details(args)
			item_line.item_code = checked_item['item']
			item_line.qty = 1
			if checked_item['qty']:
				item_line.qty = checked_item['qty']
			if checked_item['rate']:
				item_line.rate = checked_item['rate']
			else:
				item_line.rate = item_details.price_list_rate
			item_line.amount = float(item_line.rate) * float(item_line.qty)
			if checked_item['income_account']:
				item_line.income_account = checked_item['income_account']
			if checked_item['dt']:
				item_line.reference_dt = checked_item['dt']
			if checked_item['dn']:
				item_line.reference_dn = checked_item['dn']
			if checked_item['description']:
				item_line.description = checked_item['description']

		self.set_missing_values(for_validate = True)

	def validate_vehicle_registration_order(self):
		if self.get('vehicle_registration_order'):
			vro = frappe.db.get_value("Vehicle Registration Order", self.vehicle_registration_order,
				['docstatus', 'use_sales_invoice', 'customer', 'customer_account'], as_dict=1)

			if not vro:
				frappe.throw(_("Vehicle Registration Order {0} does not exist")
					.format(self.vehicle_registration_order))

			if vro.docstatus != 1:
				frappe.throw(_("{0} is not submitted")
					.format(frappe.get_desk_link("Vehicle Registration Order", self.vehicle_registration_order)))

			if not cint(vro.use_sales_invoice):
				frappe.throw(_("Sales Invoice not required in {0}")
					.format(frappe.get_desk_link("Vehicle Registration Order", self.vehicle_registration_order)))

			billing_customer = self.get('bill_to') or self.get('customer')
			if not billing_customer or billing_customer != vro.customer:
				frappe.throw(_("Billing Customer does not match with {0}")
					.format(frappe.get_desk_link("Vehicle Registration Order", self.vehicle_registration_order)))

			if not self.debit_to or self.debit_to != vro.customer_account:
				frappe.throw(_("Customer Account {0} does not match with {1}")
					.format(self.debit_to, frappe.get_desk_link("Vehicle Registration Order", self.vehicle_registration_order)))

	def update_vehicle_registration_order(self):
		if self.get('vehicle_registration_order'):
			vro = frappe.get_doc("Vehicle Registration Order", self.vehicle_registration_order)
			vro.set_payment_status(update=True)
			vro.set_status(update=True)
			vro.notify_update()

	def set_rate_zero_for_claim_item(self, source_row, target_row):
		bill_to = self.get('bill_to') or self.get('customer')
		if bill_to and source_row.get('claim_customer') and bill_to != source_row.claim_customer:
			target_row.price_list_rate = 0
			target_row.rate = 0
			target_row.margin_rate_or_amount = 0
			target_row.discount_percentage = 0

	def set_can_make_vehicle_gate_pass(self):
		if 'Vehicles' not in frappe.get_active_domains():
			return

		if self.get('project') and self.get('applies_to_vehicle') and self.docstatus == 1:
			project_vehicle_status = frappe.db.get_value("Project", self.project, 'vehicle_status')
			gate_pass_exists = frappe.db.get_value("Vehicle Gate Pass", {'sales_invoice': self.name, 'docstatus': 1})
			self.set_onload('can_make_vehicle_gate_pass', project_vehicle_status == "In Workshop" and not gate_pass_exists)


def get_discounting_status(sales_invoice):
	status = None

	invoice_discounting_list = frappe.db.sql("""
		select status
		from `tabInvoice Discounting` id, `tabDiscounted Invoice` d
		where
			id.name = d.parent
			and d.sales_invoice=%s
			and id.docstatus=1
			and status in ('Disbursed', 'Settled')
	""", sales_invoice)

	for d in invoice_discounting_list:
		status = d[0]
		if status == "Disbursed":
			break

	return status


def validate_inter_company_party(doctype, party, company, inter_company_reference):
	if not party:
		return

	ref_doctype = get_intercompany_ref_doctype(doctype)

	if doctype in ["Sales Invoice", "Delivery Note", "Sales Order"]:
		partytype, ref_partytype, internal = "Customer", "Supplier", "is_internal_customer"
	else:
		partytype, ref_partytype, internal = "Supplier", "Customer", "is_internal_supplier"

	if inter_company_reference:
		doc = frappe.get_doc(ref_doctype, inter_company_reference)
		ref_party = doc.supplier if doctype in ["Sales Invoice", "Sales Order"] else doc.customer
		if not frappe.db.get_value(partytype, {"represents_company": doc.company}, "name") == party:
			frappe.throw(_("Invalid {0} for Inter Company Transaction.").format(partytype))
		if not frappe.get_cached_value(ref_partytype, ref_party, "represents_company") == company:
			frappe.throw(_("Invalid Company for Inter Company Transaction."))

	elif frappe.db.get_value(partytype, {"name": party, internal: 1}, "name") == party:
		companies = frappe.get_all("Allowed To Transact With", fields=["company"], filters={"parenttype": partytype, "parent": party})
		companies = [d.company for d in companies]
		if not company in companies:
			frappe.throw(_("{0} not allowed to transact with {1}. Please change the Company.").format(partytype, company))


def update_linked_doc(doctype, name, inter_company_reference):
	ref_doctype = get_intercompany_ref_doctype(doctype)
	if inter_company_reference:
		frappe.db.set_value(ref_doctype, inter_company_reference, "inter_company_reference", name, notify=1)


def unlink_inter_company_doc(doctype, name, inter_company_reference):
	ref_doctype = get_intercompany_ref_doctype(doctype)
	if inter_company_reference:
		frappe.db.set_value(doctype, name, "inter_company_reference", "")
		frappe.db.set_value(ref_doctype, inter_company_reference, "inter_company_reference", "", notify=1)


def get_intercompany_ref_doctype(doctype):
	ref_doc_map = {
		"Sales Invoice": "Purchase Invoice",
		"Sales Order": "Purchase Order",
		"Delivery Note": "Purchase Receipt",
	}
	for source, target in ref_doc_map.copy().items():
		ref_doc_map[target] = source

	ref_doc = ref_doc_map.get(doctype)
	if not ref_doc:
		frappe.throw(_("Inter Company Transaction for {0} not allowed").format(doctype))

	return ref_doc


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Invoices'),
	})
	return list_context


@frappe.whitelist()
def get_bank_cash_account(mode_of_payment, company):
	account = frappe.db.get_value("Mode of Payment Account",
		{"parent": mode_of_payment, "company": company}, "default_account")
	if not account:
		frappe.throw(_("Please set default Cash or Bank account in Mode of Payment {0}")
			.format(mode_of_payment))
	return {
		"account": account
	}


@frappe.whitelist()
def make_maintenance_schedule(source_name, target_doc=None):
	doclist = get_mapped_doc("Sales Invoice", source_name, 	{
		"Sales Invoice": {
			"doctype": "Maintenance Schedule",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Invoice Item": {
			"doctype": "Maintenance Schedule Item",
		},
	}, target_doc)

	return doclist


@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	def get_pending_qty(source):
		return flt(source.qty) - flt(source.delivered_qty)

	def item_condition(source, source_parent, target_parent):
		if source.name in [d.sales_invoice_item for d in target_parent.get('items') if d.sales_invoice_item]:
			return False

		if source.delivered_by_supplier:
			return False

		return get_pending_qty(source)

	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent, target_parent):
		target.qty = get_pending_qty(source)

	doclist = get_mapped_doc("Sales Invoice", source_name, 	{
		"Sales Invoice": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			},
			"field_map": {
				"remarks": "remarks",
			}
		},
		"Sales Invoice Item": {
			"doctype": "Delivery Note Item",
			"field_map": {
				"name": "sales_invoice_item",
				"parent": "sales_invoice",
				"serial_no": "serial_no",
				"vehicle": "vehicle",
				"sales_order": "sales_order",
				"sales_order_item": "sales_order_item",
				"quotation": "quotation",
				"quotation_item": "quotation_item",
				"cost_center": "cost_center"
			},
			"postprocess": update_item,
			"condition": item_condition,
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"field_map": {
				"incentives": "incentives"
			},
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doclist


@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc
	return make_return_doc("Sales Invoice", source_name, target_doc)


def set_account_for_mode_of_payment(self):
	for data in self.payments:
		if not data.account:
			data.account = get_bank_cash_account(data.mode_of_payment, self.company).get("account")


def get_inter_company_details(doc, doctype):
	if doctype in ["Sales Invoice", "Delivery Note", "Sales Order"]:
		party = frappe.db.get_value("Supplier", {"disabled": 0, "is_internal_supplier": 1, "represents_company": doc.company}, "name")
		company = frappe.get_cached_value("Customer", doc.customer, "represents_company")
	else:
		party = frappe.db.get_value("Customer", {"disabled": 0, "is_internal_customer": 1, "represents_company": doc.company}, "name")
		company = frappe.get_cached_value("Supplier", doc.supplier, "represents_company")

	return {
		"party": party,
		"company": company
	}


def get_internal_party(parties, link_doctype, doc):
	if len(parties) == 1:
		party = parties[0].name
	else:
		# If more than one Internal Supplier/Customer, get supplier/customer on basis of address
		if doc.get('company_address') or doc.get('shipping_address'):
			party = frappe.db.get_value("Dynamic Link", {"parent": doc.get('company_address') or doc.get('shipping_address'),
			"parenttype": "Address", "link_doctype": link_doctype}, "link_name")

			if not party:
				party = parties[0].name
		else:
			party = parties[0].name

	return party


def validate_inter_company_transaction(doc, doctype):
	details = get_inter_company_details(doc, doctype)
	price_list = doc.selling_price_list if doctype in ["Sales Invoice", "Delivery Note", "Sales Order"] else doc.buying_price_list
	valid_price_list = frappe.db.get_value("Price List", {"name": price_list, "buying": 1, "selling": 1})
	if not valid_price_list:
		frappe.throw(_("Selected Price List should have buying and selling fields checked."))

	party = details.get("party")
	if not party:
		partytype = "Supplier" if doctype in ["Sales Invoice", "Delivery Note", "Sales Order"] else "Customer"
		frappe.throw(_("No {0} found for Inter Company Transactions.").format(partytype))

	company = details.get("company")
	default_currency = frappe.get_cached_value('Company', company, "default_currency")
	if default_currency != doc.currency:
		frappe.throw(_("Company currencies of both the companies should match for Inter Company Transactions."))

	return


@frappe.whitelist()
def make_inter_company_purchase_invoice(source_name, target_doc=None):
	return make_inter_company_transaction("Sales Invoice", source_name, target_doc)


def make_inter_company_transaction(doctype, source_name, target_doc=None):
	source_doc = frappe.get_doc(doctype, source_name)
	target_doctype = get_intercompany_ref_doctype(doctype)

	validate_inter_company_transaction(source_doc, doctype)
	details = get_inter_company_details(source_doc, doctype)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_items(source_doc, target_doc, source_parent, target_parent):
		if target_parent.doctype in ["Purchase Receipt", "Purchase Invoice"]:
			target_doc.received_qty = target_doc.qty

	def update_details(source_doc, target_doc, source_parent, target_parent):
		target_doc.inter_company_reference = source_doc.name
		if target_doc.doctype in ["Purchase Invoice", "Purchase Receipt", "Purchase Order"]:
			target_doc.company = details.get("company")
			target_doc.supplier = details.get("party")
			target_doc.buying_price_list = source_doc.selling_price_list
		else:
			target_doc.company = details.get("company")
			target_doc.customer = details.get("party")
			target_doc.selling_price_list = source_doc.buying_price_list

	doclist = get_mapped_doc(doctype, source_name,	{
		doctype: {
			"doctype": target_doctype,
			"postprocess": update_details,
			"field_no_map": [
				"taxes_and_charges",
				"cost_center",
				"set_warehouse",
				"transaction_type",
				"address_display",
				"shipping_address",
			]
		},
		doctype + " Item": {
			"doctype": target_doctype + " Item",
			"postprocess": update_items,
			"field_no_map": [
				"income_account",
				"expense_account",
				"cost_center",
				"warehouse"
			]
		}

	}, target_doc, set_missing_values)

	return doclist


@frappe.whitelist()
def get_loyalty_programs(customer):
	''' sets applicable loyalty program to the customer or returns a list of applicable programs '''
	from erpnext.selling.doctype.customer.customer import get_loyalty_programs

	customer = frappe.get_doc('Customer', customer)
	if customer.loyalty_program: return

	lp_details = get_loyalty_programs(customer)

	if len(lp_details) == 1:
		frappe.db.set(customer, 'loyalty_program', lp_details[0])
		return []
	else:
		return lp_details


def on_doctype_update():
	frappe.db.add_index("Sales Invoice", ["customer", "is_return", "return_against"])


@frappe.whitelist()
def create_invoice_discounting(source_name, target_doc=None):
	invoice = frappe.get_doc("Sales Invoice", source_name)
	invoice_discounting = frappe.new_doc("Invoice Discounting")
	invoice_discounting.company = invoice.company
	invoice_discounting.append("invoices", {
		"sales_invoice": source_name,
		"customer": invoice.customer,
		"posting_date": invoice.posting_date,
		"outstanding_amount": invoice.outstanding_amount
	})

	return invoice_discounting


def get_all_sales_invoice_receivable_accounts(sales_invoice):
	party_accounts = []

	invoice_account = frappe.db.get_value("Sales Invoice", sales_invoice, "debit_to")
	if invoice_account:
		party_accounts.append(invoice_account)

	all_invoice_discounting = frappe.db.sql("""
		select par.accounts_receivable_discounted, par.accounts_receivable_unpaid, par.accounts_receivable_credit
		from `tabInvoice Discounting` par
		where par.docstatus=1 and exists(
			select ch.name from `tabDiscounted Invoice` ch where par.name=ch.parent and ch.sales_invoice = %s
		)
	""", sales_invoice, as_dict=1)

	for d in all_invoice_discounting:
		if d.accounts_receivable_discounted:
			party_accounts.append(d.accounts_receivable_discounted)
		if d.accounts_receivable_unpaid:
			party_accounts.append(d.accounts_receivable_unpaid)
		if d.accounts_receivable_credit:
			party_accounts.append(d.accounts_receivable_credit)

	return list(set(party_accounts))
