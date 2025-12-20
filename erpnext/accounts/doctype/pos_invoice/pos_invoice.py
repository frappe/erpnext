# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe import _, bold
from frappe.model.mapper import map_child_doc, map_doc
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import cint, flt, get_link_to_form, getdate, nowdate
from frappe.utils.nestedset import get_descendants_of

from erpnext.accounts.doctype.loyalty_program.loyalty_program import validate_loyalty_points
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	SalesInvoice,
	get_mode_of_payment_info,
	update_multi_mode_option,
)
from erpnext.accounts.party import get_due_date, get_party_account
from erpnext.controllers.queries import item_query as _item_query
from erpnext.controllers.sales_and_purchase_return import get_sales_invoice_item_from_consolidated_invoice
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.stock_ledger import is_negative_stock_allowed


class ProductBundleStockValidationError(frappe.ValidationError):
	pass


class POSInvoice(SalesInvoice):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.item_wise_tax_detail.item_wise_tax_detail import ItemWiseTaxDetail
		from erpnext.accounts.doctype.payment_schedule.payment_schedule import PaymentSchedule
		from erpnext.accounts.doctype.pos_invoice_item.pos_invoice_item import POSInvoiceItem
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.sales_invoice_advance.sales_invoice_advance import SalesInvoiceAdvance
		from erpnext.accounts.doctype.sales_invoice_payment.sales_invoice_payment import SalesInvoicePayment
		from erpnext.accounts.doctype.sales_invoice_timesheet.sales_invoice_timesheet import (
			SalesInvoiceTimesheet,
		)
		from erpnext.accounts.doctype.sales_taxes_and_charges.sales_taxes_and_charges import (
			SalesTaxesandCharges,
		)
		from erpnext.selling.doctype.sales_team.sales_team import SalesTeam
		from erpnext.stock.doctype.packed_item.packed_item import PackedItem

		account_for_change_amount: DF.Link | None
		additional_discount_percentage: DF.Float
		address_display: DF.TextEditor | None
		advances: DF.Table[SalesInvoiceAdvance]
		against_income_account: DF.SmallText | None
		allocate_advances_automatically: DF.Check
		amended_from: DF.Link | None
		amount_eligible_for_commission: DF.Currency
		apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
		auto_repeat: DF.Link | None
		base_change_amount: DF.Currency
		base_discount_amount: DF.Currency
		base_grand_total: DF.Currency
		base_in_words: DF.Data | None
		base_net_total: DF.Currency
		base_paid_amount: DF.Currency
		base_rounded_total: DF.Currency
		base_rounding_adjustment: DF.Currency
		base_total: DF.Currency
		base_total_taxes_and_charges: DF.Currency
		base_write_off_amount: DF.Currency
		cash_bank_account: DF.Link | None
		change_amount: DF.Currency
		commission_rate: DF.Float
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.TextEditor | None
		company_contact_person: DF.Link | None
		consolidated_invoice: DF.Link | None
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.Data | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		coupon_code: DF.Link | None
		currency: DF.Link
		customer: DF.Link | None
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		debit_to: DF.Link
		discount_amount: DF.Currency
		due_date: DF.Date | None
		from_date: DF.Date | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		inter_company_invoice_reference: DF.Link | None
		is_discounted: DF.Check
		is_opening: DF.Literal["No", "Yes"]
		is_pos: DF.Check
		is_return: DF.Check
		item_wise_tax_details: DF.Table[ItemWiseTaxDetail]
		items: DF.Table[POSInvoiceItem]
		language: DF.Data | None
		letter_head: DF.Link | None
		loyalty_amount: DF.Currency
		loyalty_points: DF.Int
		loyalty_program: DF.Link | None
		loyalty_redemption_account: DF.Link | None
		loyalty_redemption_cost_center: DF.Link | None
		naming_series: DF.Literal["ACC-PSINV-.YYYY.-"]
		net_total: DF.Currency
		other_charges_calculation: DF.TextEditor | None
		outstanding_amount: DF.Currency
		packed_items: DF.Table[PackedItem]
		paid_amount: DF.Currency
		party_account_currency: DF.Link | None
		payment_schedule: DF.Table[PaymentSchedule]
		payment_terms_template: DF.Link | None
		payments: DF.Table[SalesInvoicePayment]
		plc_conversion_rate: DF.Float
		po_date: DF.Date | None
		po_no: DF.Data | None
		pos_profile: DF.Link | None
		posting_date: DF.Date
		posting_time: DF.Time | None
		price_list_currency: DF.Link
		pricing_rules: DF.Table[PricingRuleDetail]
		project: DF.Link | None
		redeem_loyalty_points: DF.Check
		remarks: DF.SmallText | None
		return_against: DF.Link | None
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		sales_partner: DF.Link | None
		sales_team: DF.Table[SalesTeam]
		scan_barcode: DF.Data | None
		select_print_heading: DF.Link | None
		selling_price_list: DF.Link
		set_posting_time: DF.Check
		set_warehouse: DF.Link | None
		shipping_address: DF.TextEditor | None
		shipping_address_name: DF.Link | None
		shipping_rule: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"Return",
			"Credit Note Issued",
			"Consolidated",
			"Submitted",
			"Paid",
			"Partly Paid",
			"Unpaid",
			"Partly Paid and Discounted",
			"Unpaid and Discounted",
			"Overdue and Discounted",
			"Overdue",
			"Cancelled",
		]
		tax_category: DF.Link | None
		tax_id: DF.Data | None
		taxes: DF.Table[SalesTaxesandCharges]
		taxes_and_charges: DF.Link | None
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		territory: DF.Link | None
		timesheets: DF.Table[SalesInvoiceTimesheet]
		to_date: DF.Date | None
		total: DF.Currency
		total_advance: DF.Currency
		total_billing_amount: DF.Currency
		total_commission: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		update_billed_amount_in_delivery_note: DF.Check
		update_billed_amount_in_sales_order: DF.Check
		update_stock: DF.Check
		utm_campaign: DF.Link | None
		utm_medium: DF.Link | None
		utm_source: DF.Link | None
		write_off_account: DF.Link | None
		write_off_amount: DF.Currency
		write_off_cost_center: DF.Link | None
		write_off_outstanding_amount_automatically: DF.Check
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def validate(self):
		if not self.customer:
			frappe.throw(_("Please select Customer first"))

		if not cint(self.is_pos):
			frappe.throw(
				_("POS Invoice should have the field {0} checked.").format(frappe.bold(_("Include Payment")))
			)

		# run on validate method of selling controller
		super(SalesInvoice, self).validate()
		self.validate_pos_opening_entry()
		self.validate_is_pos_using_sales_invoice()
		self.validate_auto_set_posting_time()
		self.validate_mode_of_payment()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_debit_to_acc()
		self.validate_write_off_account()
		self.validate_change_amount()
		self.validate_change_account()
		self.validate_item_cost_centers()
		self.validate_warehouse()
		self.validate_serialised_or_batched_item()
		self.validate_stock_availablility()
		self.validate_return_items_qty()
		self.set_status()
		self.validate_pos()
		self.validate_payment_amount()
		self.validate_loyalty_transaction()
		self.validate_company_with_pos_company()
		self.validate_full_payment()
		self.update_packing_list()
		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code

			validate_coupon_code(self.coupon_code)

	def before_submit(self):
		self.set_outstanding_amount()

	def on_submit(self):
		# create the loyalty point ledger entry if the customer is enrolled in any loyalty program
		if not self.is_return and self.loyalty_program:
			self.make_loyalty_point_entry()
		elif self.is_return and self.return_against and self.loyalty_program:
			against_psi_doc = frappe.get_doc("POS Invoice", self.return_against)
			against_psi_doc.delete_loyalty_point_entry()
			against_psi_doc.make_loyalty_point_entry()
		if self.redeem_loyalty_points and self.loyalty_points:
			self.apply_loyalty_points()
		self.check_phone_payments()
		self.set_status(update=True)
		self.make_bundle_for_sales_purchase_return()
		for table_name in ["items", "packed_items"]:
			self.make_bundle_using_old_serial_batch_fields(table_name)
			self.submit_serial_batch_bundle(table_name)

		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

			update_coupon_code_count(self.coupon_code, "used")
		self.clear_unallocated_mode_of_payments()

		if self.is_return and self.invoice_type_in_pos == "Sales Invoice":
			self.create_and_add_consolidated_sales_invoice()

	def before_cancel(self):
		if (
			self.consolidated_invoice
			and frappe.db.get_value("Sales Invoice", self.consolidated_invoice, "docstatus") == 1
		):
			pos_closing_entry = frappe.get_all(
				"POS Invoice Reference",
				ignore_permissions=True,
				filters={"pos_invoice": self.name},
				pluck="parent",
				limit=1,
			)
			frappe.throw(
				_("You need to cancel POS Closing Entry {} to be able to cancel this document.").format(
					get_link_to_form("POS Closing Entry", pos_closing_entry[0])
				),
				title=_("Not Allowed"),
			)

	def on_cancel(self):
		self.ignore_linked_doctypes = ["Payment Ledger Entry", "Serial and Batch Bundle"]
		# run on cancel method of selling controller
		super(SalesInvoice, self).on_cancel()
		if not self.is_return and self.loyalty_program:
			self.delete_loyalty_point_entry()
		elif self.is_return and self.return_against and self.loyalty_program:
			against_psi_doc = frappe.get_doc("POS Invoice", self.return_against)
			against_psi_doc.delete_loyalty_point_entry()
			against_psi_doc.make_loyalty_point_entry()

		self.db_set("status", "Cancelled")

		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

			update_coupon_code_count(self.coupon_code, "cancelled")

		self.delink_serial_and_batch_bundle()

	def clear_unallocated_mode_of_payments(self):
		self.set("payments", self.get("payments", {"amount": ["not in", [0, None, ""]]}))

		sip = frappe.qb.DocType("Sales Invoice Payment")
		frappe.qb.from_(sip).delete().where(sip.parent == self.name).where(sip.amount == 0).run()

	def create_and_add_consolidated_sales_invoice(self):
		sales_inv = self.create_return_sales_invoice()
		self.db_set("consolidated_invoice", sales_inv.name)
		self.set_status(update=True)

	def create_return_sales_invoice(self):
		return_sales_invoice = frappe.new_doc("Sales Invoice")
		return_sales_invoice.is_pos = 1
		return_sales_invoice.is_return = 1
		map_doc(self, return_sales_invoice, table_map={"doctype": return_sales_invoice.doctype})
		return_sales_invoice.is_created_using_pos = 1
		return_sales_invoice.is_consolidated = 1
		return_sales_invoice.return_against = frappe.db.get_value(
			"POS Invoice", self.return_against, "consolidated_invoice"
		)
		items, taxes, payments = [], [], []
		for d in self.items:
			si_item = map_child_doc(d, return_sales_invoice, {"doctype": "Sales Invoice Item"})
			si_item.pos_invoice = self.name
			si_item.pos_invoice_item = d.name
			si_item.sales_invoice_item = get_sales_invoice_item_from_consolidated_invoice(
				self.return_against, d.pos_invoice_item
			)
			items.append(si_item)

		for d in self.get("taxes"):
			tax = map_child_doc(d, return_sales_invoice, {"doctype": "Sales Taxes and Charges"})
			taxes.append(tax)

		for d in self.get("payments"):
			payment = map_child_doc(d, return_sales_invoice, {"doctype": "Sales Invoice Payment"})
			payments.append(payment)

		return_sales_invoice.set("items", items)
		return_sales_invoice.set("taxes", taxes)
		return_sales_invoice.set("payments", payments)
		return_sales_invoice.save()
		return_sales_invoice.submit()

		return return_sales_invoice

	def delink_serial_and_batch_bundle(self):
		for row in self.items:
			if row.serial_and_batch_bundle:
				if not self.consolidated_invoice:
					frappe.db.set_value(
						"Serial and Batch Bundle",
						row.serial_and_batch_bundle,
						{"is_cancelled": 1, "voucher_no": ""},
					)

				frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle).cancel()
				row.db_set("serial_and_batch_bundle", None)

	def submit_serial_batch_bundle(self, table_name):
		for item in self.get(table_name):
			if item.serial_and_batch_bundle:
				doc = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)

				if doc.docstatus == 0:
					doc.flags.ignore_voucher_validation = True
					doc.submit()

	def check_phone_payments(self):
		for pay in self.payments:
			if pay.type == "Phone" and pay.amount >= 0:
				paid_amt = frappe.db.get_value(
					"Payment Request",
					filters=dict(
						reference_doctype="POS Invoice",
						reference_name=self.name,
						mode_of_payment=pay.mode_of_payment,
						status="Paid",
					),
					fieldname="grand_total",
				)

				if paid_amt and pay.amount != paid_amt:
					return frappe.throw(
						_("Payment related to {0} is not completed").format(pay.mode_of_payment)
					)

	def validate_stock_availablility(self):
		if self.is_return:
			return

		if self.docstatus.is_draft() and not frappe.db.get_value(
			"POS Profile", self.pos_profile, "validate_stock_on_save"
		):
			return

		for d in self.get("items"):
			if not d.serial_and_batch_bundle:
				if frappe.db.exists("Product Bundle", d.item_code):
					(
						availability,
						is_stock_item,
						is_negative_stock_allowed,
					) = get_product_bundle_stock_availability(d.item_code, d.warehouse, d.stock_qty)

				else:
					availability, is_stock_item, is_negative_stock_allowed = get_stock_availability(
						d.item_code, d.warehouse
					)

				if is_negative_stock_allowed:
					continue

				if isinstance(availability, list):
					error_msgs = []
					for item in availability:
						if flt(item["available"]) < flt(item["required"]):
							error_msgs.append(
								_("<li>Packed Item {0}: Required {1}, Available {2}</li>").format(
									frappe.bold(item["item_code"]),
									frappe.bold(flt(item["required"], 2)),
									frappe.bold(flt(item["available"], 2)),
								)
							)

					if error_msgs:
						frappe.throw(
							_(
								"<b>Row #{0}:</b> Bundle {1} in warehouse {2} has insufficient packed items:<br><div style='margin-top: 15px;'><ul style='line-height: 0.8;'>{3}</ul></div>"
							).format(
								d.idx,
								frappe.bold(d.item_code),
								frappe.bold(d.warehouse),
								"<br>".join(error_msgs),
							),
							title=_("Insufficient Stock for Product Bundle Items"),
							exc=ProductBundleStockValidationError,
						)

				else:
					item_code, warehouse = frappe.bold(d.item_code), frappe.bold(d.warehouse)
					if is_stock_item and flt(availability) <= 0:
						frappe.throw(
							_("Row #{0}: Item {1} has no stock in warehouse {2}.").format(
								d.idx, item_code, warehouse
							),
							title=_("Item Out of Stock"),
						)
					elif is_stock_item and flt(availability) < flt(d.stock_qty):
						frappe.throw(
							_("Row #{0}: Item {1} in warehouse {2}: Available {3}, Needed {4}.").format(
								d.idx,
								item_code,
								warehouse,
								frappe.bold(flt(availability, 2)),
								frappe.bold(flt(d.stock_qty, 2)),
							),
							title=_("Insufficient Stock"),
						)

	def validate_is_pos_using_sales_invoice(self):
		self.invoice_type_in_pos = frappe.db.get_single_value("POS Settings", "invoice_type")
		if self.invoice_type_in_pos == "Sales Invoice" and not self.is_return:
			frappe.throw(_("Sales Invoice mode is activated in POS. Please create Sales Invoice instead."))

	def validate_serialised_or_batched_item(self):
		error_msg = []
		for d in self.get("items"):
			error_msg = ""
			if d.get("has_serial_no") and (
				(not d.use_serial_batch_fields and not d.serial_and_batch_bundle)
				or (d.use_serial_batch_fields and not d.serial_no)
			):
				error_msg = f"Row #{d.idx}: Please select Serial No. for item {bold(d.item_code)}"

			elif d.get("has_batch_no") and (
				(not d.use_serial_batch_fields and not d.serial_and_batch_bundle)
				or (d.use_serial_batch_fields and not d.batch_no)
			):
				error_msg = f"Row #{d.idx}: Please select Batch No. for item {bold(d.item_code)}"

		if error_msg:
			frappe.throw(error_msg, title=_("Serial / Batch Bundle Missing"), as_list=True)

	def validate_return_items_qty(self):
		if not self.get("is_return"):
			return

		for d in self.get("items"):
			if d.get("qty") > 0:
				frappe.throw(
					_(
						"Row #{}: You cannot add positive quantities in a return invoice. Please remove item {} to complete the return."
					).format(d.idx, frappe.bold(d.item_code)),
					title=_("Invalid Item"),
				)
			if d.get("serial_no"):
				serial_nos = get_serial_nos(d.serial_no)
				for sr in serial_nos:
					serial_no_exists = frappe.db.sql(
						"""
						SELECT name
						FROM `tabPOS Invoice Item`
						WHERE
							parent = %s
							and (serial_no = %s
								or serial_no like %s
								or serial_no like %s
								or serial_no like %s
							)
					""",
						(self.return_against, sr, sr + "\n%", "%\n" + sr, "%\n" + sr + "\n%"),
					)

					if not serial_no_exists:
						bold_return_against = frappe.bold(self.return_against)
						bold_serial_no = frappe.bold(sr)
						frappe.throw(
							_(
								"Row #{}: Serial No {} cannot be returned since it was not transacted in original invoice {}"
							).format(d.idx, bold_serial_no, bold_return_against)
						)

	def validate_mode_of_payment(self):
		if len(self.payments) == 0:
			frappe.throw(_("At least one mode of payment is required for POS invoice."))

	def validate_change_account(self):
		if (
			self.change_amount
			and self.account_for_change_amount
			and frappe.get_cached_value("Account", self.account_for_change_amount, "company") != self.company
		):
			frappe.throw(
				_("The selected change account {} doesn't belongs to Company {}.").format(
					self.account_for_change_amount, self.company
				)
			)

	def validate_change_amount(self):
		grand_total = flt(self.rounded_total) or flt(self.grand_total)
		base_grand_total = flt(self.base_rounded_total) or flt(self.base_grand_total)
		if not flt(self.change_amount) and grand_total < flt(self.paid_amount):
			self.change_amount = flt(self.paid_amount - grand_total + flt(self.write_off_amount))
			self.base_change_amount = (
				flt(self.base_paid_amount) - base_grand_total + flt(self.base_write_off_amount)
			)

		if flt(self.change_amount) and not self.account_for_change_amount:
			frappe.msgprint(_("Please enter Account for Change Amount"), raise_exception=1)

	def validate_payment_amount(self):
		total_amount_in_payments = 0
		for entry in self.payments:
			total_amount_in_payments += entry.amount
			if not self.is_return and entry.amount < 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be positive").format(entry.idx))
			if self.is_return and entry.amount > 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be negative").format(entry.idx))

		if self.is_return and self.docstatus != 0:
			invoice_total = self.rounded_total or self.grand_total
			total_amount_in_payments = flt(total_amount_in_payments, self.precision("grand_total"))
			if total_amount_in_payments and total_amount_in_payments < invoice_total:
				frappe.throw(_("Total payments amount can't be greater than {}").format(-invoice_total))

	def validate_company_with_pos_company(self):
		if self.company != frappe.db.get_value("POS Profile", self.pos_profile, "company"):
			frappe.throw(
				_("Company {} does not match with POS Profile Company {}").format(
					self.company, frappe.db.get_value("POS Profile", self.pos_profile, "company")
				)
			)

	def set_outstanding_amount(self):
		total = flt(self.rounded_total) or flt(self.grand_total)
		self.outstanding_amount = total - flt(self.paid_amount) if total > flt(self.paid_amount) else 0

	def validate_loyalty_transaction(self):
		if self.redeem_loyalty_points and (
			not self.loyalty_redemption_account or not self.loyalty_redemption_cost_center
		):
			expense_account, cost_center = frappe.db.get_value(
				"Loyalty Program", self.loyalty_program, ["expense_account", "cost_center"]
			)
			if not self.loyalty_redemption_account:
				self.loyalty_redemption_account = expense_account
			if not self.loyalty_redemption_cost_center:
				self.loyalty_redemption_cost_center = cost_center

		if self.redeem_loyalty_points and self.loyalty_program and self.loyalty_points:
			validate_loyalty_points(self, self.loyalty_points)

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get("amended_from"):
				self.status = "Draft"
			return

		total = flt(self.rounded_total) or flt(self.grand_total)

		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if self.consolidated_invoice:
					self.status = "Consolidated"
				elif (
					flt(self.outstanding_amount) > 0
					and getdate(self.due_date) < getdate(nowdate())
					and self.is_discounted
					and self.get_discounting_status() == "Disbursed"
				):
					self.status = "Overdue and Discounted"
				elif flt(self.outstanding_amount) > 0 and getdate(self.due_date) < getdate(nowdate()):
					self.status = "Overdue"
				elif (
					0 < flt(self.outstanding_amount) < total
					and self.is_discounted
					and self.get_discounting_status() == "Disbursed"
				):
					self.status = "Partly Paid and Discounted"
				elif 0 < flt(self.outstanding_amount) < total:
					self.status = "Partly Paid"
				elif (
					flt(self.outstanding_amount) > 0
					and getdate(self.due_date) >= getdate(nowdate())
					and self.is_discounted
					and self.get_discounting_status() == "Disbursed"
				):
					self.status = "Unpaid and Discounted"
				elif flt(self.outstanding_amount) > 0 and getdate(self.due_date) >= getdate(nowdate()):
					self.status = "Unpaid"
				elif (
					flt(self.outstanding_amount) <= 0
					and self.is_return == 0
					and frappe.db.get_value(
						"POS Invoice", {"is_return": 1, "return_against": self.name, "docstatus": 1}
					)
				):
					self.status = "Credit Note Issued"
				elif self.is_return == 1:
					self.status = "Return"
				elif flt(self.outstanding_amount) <= 0:
					self.status = "Paid"
				else:
					self.status = "Submitted"
			else:
				self.status = "Draft"

		if update:
			self.db_set("status", self.status, update_modified=update_modified)

	def set_pos_fields(self, for_validate=False):
		"""Set retail related fields from POS Profiles"""
		from erpnext.stock.get_item_details import (
			ItemDetailsCtx,
			get_pos_profile,
			get_pos_profile_item_details_,
		)

		if not self.pos_profile:
			pos_profile = get_pos_profile(self.company) or {}
			if not pos_profile:
				frappe.throw(_("No POS Profile found. Please create a New POS Profile first"))
			self.pos_profile = pos_profile.get("name")

		profile = {}
		if self.pos_profile:
			profile = frappe.get_doc("POS Profile", self.pos_profile)
			self.company = profile.get("company")

		if not self.get("payments") and not for_validate:
			update_multi_mode_option(self, profile)

		if self.is_return and not for_validate:
			add_return_modes(self, profile)

		if profile:
			if not for_validate and not self.customer:
				self.customer = profile.customer

			self.account_for_change_amount = (
				profile.get("account_for_change_amount") or self.account_for_change_amount
			)
			self.set_warehouse = profile.get("warehouse") or self.set_warehouse

			for fieldname in (
				"currency",
				"letter_head",
				"tc_name",
				"company",
				"select_print_heading",
				"write_off_account",
				"taxes_and_charges",
				"write_off_cost_center",
				"apply_discount_on",
				"cost_center",
				"tax_category",
				"ignore_pricing_rule",
				"company_address",
				"update_stock",
			):
				if not for_validate:
					self.set(fieldname, profile.get(fieldname))

			if self.customer:
				customer_price_list, customer_group, customer_currency = frappe.db.get_value(
					"Customer", self.customer, ["default_price_list", "customer_group", "default_currency"]
				)
				customer_group_price_list = frappe.get_cached_value(
					"Customer Group", customer_group, "default_price_list"
				)
				selling_price_list = (
					customer_price_list or customer_group_price_list or profile.get("selling_price_list")
				)
				if customer_currency and customer_currency != profile.get("currency"):
					self.set("currency", customer_currency)

			else:
				selling_price_list = profile.get("selling_price_list")

			if selling_price_list:
				self.set("selling_price_list", selling_price_list)

			# set pos values in items
			for item in self.get("items"):
				if item.get("item_code"):
					profile_details = get_pos_profile_item_details_(
						ItemDetailsCtx(item.as_dict()), profile.get("company"), profile
					)
					for fname, val in profile_details.items():
						if (not for_validate) or (for_validate and not item.get(fname)):
							item.set(fname, val)

			# fetch terms
			if self.tc_name and not self.terms:
				self.terms = frappe.db.get_value("Terms and Conditions", self.tc_name, "terms")

			# fetch charges
			if self.taxes_and_charges and not len(self.get("taxes")):
				self.set_taxes()

		if not self.account_for_change_amount:
			self.account_for_change_amount = frappe.get_cached_value(
				"Company", self.company, "default_cash_account"
			)

		return profile

	@frappe.whitelist()
	def set_missing_values(self, for_validate=False):
		profile = self.set_pos_fields(for_validate)

		if not self.debit_to:
			self.debit_to = get_party_account("Customer", self.customer, self.company)
			self.party_account_currency = frappe.get_cached_value(
				"Account", self.debit_to, "account_currency"
			)
		if not self.due_date and self.customer:
			self.due_date = get_due_date(
				self.posting_date,
				"Customer",
				self.customer,
				self.company,
				template_name=self.payment_terms_template,
			)

		super(SalesInvoice, self).set_missing_values(for_validate)

		print_format = profile.get("print_format") if profile else None
		if not print_format and not cint(frappe.db.get_value("Print Format", "POS Invoice", "disabled")):
			print_format = "POS Invoice"

		if profile:
			return {
				"print_format": print_format,
				"utm_source": profile.get("utm_source"),
				"utm_campaign": profile.get("utm_campaign"),
				"utm_medium": profile.get("utm_medium"),
				"allow_print_before_pay": profile.get("allow_print_before_pay"),
				"set_default_payment": profile.get("set_grand_total_to_default_mop"),
			}

	@frappe.whitelist()
	def reset_mode_of_payments(self):
		if self.pos_profile:
			pos_profile = frappe.get_cached_doc("POS Profile", self.pos_profile)
			update_multi_mode_option(self, pos_profile)
			self.paid_amount = 0

	@frappe.whitelist()
	def create_payment_request(self):
		for pay in self.payments:
			if pay.type == "Phone":
				if pay.amount <= 0:
					frappe.throw(_("Payment amount cannot be less than or equal to 0"))

				if not self.contact_mobile:
					frappe.throw(_("Please enter the phone number first"))

				pay_req = self.get_existing_payment_request(pay)
				if not pay_req:
					pay_req = self.get_new_payment_request(pay)
					pay_req.submit()
				else:
					pay_req.request_phone_payment()

				return pay_req

	def get_new_payment_request(self, mop):
		payment_gateway_account = frappe.db.get_value(
			"Payment Gateway Account",
			{
				"payment_account": mop.account,
			},
			["name"],
		)

		args = {
			"dt": "POS Invoice",
			"dn": self.name,
			"recipient_id": self.contact_mobile,
			"mode_of_payment": mop.mode_of_payment,
			"payment_gateway_account": payment_gateway_account,
			"payment_request_type": "Inward",
			"party_type": "Customer",
			"party": self.customer,
			"return_doc": True,
		}
		return make_payment_request(**args)

	def get_existing_payment_request(self, pay):
		payment_gateway_account = frappe.db.get_value(
			"Payment Gateway Account",
			{
				"payment_account": pay.account,
			},
			["name"],
		)

		filters = {
			"reference_doctype": "POS Invoice",
			"reference_name": self.name,
			"payment_gateway_account": payment_gateway_account,
			"email_to": self.contact_mobile,
		}
		pr = frappe.db.get_value("Payment Request", filters=filters)
		if pr:
			return frappe.get_doc("Payment Request", pr)

	@frappe.whitelist()
	def update_payments(self, payments):
		if self.status == "Consolidated":
			frappe.throw(_("Create Payment Entry for Consolidated POS Invoices."))

		paid_amount = flt(self.paid_amount)
		total = flt(self.rounded_total) or flt(self.grand_total)

		if paid_amount >= total:
			frappe.throw(title=_("Invoice Paid"), msg=_("This invoice has already been paid."))

		idx = self.payments[-1].idx if self.payments else -1

		for d in payments:
			idx += 1
			payment = create_payments_on_invoice(self, idx, frappe._dict(d))
			paid_amount += flt(payment.amount)
			payment.submit()

		paid_amount = flt(flt(paid_amount), self.precision("paid_amount"))
		base_paid_amount = flt(flt(paid_amount * self.conversion_rate), self.precision("base_paid_amount"))
		outstanding_amount = (
			flt(flt(total - paid_amount), self.precision("outstanding_amount")) if total > paid_amount else 0
		)
		change_amount = (
			flt(flt(paid_amount - total), self.precision("change_amount")) if paid_amount > total else 0
		)

		pi = frappe.qb.DocType("POS Invoice")
		query = (
			frappe.qb.update(pi)
			.set(pi.paid_amount, paid_amount)
			.set(pi.base_paid_amount, base_paid_amount)
			.set(pi.outstanding_amount, outstanding_amount)
			.set(pi.change_amount, change_amount)
			.where(pi.name == self.name)
		)
		query.run()
		self.reload()

		self.set_status(update=True)


