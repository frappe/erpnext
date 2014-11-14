# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt, rounded, cstr, comma_or
from erpnext.setup.utils import get_company_currency
from frappe import _, throw
from erpnext.stock.get_item_details import get_available_qty

from erpnext.controllers.stock_controller import StockController

class SellingController(StockController):
	def __setup__(self):
		if hasattr(self, "fname"):
			self.table_print_templates = {
				self.fname: "templates/print_formats/includes/item_grid.html",
				"other_charges": "templates/print_formats/includes/taxes.html",
			}

	def onload(self):
		if self.doctype in ("Sales Order", "Delivery Note", "Sales Invoice"):
			for item in self.get(self.fname):
				item.update(get_available_qty(item.item_code,
					item.warehouse))

	def validate(self):
		super(SellingController, self).validate()
		self.validate_max_discount()
		check_active_sales_items(self)

	def get_sender(self, comm):
		sender = None
		if cint(frappe.db.get_value('Sales Email Settings', None, 'extract_emails')):
			sender = frappe.db.get_value('Sales Email Settings', None, 'email_id')

		return sender or comm.sender or frappe.session.user

	def set_missing_values(self, for_validate=False):
		super(SellingController, self).set_missing_values(for_validate)

		# set contact and address details for customer, if they are not mentioned
		self.set_missing_lead_customer_details()
		self.set_price_list_and_item_details()
		if self.get("__islocal"):
			self.set_taxes("other_charges", "taxes_and_charges")

	def set_missing_lead_customer_details(self):
		if getattr(self, "customer", None):
			from erpnext.accounts.party import _get_party_details
			party_details = _get_party_details(self.customer,
				ignore_permissions=getattr(self, "ignore_permissions", None))
			if not self.meta.get_field("sales_team"):
				party_details.pop("sales_team")

			self.update_if_missing(party_details)

		elif getattr(self, "lead", None):
			from erpnext.selling.doctype.lead.lead import get_lead_details
			self.update_if_missing(get_lead_details(self.lead))

	def set_price_list_and_item_details(self):
		self.set_price_list_currency("Selling")
		self.set_missing_item_details()

	def apply_shipping_rule(self):
		if self.shipping_rule:
			shipping_rule = frappe.get_doc("Shipping Rule", self.shipping_rule)
			value = self.net_total

			# TODO
			# shipping rule calculation based on item's net weight

			shipping_amount = 0.0
			for condition in shipping_rule.get("shipping_rule_conditions"):
				if not condition.to_value or (flt(condition.from_value) <= value <= flt(condition.to_value)):
					shipping_amount = condition.shipping_amount
					break

			shipping_charge = {
				"doctype": "Sales Taxes and Charges",
				"charge_type": "Actual",
				"account_head": shipping_rule.account,
				"cost_center": shipping_rule.cost_center
			}

			existing_shipping_charge = self.get("other_charges", filters=shipping_charge)
			if existing_shipping_charge:
				# take the last record found
				existing_shipping_charge[-1].rate = shipping_amount
			else:
				shipping_charge["rate"] = shipping_amount
				shipping_charge["description"] = shipping_rule.label
				self.append("other_charges", shipping_charge)

			self.calculate_taxes_and_totals()

	def remove_shipping_charge(self):
		if self.shipping_rule:
			shipping_rule = frappe.get_doc("Shipping Rule", self.shipping_rule)
			existing_shipping_charge = self.get("other_charges", {
				"doctype": "Sales Taxes and Charges",
				"charge_type": "Actual",
				"account_head": shipping_rule.account,
				"cost_center": shipping_rule.cost_center
			})
			if existing_shipping_charge:
				self.get("other_charges").remove(existing_shipping_charge[-1])
				self.calculate_taxes_and_totals()

	def set_total_in_words(self):
		from frappe.utils import money_in_words
		company_currency = get_company_currency(self.company)

		disable_rounded_total = cint(frappe.db.get_value("Global Defaults", None,
			"disable_rounded_total"))

		if self.meta.get_field("in_words"):
			self.in_words = money_in_words(disable_rounded_total and
				self.grand_total or self.rounded_total, company_currency)
		if self.meta.get_field("in_words_export"):
			self.in_words_export = money_in_words(disable_rounded_total and
				self.grand_total_export or self.rounded_total_export, self.currency)

	def calculate_taxes_and_totals(self):
		self.other_fname = "other_charges"

		super(SellingController, self).calculate_taxes_and_totals()

		self.calculate_total_advance("Sales Invoice", "advance_adjustment_details")
		self.calculate_commission()
		self.calculate_contribution()

	def determine_exclusive_rate(self):
		if not any((cint(tax.included_in_print_rate) for tax in self.tax_doclist)):
			# no inclusive tax
			return

		for item in self.item_doclist:
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
			cumulated_tax_fraction = 0
			for i, tax in enumerate(self.tax_doclist):
				tax.tax_fraction_for_current_item = self.get_current_tax_fraction(tax, item_tax_map)

				if i==0:
					tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item
				else:
					tax.grand_total_fraction_for_current_item = \
						self.tax_doclist[i-1].grand_total_fraction_for_current_item \
						+ tax.tax_fraction_for_current_item

				cumulated_tax_fraction += tax.tax_fraction_for_current_item

			if cumulated_tax_fraction and not self.discount_amount_applied and item.qty:
				item.base_amount = flt((item.amount * self.conversion_rate) /
					(1 + cumulated_tax_fraction), self.precision("base_amount", item))

				item.base_rate = flt(item.base_amount / item.qty, self.precision("base_rate", item))
				item.discount_percentage = flt(item.discount_percentage, self.precision("discount_percentage", item))

				if item.discount_percentage == 100:
					item.base_price_list_rate = item.base_rate
					item.base_rate = 0.0
				else:
					item.base_price_list_rate = flt(item.base_rate / (1 - (item.discount_percentage / 100.0)),
						self.precision("base_price_list_rate", item))

	def get_current_tax_fraction(self, tax, item_tax_map):
		"""
			Get tax fraction for calculating tax exclusive amount
			from tax inclusive amount
		"""
		current_tax_fraction = 0

		if cint(tax.included_in_print_rate):
			tax_rate = self._get_tax_rate(tax, item_tax_map)

			if tax.charge_type == "On Net Total":
				current_tax_fraction = tax_rate / 100.0

			elif tax.charge_type == "On Previous Row Amount":
				current_tax_fraction = (tax_rate / 100.0) * \
					self.tax_doclist[cint(tax.row_id) - 1].tax_fraction_for_current_item

			elif tax.charge_type == "On Previous Row Total":
				current_tax_fraction = (tax_rate / 100.0) * \
					self.tax_doclist[cint(tax.row_id) - 1].grand_total_fraction_for_current_item

		return current_tax_fraction

	def calculate_item_values(self):
		if not self.discount_amount_applied:
			for item in self.item_doclist:
				self.round_floats_in(item)

				if item.discount_percentage == 100:
					item.rate = 0
				elif not item.rate:
					item.rate = flt(item.price_list_rate * (1.0 - (item.discount_percentage / 100.0)),
						self.precision("rate", item))

				item.amount = flt(item.rate * item.qty,
					self.precision("amount", item))

				self._set_in_company_currency(item, "price_list_rate", "base_price_list_rate")
				self._set_in_company_currency(item, "rate", "base_rate")
				self._set_in_company_currency(item, "amount", "base_amount")

	def calculate_net_total(self):
		self.net_total = self.net_total_export = 0.0

		for item in self.item_doclist:
			self.net_total += item.base_amount
			self.net_total_export += item.amount

		self.round_floats_in(self, ["net_total", "net_total_export"])

	def calculate_totals(self):
		self.grand_total = flt(self.tax_doclist[-1].total if self.tax_doclist else self.net_total)

		self.grand_total_export = flt(self.grand_total / self.conversion_rate)

		self.other_charges_total = flt(self.grand_total - self.net_total, self.precision("other_charges_total"))

		self.other_charges_total_export = flt(self.grand_total_export - self.net_total_export +
			flt(self.discount_amount), self.precision("other_charges_total_export"))

		self.grand_total = flt(self.grand_total, self.precision("grand_total"))
		self.grand_total_export = flt(self.grand_total_export, self.precision("grand_total_export"))

		self.rounded_total = rounded(self.grand_total)
		self.rounded_total_export = rounded(self.grand_total_export)

	def apply_discount_amount(self):
		if self.discount_amount:
			grand_total_for_discount_amount = self.get_grand_total_for_discount_amount()

			if grand_total_for_discount_amount:
				# calculate item amount after Discount Amount
				for item in self.item_doclist:
					distributed_amount = flt(self.discount_amount) * item.base_amount / grand_total_for_discount_amount
					item.base_amount = flt(item.base_amount - distributed_amount, self.precision("base_amount", item))

				self.discount_amount_applied = True
				self._calculate_taxes_and_totals()

	def get_grand_total_for_discount_amount(self):
		actual_taxes_dict = {}

		for tax in self.tax_doclist:
			if tax.charge_type == "Actual":
				actual_taxes_dict.setdefault(tax.idx, tax.tax_amount)
			elif tax.row_id in actual_taxes_dict:
				actual_tax_amount = flt(actual_taxes_dict.get(tax.row_id, 0)) * \
					flt(tax.rate) / 100
				actual_taxes_dict.setdefault(tax.idx, actual_tax_amount)

		grand_total_for_discount_amount = flt(self.grand_total - sum(actual_taxes_dict.values()),
			self.precision("grand_total"))
		return grand_total_for_discount_amount

	def calculate_outstanding_amount(self):
		# NOTE:
		# write_off_amount is only for POS Invoice
		# total_advance is only for non POS Invoice
		if self.doctype == "Sales Invoice" and self.docstatus == 0:
			self.round_floats_in(self, ["grand_total", "total_advance", "write_off_amount",
				"paid_amount"])
			total_amount_to_pay = self.grand_total - self.write_off_amount
			self.outstanding_amount = flt(total_amount_to_pay - self.total_advance \
				- self.paid_amount,	self.precision("outstanding_amount"))

	def calculate_commission(self):
		if self.meta.get_field("commission_rate"):
			self.round_floats_in(self, ["net_total", "commission_rate"])
			if self.commission_rate > 100.0:
				throw(_("Commission rate cannot be greater than 100"))

			self.total_commission = flt(self.net_total * self.commission_rate / 100.0,
				self.precision("total_commission"))

	def calculate_contribution(self):
		if not self.meta.get_field("sales_team"):
			return

		total = 0.0
		sales_team = self.get("sales_team")
		for sales_person in sales_team:
			self.round_floats_in(sales_person)

			sales_person.allocated_amount = flt(
				self.net_total * sales_person.allocated_percentage / 100.0,
				self.precision("allocated_amount", sales_person))

			total += sales_person.allocated_percentage

		if sales_team and total != 100.0:
			throw(_("Total allocated percentage for sales team should be 100"))

	def validate_order_type(self):
		valid_types = ["Sales", "Maintenance", "Shopping Cart"]
		if not self.order_type:
			self.order_type = "Sales"
		elif self.order_type not in valid_types:
			throw(_("Order Type must be one of {0}").format(comma_or(valid_types)))

	def check_credit(self, grand_total):
		customer_account = frappe.db.get_value("Account", {"company": self.company,
			"master_name": self.customer}, "name")
		if customer_account:
			invoice_outstanding = frappe.db.sql("""select
				sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
				from `tabGL Entry` where account = %s""", customer_account)
			invoice_outstanding = flt(invoice_outstanding[0][0]) if invoice_outstanding else 0

			ordered_amount_to_be_billed = frappe.db.sql("""
				select sum(grand_total*(100 - ifnull(per_billed, 0))/100)
				from `tabSales Order`
				where customer=%s and docstatus = 1
				and ifnull(per_billed, 0) < 100 and status != 'Stopped'""", self.customer)

			ordered_amount_to_be_billed = flt(ordered_amount_to_be_billed[0][0]) \
				if ordered_amount_to_be_billed else 0.0

			total_outstanding = invoice_outstanding + ordered_amount_to_be_billed

			frappe.get_doc('Account', customer_account).check_credit_limit(total_outstanding)

	def validate_max_discount(self):
		for d in self.get(self.fname):
			discount = flt(frappe.db.get_value("Item", d.item_code, "max_discount"))

			if discount and flt(d.discount_percentage) > discount:
				frappe.throw(_("Maxiumm discount for Item {0} is {1}%").format(d.item_code, discount))

	def get_item_list(self):
		il = []
		for d in self.get(self.fname):
			reserved_warehouse = ""
			reserved_qty_for_main_item = 0

			if d.qty is None:
				frappe.throw(_("Row {0}: Qty is mandatory").format(d.idx))

			if self.doctype == "Sales Order":
				if (frappe.db.get_value("Item", d.item_code, "is_stock_item") == 'Yes' or
					self.has_sales_bom(d.item_code)) and not d.warehouse:
						frappe.throw(_("Reserved Warehouse required for stock Item {0} in row {1}").format(d.item_code, d.idx))
				reserved_warehouse = d.warehouse
				if flt(d.qty) > flt(d.delivered_qty):
					reserved_qty_for_main_item = flt(d.qty) - flt(d.delivered_qty)

			elif self.doctype == "Delivery Note" and d.against_sales_order:
				# if SO qty is 10 and there is tolerance of 20%, then it will allow DN of 12.
				# But in this case reserved qty should only be reduced by 10 and not 12

				already_delivered_qty = self.get_already_delivered_qty(self.name,
					d.against_sales_order, d.prevdoc_detail_docname)
				so_qty, reserved_warehouse = self.get_so_qty_and_warehouse(d.prevdoc_detail_docname)

				if already_delivered_qty + d.qty > so_qty:
					reserved_qty_for_main_item = -(so_qty - already_delivered_qty)
				else:
					reserved_qty_for_main_item = -flt(d.qty)

			if self.has_sales_bom(d.item_code):
				for p in self.get("packing_details"):
					if p.parent_detail_docname == d.name and p.parent_item == d.item_code:
						# the packing details table's qty is already multiplied with parent's qty
						il.append(frappe._dict({
							'warehouse': p.warehouse,
							'reserved_warehouse': reserved_warehouse,
							'item_code': p.item_code,
							'qty': flt(p.qty),
							'reserved_qty': (flt(p.qty)/flt(d.qty)) * reserved_qty_for_main_item,
							'uom': p.uom,
							'batch_no': cstr(p.batch_no).strip(),
							'serial_no': cstr(p.serial_no).strip(),
							'name': d.name
						}))
			else:
				il.append(frappe._dict({
					'warehouse': d.warehouse,
					'reserved_warehouse': reserved_warehouse,
					'item_code': d.item_code,
					'qty': d.qty,
					'reserved_qty': reserved_qty_for_main_item,
					'uom': d.stock_uom,
					'batch_no': cstr(d.get("batch_no")).strip(),
					'serial_no': cstr(d.get("serial_no")).strip(),
					'name': d.name
				}))
		return il

	def has_sales_bom(self, item_code):
		return frappe.db.sql("""select name from `tabSales BOM`
			where new_item_code=%s and docstatus != 2""", item_code)

	def get_already_delivered_qty(self, dn, so, so_detail):
		qty = frappe.db.sql("""select sum(qty) from `tabDelivery Note Item`
			where prevdoc_detail_docname = %s and docstatus = 1
			and against_sales_order = %s
			and parent != %s""", (so_detail, so, dn))
		return qty and flt(qty[0][0]) or 0.0

	def get_so_qty_and_warehouse(self, so_detail):
		so_item = frappe.db.sql("""select qty, warehouse from `tabSales Order Item`
			where name = %s and docstatus = 1""", so_detail, as_dict=1)
		so_qty = so_item and flt(so_item[0]["qty"]) or 0.0
		so_warehouse = so_item and so_item[0]["warehouse"] or ""
		return so_qty, so_warehouse

	def check_stop_sales_order(self, ref_fieldname):
		for d in self.get(self.fname):
			if d.get(ref_fieldname):
				status = frappe.db.get_value("Sales Order", d.get(ref_fieldname), "status")
				if status == "Stopped":
					frappe.throw(_("Sales Order {0} is stopped").format(d.get(ref_fieldname)))

def check_active_sales_items(obj):
	for d in obj.get(obj.fname):
		if d.item_code:
			item = frappe.db.sql("""select docstatus, is_sales_item,
				is_service_item, income_account from tabItem where name = %s""",
				d.item_code, as_dict=True)[0]
			if item.is_sales_item == 'No' and item.is_service_item == 'No':
				frappe.throw(_("Item {0} must be Sales or Service Item in {1}").format(d.item_code, d.idx))
			if getattr(d, "income_account", None) and not item.income_account:
				frappe.db.set_value("Item", d.item_code, "income_account",
					d.income_account)
