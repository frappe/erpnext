# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cint, flt, get_link_to_form, getdate, nowdate

from erpnext.accounts.doctype.loyalty_program.loyalty_program import validate_loyalty_points
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	SalesInvoice,
	get_bank_cash_account,
	get_mode_of_payment_info,
	update_multi_mode_option,
)
from erpnext.accounts.party import get_due_date, get_party_account
from erpnext.stock.doctype.batch.batch import get_batch_qty, get_pos_reserved_batch_qty
from erpnext.stock.doctype.serial_no.serial_no import (
	get_delivered_serial_nos,
	get_pos_reserved_serial_nos,
	get_serial_nos,
)


class POSInvoice(SalesInvoice):
	def __init__(self, *args, **kwargs):
		super(POSInvoice, self).__init__(*args, **kwargs)

	def validate(self):
		if not cint(self.is_pos):
			frappe.throw(
				_("POS Invoice should have {} field checked.").format(frappe.bold("Include Payment"))
			)

		# run on validate method of selling controller
		super(SalesInvoice, self).validate()
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
		self.set_account_for_mode_of_payment()
		self.validate_pos()
		self.validate_payment_amount()
		self.validate_loyalty_transaction()
		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code

			validate_coupon_code(self.coupon_code)

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

		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

			update_coupon_code_count(self.coupon_code, "used")

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
		self.ignore_linked_doctypes = "Payment Ledger Entry"
		# run on cancel method of selling controller
		super(SalesInvoice, self).on_cancel()
		if not self.is_return and self.loyalty_program:
			self.delete_loyalty_point_entry()
		elif self.is_return and self.return_against and self.loyalty_program:
			against_psi_doc = frappe.get_doc("POS Invoice", self.return_against)
			against_psi_doc.delete_loyalty_point_entry()
			against_psi_doc.make_loyalty_point_entry()

		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

			update_coupon_code_count(self.coupon_code, "cancelled")

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
					return frappe.throw(_("Payment related to {0} is not completed").format(pay.mode_of_payment))

	def validate_pos_reserved_serial_nos(self, item):
		serial_nos = get_serial_nos(item.serial_no)
		filters = {"item_code": item.item_code, "warehouse": item.warehouse}
		if item.batch_no:
			filters["batch_no"] = item.batch_no

		reserved_serial_nos = get_pos_reserved_serial_nos(filters)
		invalid_serial_nos = [s for s in serial_nos if s in reserved_serial_nos]

		bold_invalid_serial_nos = frappe.bold(", ".join(invalid_serial_nos))
		if len(invalid_serial_nos) == 1:
			frappe.throw(
				_(
					"Row #{}: Serial No. {} has already been transacted into another POS Invoice. Please select valid serial no."
				).format(item.idx, bold_invalid_serial_nos),
				title=_("Item Unavailable"),
			)
		elif invalid_serial_nos:
			frappe.throw(
				_(
					"Row #{}: Serial Nos. {} have already been transacted into another POS Invoice. Please select valid serial no."
				).format(item.idx, bold_invalid_serial_nos),
				title=_("Item Unavailable"),
			)

	def validate_pos_reserved_batch_qty(self, item):
		filters = {"item_code": item.item_code, "warehouse": item.warehouse, "batch_no": item.batch_no}

		available_batch_qty = get_batch_qty(item.batch_no, item.warehouse, item.item_code)
		reserved_batch_qty = get_pos_reserved_batch_qty(filters)

		bold_item_name = frappe.bold(item.item_name)
		bold_extra_batch_qty_needed = frappe.bold(
			abs(available_batch_qty - reserved_batch_qty - item.qty)
		)
		bold_invalid_batch_no = frappe.bold(item.batch_no)

		if (available_batch_qty - reserved_batch_qty) == 0:
			frappe.throw(
				_(
					"Row #{}: Batch No. {} of item {} has no stock available. Please select valid batch no."
				).format(item.idx, bold_invalid_batch_no, bold_item_name),
				title=_("Item Unavailable"),
			)
		elif (available_batch_qty - reserved_batch_qty - item.qty) < 0:
			frappe.throw(
				_(
					"Row #{}: Batch No. {} of item {} has less than required stock available, {} more required"
				).format(
					item.idx, bold_invalid_batch_no, bold_item_name, bold_extra_batch_qty_needed
				),
				title=_("Item Unavailable"),
			)

	def validate_delivered_serial_nos(self, item):
		delivered_serial_nos = get_delivered_serial_nos(item.serial_no)

		if delivered_serial_nos:
			bold_delivered_serial_nos = frappe.bold(", ".join(delivered_serial_nos))
			frappe.throw(
				_(
					"Row #{}: Serial No. {} has already been transacted into another Sales Invoice. Please select valid serial no."
				).format(item.idx, bold_delivered_serial_nos),
				title=_("Item Unavailable"),
			)

	def validate_invalid_serial_nos(self, item):
		serial_nos = get_serial_nos(item.serial_no)
		error_msg = []
		invalid_serials, msg = "", ""
		for serial_no in serial_nos:
			if not frappe.db.exists("Serial No", serial_no):
				invalid_serials = invalid_serials + (", " if invalid_serials else "") + serial_no
		msg = _("Row #{}: Following Serial numbers for item {} are <b>Invalid</b>: {}").format(
			item.idx, frappe.bold(item.get("item_code")), frappe.bold(invalid_serials)
		)
		if invalid_serials:
			error_msg.append(msg)

		if error_msg:
			frappe.throw(error_msg, title=_("Invalid Item"), as_list=True)

	def validate_stock_availablility(self):
		if self.is_return:
			return

		if self.docstatus.is_draft() and not frappe.db.get_value(
			"POS Profile", self.pos_profile, "validate_stock_on_save"
		):
			return

		from erpnext.stock.stock_ledger import is_negative_stock_allowed

		for d in self.get("items"):
			if d.serial_no:
				self.validate_pos_reserved_serial_nos(d)
				self.validate_delivered_serial_nos(d)
				self.validate_invalid_serial_nos(d)
			elif d.batch_no:
				self.validate_pos_reserved_batch_qty(d)
			else:
				if is_negative_stock_allowed(item_code=d.item_code):
					return

				available_stock, is_stock_item = get_stock_availability(d.item_code, d.warehouse)

				item_code, warehouse, qty = (
					frappe.bold(d.item_code),
					frappe.bold(d.warehouse),
					frappe.bold(d.qty),
				)
				if is_stock_item and flt(available_stock) <= 0:
					frappe.throw(
						_("Row #{}: Item Code: {} is not available under warehouse {}.").format(
							d.idx, item_code, warehouse
						),
						title=_("Item Unavailable"),
					)
				elif is_stock_item and flt(available_stock) < flt(d.qty):
					frappe.throw(
						_(
							"Row #{}: Stock quantity not enough for Item Code: {} under warehouse {}. Available quantity {}."
						).format(d.idx, item_code, warehouse, available_stock),
						title=_("Item Unavailable"),
					)

	def validate_serialised_or_batched_item(self):
		error_msg = []
		for d in self.get("items"):
			serialized = d.get("has_serial_no")
			batched = d.get("has_batch_no")
			no_serial_selected = not d.get("serial_no")
			no_batch_selected = not d.get("batch_no")

			msg = ""
			item_code = frappe.bold(d.item_code)
			serial_nos = get_serial_nos(d.serial_no)
			if serialized and batched and (no_batch_selected or no_serial_selected):
				msg = _(
					"Row #{}: Please select a serial no and batch against item: {} or remove it to complete transaction."
				).format(d.idx, item_code)
			elif serialized and no_serial_selected:
				msg = _(
					"Row #{}: No serial number selected against item: {}. Please select one or remove it to complete transaction."
				).format(d.idx, item_code)
			elif batched and no_batch_selected:
				msg = _(
					"Row #{}: No batch selected against item: {}. Please select a batch or remove it to complete transaction."
				).format(d.idx, item_code)
			elif serialized and not no_serial_selected and len(serial_nos) != d.qty:
				msg = _("Row #{}: You must select {} serial numbers for item {}.").format(
					d.idx, frappe.bold(cint(d.qty)), item_code
				)

			if msg:
				error_msg.append(msg)

		if error_msg:
			frappe.throw(error_msg, title=_("Invalid Item"), as_list=True)

	def validate_return_items_qty(self):
		if not self.get("is_return"):
			return

		for d in self.get("items"):
			if d.get("qty") > 0:
				frappe.throw(
					_(
						"Row #{}: You cannot add postive quantities in a return invoice. Please remove item {} to complete the return."
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
			and frappe.db.get_value("Account", self.account_for_change_amount, "company") != self.company
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

		if self.is_return:
			invoice_total = self.rounded_total or self.grand_total
			if total_amount_in_payments and total_amount_in_payments < invoice_total:
				frappe.throw(_("Total payments amount can't be greater than {}").format(-invoice_total))

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
		from erpnext.stock.get_item_details import get_pos_profile, get_pos_profile_item_details

		if not self.pos_profile:
			pos_profile = get_pos_profile(self.company) or {}
			if not pos_profile:
				frappe.throw(_("No POS Profile found. Please create a New POS Profile first"))
			self.pos_profile = pos_profile.get("name")

		profile = {}
		if self.pos_profile:
			profile = frappe.get_doc("POS Profile", self.pos_profile)

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
				customer_group_price_list = frappe.db.get_value(
					"Customer Group", customer_group, "default_price_list"
				)
				selling_price_list = (
					customer_price_list or customer_group_price_list or profile.get("selling_price_list")
				)
				if customer_currency != profile.get("currency"):
					self.set("currency", customer_currency)

			else:
				selling_price_list = profile.get("selling_price_list")

			if selling_price_list:
				self.set("selling_price_list", selling_price_list)

			# set pos values in items
			for item in self.get("items"):
				if item.get("item_code"):
					profile_details = get_pos_profile_item_details(
						profile.get("company"), frappe._dict(item.as_dict()), profile
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
			self.party_account_currency = frappe.db.get_value(
				"Account", self.debit_to, "account_currency", cache=True
			)
		if not self.due_date and self.customer:
			self.due_date = get_due_date(self.posting_date, "Customer", self.customer, self.company)

		super(SalesInvoice, self).set_missing_values(for_validate)

		print_format = profile.get("print_format") if profile else None
		if not print_format and not cint(frappe.db.get_value("Print Format", "POS Invoice", "disabled")):
			print_format = "POS Invoice"

		if profile:
			return {
				"print_format": print_format,
				"campaign": profile.get("campaign"),
				"allow_print_before_pay": profile.get("allow_print_before_pay"),
			}

	@frappe.whitelist()
	def reset_mode_of_payments(self):
		if self.pos_profile:
			pos_profile = frappe.get_cached_doc("POS Profile", self.pos_profile)
			update_multi_mode_option(self, pos_profile)
			self.paid_amount = 0

	def set_account_for_mode_of_payment(self):
		for pay in self.payments:
			if not pay.account:
				pay.account = get_bank_cash_account(pay.mode_of_payment, self.company).get("account")

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
def get_stock_availability(item_code, warehouse):
	if frappe.db.get_value("Item", item_code, "is_stock_item"):
		is_stock_item = True
		bin_qty = get_bin_qty(item_code, warehouse)
		pos_sales_qty = get_pos_reserved_qty(item_code, warehouse)
		return bin_qty - pos_sales_qty, is_stock_item
	else:
		is_stock_item = True
		if frappe.db.exists("Product Bundle", item_code):
			return get_bundle_availability(item_code, warehouse), is_stock_item
		else:
			is_stock_item = False
			# Is a service item or non_stock item
			return 0, is_stock_item


def get_bundle_availability(bundle_item_code, warehouse):
	product_bundle = frappe.get_doc("Product Bundle", bundle_item_code)

	bundle_bin_qty = 1000000
	for item in product_bundle.items:
		item_bin_qty = get_bin_qty(item.item_code, warehouse)
		item_pos_reserved_qty = get_pos_reserved_qty(item.item_code, warehouse)
		available_qty = item_bin_qty - item_pos_reserved_qty

		max_available_bundles = available_qty / item.qty
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
	reserved_qty = frappe.db.sql(
		"""select sum(p_item.qty) as qty
		from `tabPOS Invoice` p, `tabPOS Invoice Item` p_item
		where p.name = p_item.parent
		and ifnull(p.consolidated_invoice, '') = ''
		and p_item.docstatus = 1
		and p_item.item_code = %s
		and p_item.warehouse = %s
		""",
		(item_code, warehouse),
		as_dict=1,
	)

	return reserved_qty[0].qty or 0 if reserved_qty else 0


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
		frappe.throw(_("Atleast one invoice has to be selected."))

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