@frappe.whitelist()
def get_stock_availability(item_code, warehouse):
	if frappe.db.get_value("Item", item_code, "is_stock_item"):
		is_stock_item = True
		bin_qty = get_bin_qty(item_code, warehouse)
		pos_sales_qty = get_pos_reserved_qty(item_code, warehouse)

		return bin_qty - pos_sales_qty, is_stock_item, is_negative_stock_allowed(item_code=item_code)
	else:
		is_stock_item = True
		if frappe.db.exists("Product Bundle", {"name": item_code, "disabled": 0}):
			return get_bundle_availability(item_code, warehouse), is_stock_item, False
		else:
			is_stock_item = False
			# Is a service item or non_stock item
			return 0, is_stock_item, False


def get_product_bundle_stock_availability(item_code, warehouse, item_qty):
	is_stock_item = True
	bundle = frappe.get_doc("Product Bundle", item_code)
	availabilities = []
	for bundle_item in bundle.items:
		if frappe.get_value("Item", bundle_item.item_code, "is_stock_item"):
			bin_qty = get_bin_qty(bundle_item.item_code, warehouse)
			reserved_qty = get_pos_reserved_qty(bundle_item.item_code, warehouse)
			available = bin_qty - reserved_qty
			availabilities.append(
				{
					"item_code": bundle_item.item_code,
					"required": bundle_item.qty * item_qty,
					"available": available,
				}
			)

	return availabilities, is_stock_item, is_negative_stock_allowed(item_code=item_code)


