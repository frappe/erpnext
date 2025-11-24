# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, bold, throw
from frappe.utils import cint, flt, get_link_to_form, nowtime

from erpnext.accounts.party import render_address
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from erpnext.controllers.sales_and_purchase_return import get_rate_for_return
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.doctype.item.item import set_item_default
from erpnext.stock.get_item_details import get_bin_details, get_conversion_factor
from erpnext.stock.utils import get_combine_datetime, get_incoming_rate, get_valuation_method


class SellingController(StockController):
	def __setup__(self):
		self.flags.ignore_permlevel_for_fields = ["selling_price_list", "price_list_currency"]

	def onload(self):
		super().onload()
		if (
			self.doctype in ("Sales Order", "Delivery Note", "Sales Invoice", "Quotation")
			and self.docstatus.is_draft()
			and not hasattr(self, "_action")
		):
			for item in self.get("items") + (self.get("packed_items") or []):
				company = self.company

				item.update(
					get_bin_details(
						item.item_code, item.warehouse, company=company, include_child_warehouses=True
					)
				)

		if self.docstatus == 1 and self.doctype in ["Delivery Note", "Sales Invoice"]:
			self.set_onload(
				"allow_to_make_qc_after_submission",
				frappe.get_single_value(
					"Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery"
				),
			)

	def validate(self):
		super().validate()
		self.validate_items()
		if not (self.get("is_debit_note") or self.get("is_return")):
			self.validate_max_discount()
		self.validate_selling_price()
		self.set_qty_as_per_stock_uom()
		self.set_po_nos(for_validate=True)
		self.set_gross_profit()
		set_default_income_account_for_item(self)
		self.set_customer_address()
		self.validate_for_duplicate_items()
		self.validate_target_warehouse()
		self.validate_auto_repeat_subscription_dates()
		for table_field in ["items", "packed_items"]:
			if self.get(table_field):
				self.set_serial_and_batch_bundle(table_field)

	def validate_standalone_serial_nos_customer(self):
		if not self.is_return or self.return_against:
			return

		if self.doctype in ["Sales Invoice", "Delivery Note"]:
			bundle_ids = [d.serial_and_batch_bundle for d in self.get("items") if d.serial_and_batch_bundle]
			if not bundle_ids:
				return

			serial_nos = frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": ("in", bundle_ids), "serial_no": ("is", "set")},
				pluck="serial_no",
			)

			if not serial_nos:
				return

			if serial_nos := frappe.get_all(
				"Serial No",
				filters={"name": ("in", serial_nos), "customer": ("is", "set")},
				fields=["name", "customer"],
			):
				for sn in serial_nos:
					if sn.customer and sn.customer != self.customer:
						frappe.throw(
							_(
								"Serial No {0} is already assigned to customer {1}. Can only be returned against the customer {1}"
							).format(frappe.bold(sn.name), frappe.bold(sn.customer)),
							title=_("Serial No Already Assigned"),
						)

	def set_missing_values(self, for_validate=False):
		super().set_missing_values(for_validate)

		# set contact and address details for customer, if they are not mentioned
		self.set_missing_lead_customer_details(for_validate=for_validate)
		self.set_price_list_and_item_details(for_validate=for_validate)
		self.set_company_contact_person()

	def set_missing_lead_customer_details(self, for_validate=False):
		customer, lead = None, None
		if getattr(self, "customer", None):
			customer = self.customer
		elif self.doctype == "Opportunity" and self.party_name:
			if self.opportunity_from == "Customer":
				customer = self.party_name
			else:
				lead = self.party_name
		elif self.doctype == "Quotation" and self.party_name:
			if self.quotation_to == "Customer":
				customer = self.party_name
			elif self.quotation_to == "Lead":
				lead = self.party_name

		if customer:
			from erpnext.accounts.party import _get_party_details

			party_details = _get_party_details(
				customer,
				ignore_permissions=self.flags.ignore_permissions,
				doctype=self.doctype,
				company=self.company,
				posting_date=self.get("posting_date"),
				fetch_payment_terms_template=self.has_value_changed("company"),
				party_address=self.customer_address,
				shipping_address=self.shipping_address_name,
				company_address=self.get("company_address"),
			)
			if not self.meta.get_field("sales_team"):
				party_details.pop("sales_team")
			self.update_if_missing(party_details)

		elif lead:
			from erpnext.crm.doctype.lead.lead import get_lead_details

			self.update_if_missing(
				get_lead_details(
					lead,
					posting_date=self.get("transaction_date") or self.get("posting_date"),
					company=self.company,
					doctype=self.doctype,
				)
			)

		if self.get("taxes_and_charges") and not self.get("taxes") and not for_validate:
			taxes = get_taxes_and_charges("Sales Taxes and Charges Template", self.taxes_and_charges)
			for tax in taxes:
				self.append("taxes", tax)

	def set_price_list_and_item_details(self, for_validate=False):
		self.set_price_list_currency("Selling")
		self.set_missing_item_details(for_validate=for_validate)

	def set_company_contact_person(self):
		"""Set the Company's Default Sales Contact as Company Contact Person."""
		if self.company and self.meta.has_field("company_contact_person") and not self.company_contact_person:
			self.company_contact_person = frappe.get_cached_value(
				"Company", self.company, "default_sales_contact"
			)

	def remove_shipping_charge(self):
		if self.shipping_rule:
			shipping_rule = frappe.get_last_doc("Shipping Rule", self.shipping_rule)
			existing_shipping_charge = self.get(
				"taxes",
				{
					"doctype": "Sales Taxes and Charges",
					"charge_type": "Actual",
					"account_head": shipping_rule.account,
					"cost_center": shipping_rule.cost_center,
				},
			)
			if existing_shipping_charge:
				self.get("taxes").remove(existing_shipping_charge[-1])
				self.calculate_taxes_and_totals()

	def set_total_in_words(self):
		from frappe.utils import money_in_words

		if self.meta.get_field("base_in_words"):
			base_amount = abs(
				self.base_grand_total if self.is_rounded_total_disabled() else self.base_rounded_total
			)
			self.base_in_words = money_in_words(base_amount, self.company_currency)

		if self.meta.get_field("in_words"):
			amount = abs(self.grand_total if self.is_rounded_total_disabled() else self.rounded_total)
			self.in_words = money_in_words(amount, self.currency)

	def calculate_commission(self):
		if not self.meta.get_field("commission_rate"):
			return

		self.round_floats_in(self, ("amount_eligible_for_commission", "commission_rate"))

		if not (0 <= self.commission_rate <= 100.0):
			throw(
				"{} {}".format(
					_(self.meta.get_label("commission_rate")),
					_("must be between 0 and 100"),
				)
			)

		self.amount_eligible_for_commission = sum(
			item.base_net_amount for item in self.items if item.grant_commission
		)

		self.total_commission = flt(
			self.amount_eligible_for_commission * self.commission_rate / 100.0,
			self.precision("total_commission"),
		)

	def calculate_contribution(self):
		if not self.meta.get_field("sales_team"):
			return

		total = 0.0
		sales_team = self.get("sales_team")

		self.validate_sales_team(sales_team)

		for sales_person in sales_team:
			self.round_floats_in(sales_person)

			sales_person.allocated_amount = flt(
				flt(self.amount_eligible_for_commission) * sales_person.allocated_percentage / 100.0,
				self.precision("allocated_amount", sales_person),
			)

			if sales_person.commission_rate:
				sales_person.incentives = flt(
					sales_person.allocated_amount * flt(sales_person.commission_rate) / 100.0,
					self.precision("incentives", sales_person),
				)

			total += sales_person.allocated_percentage

		if sales_team and total != 100.0:
			throw(_("Total allocated percentage for sales team should be 100"))

	def validate_sales_team(self, sales_team):
		sales_persons = [d.sales_person for d in sales_team]

		if not sales_persons:
			return

		sales_person_status = frappe.db.get_all(
			"Sales Person", filters={"name": ["in", sales_persons]}, fields=["name", "enabled"]
		)

		for row in sales_person_status:
			if not row.enabled:
				frappe.throw(_("Sales Person <b>{0}</b> is disabled.").format(row.name))

	def validate_max_discount(self):
		for d in self.get("items"):
			if d.item_code:
				discount = flt(frappe.get_cached_value("Item", d.item_code, "max_discount"))

				if discount and flt(d.discount_percentage) > discount:
					frappe.throw(_("Maximum discount for Item {0} is {1}%").format(d.item_code, discount))

	def set_qty_as_per_stock_uom(self):
		allow_to_edit_stock_qty = frappe.get_single_value(
			"Stock Settings", "allow_to_edit_stock_uom_qty_for_sales"
		)

		for d in self.get("items"):
			if d.meta.get_field("stock_qty"):
				if not d.conversion_factor:
					frappe.throw(_("Row {0}: Conversion Factor is mandatory").format(d.idx))
				d.stock_qty = flt(d.qty) * flt(d.conversion_factor)
				if allow_to_edit_stock_qty:
					d.stock_qty = flt(d.stock_qty, d.precision("stock_qty"))

	def validate_selling_price(self):
		def throw_message(idx, item_name, rate, ref_rate_field):
			throw(
				_(
					"""Row #{0}: Selling rate for item {1} is lower than its {2}.
					Selling {3} should be atleast {4}.<br><br>Alternatively,
					you can disable selling price validation in {5} to bypass
					this validation."""
				).format(
					idx,
					bold(item_name),
					bold(ref_rate_field),
					bold("net rate"),
					bold(rate),
					get_link_to_form("Selling Settings", "Selling Settings"),
				),
				title=_("Invalid Selling Price"),
			)

		if self.get("is_return") or not frappe.get_single_value("Selling Settings", "validate_selling_price"):
			return

		is_internal_customer = self.get("is_internal_customer")
		valuation_rate_map = {}

		for item in self.items:
			if not item.item_code or item.is_free_item:
				continue

			last_purchase_rate, is_stock_item = frappe.get_cached_value(
				"Item", item.item_code, ("last_purchase_rate", "is_stock_item")
			)

			last_purchase_rate_in_sales_uom = last_purchase_rate * (item.conversion_factor or 1)

			if flt(item.base_net_rate) < flt(last_purchase_rate_in_sales_uom):
				throw_message(item.idx, item.item_name, last_purchase_rate_in_sales_uom, "last purchase rate")

			if is_internal_customer or not is_stock_item:
				continue

			valuation_rate_map[(item.item_code, item.warehouse)] = None

		if not valuation_rate_map:
			return

		or_conditions = (
			f"""(item_code = {frappe.db.escape(valuation_rate[0])}
			and warehouse = {frappe.db.escape(valuation_rate[1])})"""
			for valuation_rate in valuation_rate_map
		)

		valuation_rates = frappe.db.sql(
			f"""
			select
				item_code, warehouse, valuation_rate
			from
				`tabBin`
			where
				({" or ".join(or_conditions)})
				and valuation_rate > 0
		""",
			as_dict=True,
		)

		for rate in valuation_rates:
			valuation_rate_map[(rate.item_code, rate.warehouse)] = rate.valuation_rate

		for item in self.items:
			if not item.item_code or item.is_free_item:
				continue

			last_valuation_rate = valuation_rate_map.get((item.item_code, item.warehouse))

			if not last_valuation_rate:
				continue

			last_valuation_rate_in_sales_uom = last_valuation_rate * (item.conversion_factor or 1)

			if flt(item.base_net_rate) < flt(last_valuation_rate_in_sales_uom):
				throw_message(
					item.idx,
					item.item_name,
					last_valuation_rate_in_sales_uom,
					"valuation rate (Moving Average)",
				)

	def get_item_list(self):
		il = []
		for d in self.get("items"):
			if self.has_product_bundle(d.item_code):
				for p in self.get("packed_items"):
					if p.parent_detail_docname == d.name and p.parent_item == d.item_code:
						# the packing details table's qty is already multiplied with parent's qty
						il.append(
							frappe._dict(
								{
									"warehouse": p.warehouse or d.warehouse,
									"item_code": p.item_code,
									"qty": flt(p.qty),
									"serial_no": p.serial_no if self.docstatus == 2 else None,
									"batch_no": p.batch_no if self.docstatus == 2 else None,
									"uom": p.uom,
									"serial_and_batch_bundle": p.serial_and_batch_bundle
									or get_serial_and_batch_bundle(p, self, d),
									"name": d.name,
									"target_warehouse": p.target_warehouse,
									"company": self.company,
									"voucher_type": self.doctype,
									"allow_zero_valuation": d.allow_zero_valuation_rate,
									"sales_invoice_item": d.get("sales_invoice_item"),
									"dn_detail": d.get("dn_detail"),
									"incoming_rate": p.get("incoming_rate"),
									"item_row": p,
								}
							)
						)
			else:
				il.append(
					frappe._dict(
						{
							"warehouse": d.warehouse,
							"item_code": d.item_code,
							"qty": d.stock_qty,
							"serial_no": d.serial_no if self.docstatus == 2 else None,
							"batch_no": d.batch_no if self.docstatus == 2 else None,
							"uom": d.uom,
							"stock_uom": d.stock_uom,
							"conversion_factor": d.conversion_factor,
							"serial_and_batch_bundle": d.serial_and_batch_bundle,
							"name": d.name,
							"target_warehouse": d.target_warehouse,
							"company": self.company,
							"voucher_type": self.doctype,
							"allow_zero_valuation": d.allow_zero_valuation_rate,
							"sales_invoice_item": d.get("sales_invoice_item"),
							"dn_detail": d.get("dn_detail"),
							"incoming_rate": d.get("incoming_rate"),
							"item_row": d,
						}
					)
				)

		return il

	def has_product_bundle(self, item_code):
		product_bundle_items = getattr(self, "_product_bundle_items", None)
		if product_bundle_items is None:
			self._product_bundle_items = product_bundle_items = {}

		if item_code not in product_bundle_items:
			self._fetch_product_bundle_items(item_code)

		return product_bundle_items[item_code]

	def _fetch_product_bundle_items(self, item_code):
		product_bundle_items = self._product_bundle_items
		items_to_fetch = {row.item_code for row in self.items if row.item_code not in product_bundle_items}
		# fetch for requisite item_code even if it is not in items
		items_to_fetch.add(item_code)

		items_with_product_bundle = {
			row.new_item_code
			for row in frappe.get_all(
				"Product Bundle",
				filters={"new_item_code": ("in", items_to_fetch), "disabled": 0},
				fields="new_item_code",
			)
		}

		for item_code in items_to_fetch:
			product_bundle_items[item_code] = item_code in items_with_product_bundle

	def get_already_delivered_qty(self, current_docname, so, so_detail):
		delivered_via_dn = frappe.db.sql(
			"""select sum(qty) from `tabDelivery Note Item`
			where so_detail = %s and docstatus = 1
			and against_sales_order = %s
			and parent != %s""",
			(so_detail, so, current_docname),
		)

		delivered_via_si = frappe.db.sql(
			"""select sum(si_item.qty)
			from `tabSales Invoice Item` si_item, `tabSales Invoice` si
			where si_item.parent = si.name and si.update_stock = 1
			and si_item.so_detail = %s and si.docstatus = 1
			and si_item.sales_order = %s
			and si.name != %s""",
			(so_detail, so, current_docname),
		)

		total_delivered_qty = (flt(delivered_via_dn[0][0]) if delivered_via_dn else 0) + (
			flt(delivered_via_si[0][0]) if delivered_via_si else 0
		)

		return total_delivered_qty

	def get_so_qty_and_warehouse(self, so_detail):
		so_item = frappe.db.sql(
			"""select qty, warehouse from `tabSales Order Item`
			where name = %s and docstatus = 1""",
			so_detail,
			as_dict=1,
		)
		so_qty = so_item and flt(so_item[0]["qty"]) or 0.0
		so_warehouse = so_item and so_item[0]["warehouse"] or ""
		return so_qty, so_warehouse

	def check_sales_order_on_hold_or_close(self, ref_fieldname):
		for d in self.get("items"):
			if d.get(ref_fieldname):
				status = frappe.db.get_value("Sales Order", d.get(ref_fieldname), "status")
				if status in ("Closed", "On Hold") and not self.is_return:
					frappe.throw(_("Sales Order {0} is {1}").format(d.get(ref_fieldname), status))

	def update_reserved_qty(self):
		so_map = {}
		for d in self.get("items"):
			if d.so_detail:
				if self.doctype == "Delivery Note" and d.against_sales_order:
					so_map.setdefault(d.against_sales_order, []).append(d.so_detail)
				elif self.doctype == "Sales Invoice" and d.sales_order and self.update_stock:
					so_map.setdefault(d.sales_order, []).append(d.so_detail)

		for so, so_item_rows in so_map.items():
			if so and so_item_rows:
				sales_order = frappe.get_lazy_doc("Sales Order", so)

				if (sales_order.status == "Closed" and not self.is_return) or sales_order.status in [
					"Cancelled"
				]:
					frappe.throw(
						_("{0} {1} is cancelled or closed").format(_("Sales Order"), so),
						frappe.InvalidStatusError,
					)

				sales_order.update_reserved_qty(so_item_rows)

	def set_incoming_rate(self):
		if self.doctype not in ("Delivery Note", "Sales Invoice"):
			return

		allow_at_arms_length_price = frappe.get_cached_value(
			"Stock Settings", None, "allow_internal_transfer_at_arms_length_price"
		)
		items = self.get("items") + (self.get("packed_items") or [])
		for d in items:
			if not frappe.get_cached_value("Item", d.item_code, "is_stock_item"):
				continue

			item_details = frappe.get_cached_value(
				"Item", d.item_code, ["has_serial_no", "has_batch_no"], as_dict=1
			)

			if not self.get("return_against") or (
				get_valuation_method(d.item_code, self.company) == "Moving Average"
				and self.get("is_return")
				and not item_details.has_serial_no
				and not item_details.has_batch_no
			):
				# Get incoming rate based on original item cost based on valuation method
				qty = flt(d.get("stock_qty") or d.get("actual_qty") or d.get("qty"))

				if (
					not d.incoming_rate
					or self.is_internal_transfer()
					or (
						get_valuation_method(d.item_code, self.company) == "Moving Average"
						and self.get("is_return")
					)
				):
					d.incoming_rate = get_incoming_rate(
						{
							"item_code": d.item_code,
							"warehouse": d.warehouse,
							"posting_date": self.get("posting_date") or self.get("transaction_date"),
							"posting_time": self.get("posting_time") or nowtime(),
							"qty": qty if cint(self.get("is_return")) else (-1 * qty),
							"serial_and_batch_bundle": d.serial_and_batch_bundle,
							"company": self.company,
							"voucher_type": self.doctype,
							"voucher_no": self.name,
							"voucher_detail_no": d.name,
							"allow_zero_valuation": d.get("allow_zero_valuation"),
							"batch_no": d.batch_no,
							"serial_no": d.serial_no,
						},
						raise_error_if_no_rate=False,
					)

				if (
					not d.incoming_rate
					and self.get("return_against")
					and self.get("is_return")
					and get_valuation_method(d.item_code, self.company) == "Moving Average"
				):
					d.incoming_rate = get_rate_for_return(
						self.doctype, self.name, d.item_code, self.return_against, item_row=d
					)

				if (
					self.get("is_return")
					and not d.incoming_rate
					and not self.get("return_against")
					and not self.is_internal_transfer()
					and not d.get("allow_zero_valuation_rate")
				):
					d.incoming_rate = d.rate

				# For internal transfers use incoming rate as the valuation rate
				if self.is_internal_transfer():
					if self.doctype == "Delivery Note" or self.get("update_stock"):
						if d.doctype == "Packed Item":
							incoming_rate = flt(
								flt(d.incoming_rate, d.precision("incoming_rate")) * d.conversion_factor,
								d.precision("incoming_rate"),
							)
							if d.incoming_rate != incoming_rate:
								d.incoming_rate = incoming_rate
						else:
							if allow_at_arms_length_price:
								continue

							rate = flt(
								flt(d.incoming_rate, d.precision("incoming_rate")) * d.conversion_factor,
								d.precision("rate"),
							)
							if d.rate != rate:
								d.rate = rate
								frappe.msgprint(
									_(
										"Row {0}: Item rate has been updated as per valuation rate since its an internal stock transfer"
									).format(d.idx),
									alert=1,
								)

							d.discount_percentage = 0.0
							d.discount_amount = 0.0
							d.margin_rate_or_amount = 0.0

			elif self.get("return_against"):
				# Get incoming rate of return entry from reference document
				# based on original item cost as per valuation method
				d.incoming_rate = get_rate_for_return(
					self.doctype, self.name, d.item_code, self.return_against, item_row=d
				)

	def update_stock_ledger(self, allow_negative_stock=False):
		self.update_reserved_qty()

		sl_entries = []
		# Loop over items and packed items table
		for d in self.get_item_list():
			if frappe.get_cached_value("Item", d.item_code, "is_stock_item") == 1 and flt(d.qty):
				if flt(d.conversion_factor) == 0.0:
					d.conversion_factor = (
						get_conversion_factor(d.item_code, d.uom).get("conversion_factor") or 1.0
					)

				# On cancellation or return entry submission, make stock ledger entry for
				# target warehouse first, to update serial no values properly

				if d.warehouse and (
					(not cint(self.is_return) and self.docstatus == 1)
					or (cint(self.is_return) and self.docstatus == 2)
				):
					sl_entries.append(self.get_sle_for_source_warehouse(d))

				if d.target_warehouse:
					sl_entries.append(self.get_sle_for_target_warehouse(d))

				if d.warehouse and (
					(not cint(self.is_return) and self.docstatus == 2)
					or (cint(self.is_return) and self.docstatus == 1)
				):
					sl_entries.append(self.get_sle_for_source_warehouse(d))

		self.make_sl_entries(sl_entries, allow_negative_stock=allow_negative_stock)

	def get_sle_for_source_warehouse(self, item_row):
		serial_and_batch_bundle = (
			item_row.serial_and_batch_bundle
			if not self.is_internal_transfer() or self.docstatus == 1
			else None
		)

		if self.is_internal_transfer():
			if serial_and_batch_bundle and self.docstatus == 1 and self.is_return:
				serial_and_batch_bundle = self.make_package_for_transfer(
					serial_and_batch_bundle, item_row.warehouse, type_of_transaction="Inward"
				)
			elif not serial_and_batch_bundle:
				serial_and_batch_bundle = frappe.db.get_value(
					"Stock Ledger Entry",
					{"voucher_detail_no": item_row.name, "warehouse": item_row.warehouse},
					"serial_and_batch_bundle",
				)

		sle = self.get_sl_entries(
			item_row,
			{
				"actual_qty": -1 * flt(item_row.qty),
				"incoming_rate": item_row.incoming_rate,
				"recalculate_rate": cint(self.is_return),
				"serial_and_batch_bundle": serial_and_batch_bundle,
			},
		)
		if item_row.target_warehouse and not cint(self.is_return):
			sle.dependant_sle_voucher_detail_no = item_row.name

		return sle

	def get_sle_for_target_warehouse(self, item_row):
		sle = self.get_sl_entries(
			item_row, {"actual_qty": flt(item_row.qty), "warehouse": item_row.target_warehouse}
		)

		if self.docstatus == 1:
			if not cint(self.is_return):
				sle.update({"incoming_rate": item_row.incoming_rate, "recalculate_rate": 1})
			else:
				sle.update({"outgoing_rate": item_row.incoming_rate})
				if item_row.warehouse:
					sle.dependant_sle_voucher_detail_no = item_row.name

			if item_row.serial_and_batch_bundle and not cint(self.is_return):
				type_of_transaction = "Inward"
				if cint(self.is_return):
					type_of_transaction = "Outward"

				sle["serial_and_batch_bundle"] = self.make_package_for_transfer(
					item_row.serial_and_batch_bundle,
					item_row.target_warehouse,
					type_of_transaction=type_of_transaction,
				)

		return sle

	def set_po_nos(self, for_validate=False):
		if self.doctype == "Sales Invoice" and hasattr(self, "items"):
			if for_validate and self.po_no:
				return
			self.set_pos_for_sales_invoice()
		if self.doctype == "Delivery Note" and hasattr(self, "items"):
			if for_validate and self.po_no:
				return
			self.set_pos_for_delivery_note()

	def set_pos_for_sales_invoice(self):
		po_nos = []
		if self.po_no:
			po_nos.append(self.po_no)
		self.get_po_nos("Sales Order", "sales_order", po_nos)
		self.get_po_nos("Delivery Note", "delivery_note", po_nos)
		self.po_no = ", ".join(list(set(x.strip() for x in ",".join(po_nos).split(","))))

	def set_pos_for_delivery_note(self):
		po_nos = []
		if self.po_no:
			po_nos.append(self.po_no)
		self.get_po_nos("Sales Order", "against_sales_order", po_nos)
		self.get_po_nos("Sales Invoice", "against_sales_invoice", po_nos)
		self.po_no = ", ".join(list(set(x.strip() for x in ",".join(po_nos).split(","))))

	def get_po_nos(self, ref_doctype, ref_fieldname, po_nos):
		doc_list = list(set(d.get(ref_fieldname) for d in self.items if d.get(ref_fieldname)))
		if doc_list:
			po_nos += [
				d.po_no
				for d in frappe.get_all(ref_doctype, "po_no", filters={"name": ("in", doc_list)})
				if d.get("po_no")
			]

	def set_gross_profit(self):
		if self.doctype in ["Sales Order", "Quotation"]:
			for item in self.items:
				item.gross_profit = flt(
					((flt(item.stock_uom_rate) - flt(item.valuation_rate)) * item.stock_qty),
					self.precision("amount", item),
				)

	def set_customer_address(self):
		address_dict = {
			"customer_address": "address_display",
			"shipping_address_name": "shipping_address",
			"company_address": "company_address_display",
			"dispatch_address_name": "dispatch_address",
		}

		for address_field, address_display_field in address_dict.items():
			if self.get(address_field):
				self.set(
					address_display_field, render_address(self.get(address_field), check_permissions=False)
				)

	def validate_for_duplicate_items(self):
		check_list, chk_dupl_itm = [], []
		if cint(frappe.get_single_value("Selling Settings", "allow_multiple_items")):
			return
		if self.doctype == "Sales Invoice" and self.is_consolidated:
			return
		if self.doctype == "POS Invoice":
			return

		items = [item.item_code for item in self.get("items")]
		item_stock_map = frappe._dict(
			frappe.get_all(
				"Item",
				filters={"item_code": ["in", items]},
				fields=["item_code", "is_stock_item"],
				as_list=True,
			)
		)

		for d in self.get("items"):
			if self.doctype == "Sales Invoice":
				stock_items = [
					d.item_code,
					d.description,
					d.warehouse,
					d.sales_order or d.delivery_note,
					d.batch_no or "",
				]
				non_stock_items = [d.item_code, d.description, d.sales_order or d.delivery_note]
			elif self.doctype == "Delivery Note":
				stock_items = [
					d.item_code,
					d.description,
					d.warehouse,
					d.against_sales_order or d.against_sales_invoice,
					d.batch_no or "",
				]
				non_stock_items = [
					d.item_code,
					d.description,
					d.against_sales_order or d.against_sales_invoice,
				]
			elif self.doctype in ["Sales Order", "Quotation"]:
				stock_items = [d.item_code, d.description, d.warehouse, ""]
				non_stock_items = [d.item_code, d.description]

			duplicate_items_msg = _("Item {0} entered multiple times.").format(frappe.bold(d.item_code))
			duplicate_items_msg += "<br><br>"
			duplicate_items_msg += _("Please enable {} in {} to allow same item in multiple rows").format(
				frappe.bold(_("Allow Item to Be Added Multiple Times in a Transaction")),
				get_link_to_form("Selling Settings", "Selling Settings"),
			)
			if item_stock_map.get(d.item_code):
				if stock_items in check_list:
					frappe.throw(duplicate_items_msg)
				else:
					check_list.append(stock_items)
			else:
				if non_stock_items in chk_dupl_itm:
					frappe.throw(duplicate_items_msg)
				else:
					chk_dupl_itm.append(non_stock_items)

	def validate_target_warehouse(self):
		items = self.get("items") + (self.get("packed_items") or [])

		for d in items:
			if d.get("target_warehouse") and d.get("warehouse") == d.get("target_warehouse"):
				warehouse = frappe.bold(d.get("target_warehouse"))
				frappe.throw(
					_(
						"Row {0}: Delivery Warehouse ({1}) and Customer Warehouse ({2}) can not be same"
					).format(d.idx, warehouse, warehouse)
				)

		if not self.get("is_internal_customer") and any(d.get("target_warehouse") for d in items):
			msg = _("Target Warehouse is set for some items but the customer is not an internal customer.")
			msg += " " + _("This {} will be treated as material transfer.").format(_(self.doctype))
			frappe.msgprint(msg, title="Internal Transfer", alert=True)

	def validate_items(self):
		# validate items to see if they have is_sales_item enabled
		from erpnext.controllers.buying_controller import validate_item_type

		validate_item_type(self, "is_sales_item", "sales")

	def update_stock_reservation_entries(self) -> None:
		"""Updates Delivered Qty in Stock Reservation Entries."""

		# Don't update Delivered Qty on Return.
		if self.is_return:
			return

		so_field = "sales_order" if self.doctype == "Sales Invoice" else "against_sales_order"

		if self._action == "submit":
			for item in self.get("items"):
				# Skip if `Sales Order` or `Sales Order Item` reference is not set.
				if not item.get(so_field) or not item.so_detail:
					continue

				table = frappe.qb.DocType("Stock Reservation Entry")
				query = (
					frappe.qb.from_(table)
					.select(table.name)
					.where(
						(table.docstatus == 1)
						& (table.voucher_type == "Sales Order")
						& (table.voucher_no == item.get(so_field))
						& (table.voucher_detail_no == item.so_detail)
						& (table.warehouse == item.warehouse)
						& (table.delivered_qty < table.reserved_qty)
					)
					.orderby(table.creation)
				)
				sre_list = query.run(pluck="name")

				# Skip if no Stock Reservation Entries.
				if not sre_list:
					continue

				qty_to_deliver = item.stock_qty
				for sre in sre_list:
					if qty_to_deliver <= 0:
						break

					sre_doc = frappe.get_doc("Stock Reservation Entry", sre)

					qty_can_be_deliver = 0
					if sre_doc.reservation_based_on == "Serial and Batch":
						sbb = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
						if sre_doc.has_serial_no:
							delivered_serial_nos = [d.serial_no for d in sbb.entries]
							for entry in sre_doc.sb_entries:
								if entry.serial_no in delivered_serial_nos:
									entry.delivered_qty = 1  # Qty will always be 0 or 1 for Serial No.
									entry.db_update()
									qty_can_be_deliver += 1
									delivered_serial_nos.remove(entry.serial_no)
						else:
							delivered_batch_qty = {d.batch_no: -1 * d.qty for d in sbb.entries}
							for entry in sre_doc.sb_entries:
								if entry.batch_no in delivered_batch_qty:
									delivered_qty = min(
										(entry.qty - entry.delivered_qty), delivered_batch_qty[entry.batch_no]
									)
									entry.delivered_qty += delivered_qty
									entry.db_update()
									qty_can_be_deliver += delivered_qty
									delivered_batch_qty[entry.batch_no] -= delivered_qty
					else:
						# `Delivered Qty` should be less than or equal to `Reserved Qty`.
						qty_can_be_deliver = min(
							(sre_doc.reserved_qty - sre_doc.delivered_qty), qty_to_deliver
						)

					sre_doc.delivered_qty += qty_can_be_deliver
					sre_doc.db_update()

					# Update Stock Reservation Entry `Status` based on `Delivered Qty`.
					sre_doc.update_status()

					# Update Reserved Stock in Bin.
					sre_doc.update_reserved_stock_in_bin()

					qty_to_deliver -= qty_can_be_deliver

		if self._action == "cancel":
			for item in self.get("items"):
				# Skip if `Sales Order` or `Sales Order Item` reference is not set.
				if not item.get(so_field) or not item.so_detail:
					continue

				sre_list = frappe.db.get_all(
					"Stock Reservation Entry",
					{
						"docstatus": 1,
						"voucher_type": "Sales Order",
						"voucher_no": item.get(so_field),
						"voucher_detail_no": item.so_detail,
						"warehouse": item.warehouse,
						"status": ["in", ["Partially Delivered", "Delivered", "Partially Used", "Closed"]],
					},
					order_by="creation",
				)

				# Skip if no Stock Reservation Entries.
				if not sre_list:
					continue

				qty_to_undelivered = item.stock_qty
				for sre in sre_list:
					if qty_to_undelivered <= 0:
						break

					sre_doc = frappe.get_doc("Stock Reservation Entry", sre)

					qty_can_be_undelivered = 0
					if sre_doc.reservation_based_on == "Serial and Batch":
						sbb = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
						if sre_doc.has_serial_no:
							serial_nos_to_undelivered = [d.serial_no for d in sbb.entries]
							for entry in sre_doc.sb_entries:
								if entry.serial_no in serial_nos_to_undelivered:
									entry.delivered_qty = 0  # Qty will always be 0 or 1 for Serial No.
									entry.db_update()
									qty_can_be_undelivered += 1
									serial_nos_to_undelivered.remove(entry.serial_no)
						else:
							batch_qty_to_undelivered = {d.batch_no: -1 * d.qty for d in sbb.entries}
							for entry in sre_doc.sb_entries:
								if entry.batch_no in batch_qty_to_undelivered:
									undelivered_qty = min(
										entry.delivered_qty, batch_qty_to_undelivered[entry.batch_no]
									)
									entry.delivered_qty -= undelivered_qty
									entry.db_update()
									qty_can_be_undelivered += undelivered_qty
									batch_qty_to_undelivered[entry.batch_no] -= undelivered_qty
					else:
						# `Qty to Undelivered` should be less than or equal to `Delivered Qty`.
						qty_can_be_undelivered = min(sre_doc.delivered_qty, qty_to_undelivered)

					sre_doc.delivered_qty -= qty_can_be_undelivered
					sre_doc.db_update()

					# Update Stock Reservation Entry `Status` based on `Delivered Qty`.
					sre_doc.update_status()

					# Update Reserved Stock in Bin.
					sre_doc.update_reserved_stock_in_bin()

					qty_to_undelivered -= qty_can_be_undelivered


