# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt, cstr, comma_or
from erpnext.setup.utils import get_company_currency
from frappe import _, throw
from erpnext.stock.get_item_details import get_available_qty

from erpnext.controllers.stock_controller import StockController

class SellingController(StockController):
	def __setup__(self):
		if hasattr(self, "taxes"):
			self.print_templates = {
				"taxes": "templates/print_formats/includes/taxes.html"
			}

	def get_feed(self):
		return _("To {0} | {1} {2}").format(self.customer_name, self.currency,
			self.grand_total)

	def onload(self):
		if self.doctype in ("Sales Order", "Delivery Note", "Sales Invoice"):
			for item in self.get("items"):
				item.update(get_available_qty(item.item_code,
					item.warehouse))

	def validate(self):
		super(SellingController, self).validate()
		self.validate_max_discount()
		check_active_sales_items(self)

	def check_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit
		check_credit_limit(self.customer, self.company)

	def set_missing_values(self, for_validate=False):
		super(SellingController, self).set_missing_values(for_validate)

		# set contact and address details for customer, if they are not mentioned
		self.set_missing_lead_customer_details()
		self.set_price_list_and_item_details()
		if self.get("__islocal"):
			self.set_taxes("taxes", "taxes_and_charges")

	def set_missing_lead_customer_details(self):
		if getattr(self, "customer", None):
			from erpnext.accounts.party import _get_party_details
			party_details = _get_party_details(self.customer,
				ignore_permissions=self.flags.ignore_permissions)
			if not self.meta.get_field("sales_team"):
				party_details.pop("sales_team")

			self.update_if_missing(party_details)

		elif getattr(self, "lead", None):
			from erpnext.crm.doctype.lead.lead import get_lead_details
			self.update_if_missing(get_lead_details(self.lead))

	def set_price_list_and_item_details(self):
		self.set_price_list_currency("Selling")
		self.set_missing_item_details()

	def apply_shipping_rule(self):
		if self.shipping_rule:
			shipping_rule = frappe.get_doc("Shipping Rule", self.shipping_rule)
			value = self.base_net_total

			# TODO
			# shipping rule calculation based on item's net weight

			shipping_amount = 0.0
			for condition in shipping_rule.get("conditions"):
				if not condition.to_value or (flt(condition.from_value) <= value <= flt(condition.to_value)):
					shipping_amount = condition.shipping_amount
					break

			shipping_charge = {
				"doctype": "Sales Taxes and Charges",
				"charge_type": "Actual",
				"account_head": shipping_rule.account,
				"cost_center": shipping_rule.cost_center
			}

			existing_shipping_charge = self.get("taxes", filters=shipping_charge)
			if existing_shipping_charge:
				# take the last record found
				existing_shipping_charge[-1].rate = shipping_amount
			else:
				shipping_charge["rate"] = shipping_amount
				shipping_charge["description"] = shipping_rule.label
				self.append("taxes", shipping_charge)

			self.calculate_taxes_and_totals()

	def remove_shipping_charge(self):
		if self.shipping_rule:
			shipping_rule = frappe.get_doc("Shipping Rule", self.shipping_rule)
			existing_shipping_charge = self.get("taxes", {
				"doctype": "Sales Taxes and Charges",
				"charge_type": "Actual",
				"account_head": shipping_rule.account,
				"cost_center": shipping_rule.cost_center
			})
			if existing_shipping_charge:
				self.get("taxes").remove(existing_shipping_charge[-1])
				self.calculate_taxes_and_totals()

	def set_total_in_words(self):
		from frappe.utils import money_in_words
		company_currency = get_company_currency(self.company)

		disable_rounded_total = cint(frappe.db.get_value("Global Defaults", None,
			"disable_rounded_total"))

		if self.meta.get_field("base_in_words"):
			self.base_in_words = money_in_words(disable_rounded_total and
				self.base_grand_total or self.base_rounded_total, company_currency)
		if self.meta.get_field("in_words"):
			self.in_words = money_in_words(disable_rounded_total and
				self.grand_total or self.rounded_total, self.currency)

	def calculate_commission(self):
		if self.meta.get_field("commission_rate"):
			self.round_floats_in(self, ["base_net_total", "commission_rate"])
			if self.commission_rate > 100.0:
				throw(_("Commission rate cannot be greater than 100"))

			self.total_commission = flt(self.base_net_total * self.commission_rate / 100.0,
				self.precision("total_commission"))

	def calculate_contribution(self):
		if not self.meta.get_field("sales_team"):
			return

		total = 0.0
		sales_team = self.get("sales_team")
		for sales_person in sales_team:
			self.round_floats_in(sales_person)

			sales_person.allocated_amount = flt(
				self.base_net_total * sales_person.allocated_percentage / 100.0,
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

	def validate_max_discount(self):
		for d in self.get("items"):
			discount = flt(frappe.db.get_value("Item", d.item_code, "max_discount"))

			if discount and flt(d.discount_percentage) > discount:
				frappe.throw(_("Maxiumm discount for Item {0} is {1}%").format(d.item_code, discount))

	def get_item_list(self):
		il = []
		for d in self.get("items"):
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
					d.against_sales_order, d.so_detail)
				so_qty, reserved_warehouse = self.get_so_qty_and_warehouse(d.so_detail)

				if already_delivered_qty + d.qty > so_qty:
					reserved_qty_for_main_item = -(so_qty - already_delivered_qty)
				else:
					reserved_qty_for_main_item = -flt(d.qty)

			if self.has_sales_bom(d.item_code):
				for p in self.get("packed_items"):
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
                                        'stock_uom': d.stock_uom,
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
			where so_detail = %s and docstatus = 1
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
		for d in self.get("items"):
			if d.get(ref_fieldname):
				status = frappe.db.get_value("Sales Order", d.get(ref_fieldname), "status")
				if status == "Stopped":
					frappe.throw(_("Sales Order {0} is stopped").format(d.get(ref_fieldname)))

def check_active_sales_items(obj):
	for d in obj.get("items"):
		if d.item_code:
			item = frappe.db.sql("""select docstatus, is_sales_item,
				is_service_item, income_account from tabItem where name = %s""",
				d.item_code, as_dict=True)[0]
			if item.is_sales_item == 'No' and item.is_service_item == 'No':
				frappe.throw(_("Item {0} must be Sales or Service Item in {1}").format(d.item_code, d.idx))
			if getattr(d, "income_account", None) and not item.income_account:
				frappe.db.set_value("Item", d.item_code, "income_account",
					d.income_account)