def get_bundle_availability(bundle_item_code, warehouse):
	product_bundle = frappe.get_doc("Product Bundle", bundle_item_code)

	bundle_bin_qty = 1000000
	for item in product_bundle.items:
		item_bin_qty = get_bin_qty(item.item_code, warehouse)

		max_available_bundles = item_bin_qty / item.qty
		if bundle_bin_qty > max_available_bundles and frappe.get_value(
			"Item", item.item_code, "is_stock_item"
		):
			bundle_bin_qty = max_available_bundles

	pos_sales_qty = get_pos_reserved_qty(bundle_item_code, warehouse)
	return bundle_bin_qty - pos_sales_qty


def get_bin_qty(item_code, warehouse):
	bin_qty = frappe.db.sql(
		"""select actual_qty from `tabBin`
		where item_code = %s and warehouse = %s
		limit 1""",
		(item_code, warehouse),
		as_dict=1,
	)

	return bin_qty[0].actual_qty or 0 if bin_qty else 0


def get_pos_reserved_qty(item_code, warehouse):
	"""
	Calculate total quantity reserved for the given item and warehouse.

	Includes:
	- Direct sales of the item in submitted POS Invoices
	- Sales of the item as a component of a Product Bundle

	Excludes consolidated invoices (already merged into Sales Invoices via
	POS Closing Entry). Used to reflect near real-time availability in the
	POS UI and to prevent overselling while multiple sessions may be active.
	"""
	pinv_item_reserved_qty = get_pos_reserved_qty_from_table("POS Invoice Item", item_code, warehouse)
	packed_item_reserved_qty = get_pos_reserved_qty_from_table("Packed Item", item_code, warehouse)

	reserved_qty = pinv_item_reserved_qty + packed_item_reserved_qty

	return reserved_qty