def set_default_income_account_for_item(obj):
	for d in obj.get("items"):
		if d.item_code:
			if getattr(d, "income_account", None):
				set_item_default(d.item_code, obj.company, "income_account", d.income_account)


def get_serial_and_batch_bundle(child, parent, delivery_note_child=None):
	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	if parent.get("is_return") and parent.get("packed_items"):
		return

	if child.get("use_serial_batch_fields"):
		return

	if not frappe.get_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward"):
		return

	item_details = frappe.db.get_value("Item", child.item_code, ["has_serial_no", "has_batch_no"], as_dict=1)

	if not item_details.has_serial_no and not item_details.has_batch_no:
		return

	sn_doc = SerialBatchCreation(
		{
			"item_code": child.item_code,
			"warehouse": child.warehouse,
			"voucher_type": parent.doctype,
			"voucher_no": parent.name if parent.docstatus < 2 else None,
			"voucher_detail_no": delivery_note_child.name if delivery_note_child else child.name,
			"posting_datetime": get_combine_datetime(parent.posting_date, parent.posting_time),
			"qty": child.qty,
			"type_of_transaction": "Outward" if child.qty > 0 and parent.docstatus < 2 else "Inward",
			"company": parent.company,
			"do_not_submit": "True",
		}
	)

	doc = sn_doc.make_serial_and_batch_bundle()
	child.db_set("serial_and_batch_bundle", doc.name)

	return doc.name