def get_pos_reserved_qty_from_table(child_table, item_code, warehouse):
	"""
	Get the total reserved quantity for a given item in POS Invoices
	from a specific child table.

	Args:
	  child_table (str): Name of the child table to query
	                (e.g., "POS Invoice Item", "Packed Item").
	  item_code (str): The Item Code to filter by.
	  warehouse (str): The Warehouse to filter by.

	Returns:
	  float: The total reserved quantity for the item in the given
	                warehouse from submitted, unconsolidated POS Invoices.
	"""
	p_inv = frappe.qb.DocType("POS Invoice")
	p_item = frappe.qb.DocType(child_table)

	qty_column = "qty" if child_table == "Packed Item" else "stock_qty"

	reserved_qty = (
		frappe.qb.from_(p_inv)
		.from_(p_item)
		.select(Sum(p_item[qty_column]).as_("stock_qty"))
		.where(
			(p_inv.name == p_item.parent)
			& (IfNull(p_inv.consolidated_invoice, "") == "")
			& (p_item.docstatus == 1)
			& (p_item.item_code == item_code)
			& (p_item.warehouse == warehouse)
		)
	).run(as_dict=True)

	return flt(reserved_qty[0].stock_qty) if reserved_qty else 0


@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("POS Invoice", source_name, target_doc)


@frappe.whitelist()
def make_merge_log(invoices):
	import json

	if isinstance(invoices, str):
		invoices = json.loads(invoices)

	if len(invoices) == 0:
		frappe.throw(_("At least one invoice has to be selected."))

	merge_log = frappe.new_doc("POS Invoice Merge Log")
	merge_log.posting_date = getdate(nowdate())
	for inv in invoices:
		inv_data = frappe.db.get_values(
			"POS Invoice", inv.get("name"), ["customer", "posting_date", "grand_total"], as_dict=1
		)[0]
		merge_log.customer = inv_data.customer
		merge_log.append(
			"pos_invoices",
			{
				"pos_invoice": inv.get("name"),
				"customer": inv_data.customer,
				"posting_date": inv_data.posting_date,
				"grand_total": inv_data.grand_total,
			},
		)

	if merge_log.get("pos_invoices"):
		return merge_log.as_dict()


def add_return_modes(doc, pos_profile):
	def append_payment(payment_mode):
		payment = doc.append("payments", {})
		payment.default = payment_mode.default
		payment.mode_of_payment = payment_mode.parent
		payment.account = payment_mode.default_account
		payment.type = payment_mode.type

	for pos_payment_method in pos_profile.get("payments"):
		pos_payment_method = pos_payment_method.as_dict()
		mode_of_payment = pos_payment_method.mode_of_payment
		if pos_payment_method.allow_in_returns and not [
			d for d in doc.get("payments") if d.mode_of_payment == mode_of_payment
		]:
			payment_mode = get_mode_of_payment_info(mode_of_payment, doc.company)
			append_payment(payment_mode[0])


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	if pos_profile := filters.get("pos_profile")[1]:
		pos_profile = frappe.get_cached_doc("POS Profile", pos_profile)
		if item_groups := get_item_group(pos_profile):
			filters["item_group"] = ["in", tuple(item_groups)]

		del filters["pos_profile"]

	else:
		filters.pop("pos_profile", None)

	return _item_query(doctype, txt, searchfield, start, page_len, filters, as_dict)


def get_item_group(pos_profile):
	item_groups = []
	if pos_profile.get("item_groups"):
		# Get items based on the item groups defined in the POS profile
		for row in pos_profile.get("item_groups"):
			item_groups.append(row.item_group)
			item_groups.extend(get_descendants_of("Item Group", row.item_group))

	return list(set(item_groups))


def create_payments_on_invoice(doc, idx, payment_details):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account

	payment = frappe.new_doc("Sales Invoice Payment")
	payment.idx = idx
	payment.mode_of_payment = payment_details.mode_of_payment
	payment.amount = payment_details.amount
	payment.base_amount = payment.amount * doc.conversion_rate
	payment.parent = doc.name
	payment.parentfield = "payments"
	payment.parenttype = doc.doctype
	payment.account = get_bank_cash_account(payment.mode_of_payment, doc.company).get("account")

	return payment
