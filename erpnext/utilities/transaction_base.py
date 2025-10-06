# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
import frappe.share
from frappe import _
from frappe.utils import cint, flt, get_time, now_datetime

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.controllers.status_updater import StatusUpdater
from erpnext.stock.get_item_details import get_item_details
from erpnext.stock.utils import get_incoming_rate


class UOMMustBeIntegerError(frappe.ValidationError):
	pass


class TransactionBase(StatusUpdater):
	def validate_posting_time(self):
		# set Edit Posting Date and Time to 1 while data import
		if frappe.flags.in_import and self.posting_date:
			self.set_posting_time = 1

		if not getattr(self, "set_posting_time", None):
			now = now_datetime()
			self.posting_date = now.strftime("%Y-%m-%d")
			self.posting_time = now.strftime("%H:%M:%S.%f")
		elif self.posting_time:
			try:
				get_time(self.posting_time)
			except ValueError:
				frappe.throw(_("Invalid Posting Time"))

	def validate_uom_is_integer(self, uom_field, qty_fields, child_dt=None):
		validate_uom_is_integer(self, uom_field, qty_fields, child_dt)

	def validate_with_previous_doc(self, ref):
		self.exclude_fields = ["conversion_factor", "uom"] if self.get("is_return") else []

		for key, val in ref.items():
			is_child = val.get("is_child_table")
			ref_doc = {}
			item_ref_dn = []
			for d in self.get_all_children(self.doctype + " Item"):
				ref_dn = d.get(val["ref_dn_field"])
				if ref_dn:
					if is_child:
						self.compare_values({key: [ref_dn]}, val["compare_fields"], d)
						if ref_dn not in item_ref_dn:
							item_ref_dn.append(ref_dn)
						elif not val.get("allow_duplicate_prev_row_id"):
							frappe.throw(_("Duplicate row {0} with same {1}").format(d.idx, key))
					elif ref_dn:
						ref_doc.setdefault(key, [])
						if ref_dn not in ref_doc[key]:
							ref_doc[key].append(ref_dn)
			if ref_doc:
				self.compare_values(ref_doc, val["compare_fields"])

	def compare_values(self, ref_doc, fields, doc=None):
		for reference_doctype, ref_dn_list in ref_doc.items():
			prev_doc_detail_map = self.get_prev_doc_reference_details(ref_dn_list, reference_doctype, fields)
			for reference_name in ref_dn_list:
				prevdoc_values = prev_doc_detail_map.get(reference_name)
				if not prevdoc_values:
					frappe.throw(_("Invalid reference {0} {1}").format(reference_doctype, reference_name))

				for field, condition in fields:
					if prevdoc_values[field] not in [None, ""] and field not in self.exclude_fields:
						self.validate_value(field, condition, prevdoc_values[field], doc)

	def get_prev_doc_reference_details(self, reference_names, reference_doctype, fields):
		prev_doc_detail_map = {}
		details = frappe.get_all(
			reference_doctype,
			filters={"name": ("in", reference_names)},
			fields=["name"] + [d[0] for d in fields],
		)

		for d in details:
			prev_doc_detail_map.setdefault(d.name, d)

		return prev_doc_detail_map

	def validate_rate_with_reference_doc(self, ref_details):
		if self.get("is_internal_supplier"):
			return

		buying_doctypes = ["Purchase Order", "Purchase Invoice", "Purchase Receipt"]

		if self.doctype in buying_doctypes:
			action, role_allowed_to_override = frappe.get_cached_value(
				"Buying Settings", "None", ["maintain_same_rate_action", "role_to_override_stop_action"]
			)
		else:
			action, role_allowed_to_override = frappe.get_cached_value(
				"Selling Settings", "None", ["maintain_same_rate_action", "role_to_override_stop_action"]
			)

		stop_actions = []
		for ref_dt, ref_dn_field, ref_link_field in ref_details:
			reference_names = [d.get(ref_link_field) for d in self.get("items") if d.get(ref_link_field)]
			reference_details = self.get_reference_details(reference_names, ref_dt + " Item")
			for d in self.get("items"):
				if d.get(ref_link_field):
					ref_rate = reference_details.get(d.get(ref_link_field))

					if abs(flt(d.rate - ref_rate, d.precision("rate"))) >= 0.01:
						if action == "Stop":
							if role_allowed_to_override not in frappe.get_roles():
								stop_actions.append(
									_("Row #{0}: Rate must be same as {1}: {2} ({3} / {4})").format(
										d.idx, ref_dt, d.get(ref_dn_field), d.rate, ref_rate
									)
								)
						else:
							frappe.msgprint(
								_("Row #{0}: Rate must be same as {1}: {2} ({3} / {4})").format(
									d.idx, ref_dt, d.get(ref_dn_field), d.rate, ref_rate
								),
								title=_("Warning"),
								indicator="orange",
							)
		if stop_actions:
			frappe.throw(stop_actions, as_list=True)

	def get_reference_details(self, reference_names, reference_doctype):
		return frappe._dict(
			frappe.get_all(
				reference_doctype,
				filters={"name": ("in", reference_names)},
				fields=["name", "rate"],
				as_list=1,
			)
		)

	def get_link_filters(self, for_doctype):
		if hasattr(self, "prev_link_mapper") and self.prev_link_mapper.get(for_doctype):
			fieldname = self.prev_link_mapper[for_doctype]["fieldname"]

			values = filter(None, tuple(item.as_dict()[fieldname] for item in self.items))

			if values:
				ret = {for_doctype: {"filters": [[for_doctype, "name", "in", values]]}}
			else:
				ret = None
		else:
			ret = None

		return ret

	def reset_default_field_value(self, default_field: str, child_table: str, child_table_field: str):
		"""Reset "Set default X" fields on forms to avoid confusion.

		example:
		        doc = {
		                "set_from_warehouse": "Warehouse A",
		                "items": [{"from_warehouse": "warehouse B"}, {"from_warehouse": "warehouse A"}],
		        }
		        Since this has dissimilar values in child table, the default field will be erased.

		        doc.reset_default_field_value("set_from_warehouse", "items", "from_warehouse")
		"""
		child_table_values = set()

		for row in self.get(child_table):
			if default_field == "set_warehouse" and row.get("delivered_by_supplier"):
				continue

			child_table_values.add(row.get(child_table_field))

		if len(child_table_values) > 1:
			self.set(default_field, None)

	def validate_currency_for_receivable_payable_and_advance_account(self):
		if self.doctype in ["Customer", "Supplier"]:
			account_type = "Receivable" if self.doctype == "Customer" else "Payable"
			for x in self.accounts:
				company_default_currency = frappe.get_cached_value("Company", x.company, "default_currency")
				receivable_payable_account_currency = None
				advance_account_currency = None

				if x.account:
					receivable_payable_account_currency = frappe.get_cached_value(
						"Account", x.account, "account_currency"
					)

				if x.advance_account:
					advance_account_currency = frappe.get_cached_value(
						"Account", x.advance_account, "account_currency"
					)
				if receivable_payable_account_currency and (
					receivable_payable_account_currency != self.default_currency
					and receivable_payable_account_currency != company_default_currency
				):
					frappe.throw(
						_(
							"{0} Account: {1} ({2}) must be in either customer billing currency: {3} or Company default currency: {4}"
						).format(
							account_type,
							frappe.bold(x.account),
							frappe.bold(receivable_payable_account_currency),
							frappe.bold(self.default_currency),
							frappe.bold(company_default_currency),
						)
					)

				if advance_account_currency and (
					advance_account_currency != self.default_currency
					and advance_account_currency != company_default_currency
				):
					frappe.throw(
						_(
							"Advance Account: {0} must be in either customer billing currency: {1} or Company default currency: {2}"
						).format(
							frappe.bold(x.advance_account),
							frappe.bold(self.default_currency),
							frappe.bold(company_default_currency),
						)
					)

				if (
					receivable_payable_account_currency
					and advance_account_currency
					and receivable_payable_account_currency != advance_account_currency
				):
					frappe.throw(
						_(
							"Both {0} Account: {1} and Advance Account: {2} must be of same currency for company: {3}"
						).format(
							account_type,
							frappe.bold(x.account),
							frappe.bold(x.advance_account),
							frappe.bold(x.company),
						)
					)

	def fetch_item_details(self, item: dict) -> dict:
		return get_item_details(
			frappe._dict(
				{
					"item_code": item.get("item_code"),
					"barcode": item.get("barcode"),
					"serial_no": item.get("serial_no"),
					"batch_no": item.get("batch_no"),
					"set_warehouse": self.get("set_warehouse"),
					"warehouse": item.get("warehouse"),
					"customer": self.get("customer") or self.get("party_name"),
					"quotation_to": self.get("quotation_to"),
					"supplier": self.get("supplier"),
					"currency": self.get("currency"),
					"is_internal_supplier": self.get("is_internal_supplier"),
					"is_internal_customer": self.get("is_internal_customer"),
					"update_stock": self.update_stock
					if self.doctype in ["Purchase Invoice", "Sales Invoice"]
					else False,
					"conversion_rate": self.get("conversion_rate"),
					"price_list": self.get("selling_price_list") or self.get("buying_price_list"),
					"price_list_currency": self.get("price_list_currency"),
					"plc_conversion_rate": self.get("plc_conversion_rate"),
					"company": self.get("company"),
					"order_type": self.get("order_type"),
					"is_pos": cint(self.get("is_pos")),
					"is_return": cint(self.get("is_return)")),
					"is_subcontracted": self.get("is_subcontracted"),
					"ignore_pricing_rule": self.get("ignore_pricing_rule"),
					"doctype": self.get("doctype"),
					"name": self.get("name"),
					"project": item.get("project") or self.get("project"),
					"qty": item.get("qty") or 1,
					"net_rate": item.get("rate"),
					"base_net_rate": item.get("base_net_rate"),
					"stock_qty": item.get("stock_qty"),
					"conversion_factor": item.get("conversion_factor"),
					"weight_per_unit": item.get("weight_per_unit"),
					"uom": item.get("uom"),
					"weight_uom": item.get("weight_uom"),
					"manufacturer": item.get("manufacturer"),
					"stock_uom": item.get("stock_uom"),
					"pos_profile": self.get("pos_profile") if cint(self.get("is_pos")) else "",
					"cost_center": item.get("cost_center"),
					"tax_category": self.get("tax_category"),
					"item_tax_template": item.get("item_tax_template"),
					"child_doctype": item.get("doctype"),
					"child_docname": item.get("name"),
					"is_old_subcontracting_flow": self.get("is_old_subcontracting_flow"),
				}
			)
		)

	@frappe.whitelist()
	def process_item_selection(self, item_idx):
		# Server side 'item' doc. Update this to reflect in UI
		item_obj = self.get("items", {"idx": item_idx})[0]

		# 'item_details' has latest item related values
		item_details = self.fetch_item_details(item_obj)

		self.set_fetched_values(item_obj, item_details)

		if self.doctype == "Request for Quotation":
			return

		self.set_item_rate_and_discounts(item_obj, item_details)
		self.add_taxes_from_item_template(item_obj, item_details)
		self.add_free_item(item_obj, item_details)
		self.handle_internal_parties(item_obj, item_details)
		self.conversion_factor(item_obj, item_details)
		self.calculate_taxes_and_totals()

	def set_fetched_values(self, item_obj: object, item_details: dict) -> None:
		for k, v in item_details.items():
			if hasattr(item_obj, k):
				setattr(item_obj, k, v)

	def handle_internal_parties(self, item_obj: object, item_details: dict) -> None:
		fetch_valuation_rate_for_internal_transaction = cint(
			frappe.get_single_value("Accounts Settings", "fetch_valuation_rate_for_internal_transaction")
		)
		if (
			self.get("is_internal_customer") or self.get("is_internal_supplier")
		) and fetch_valuation_rate_for_internal_transaction:
			args = frappe._dict(
				{
					"item_code": item_obj.item_code,
					"warehouse": item_obj.from_warehouse
					if self.doctype in ["Purchase Receipt", "Purchase Invoice"]
					else item_obj.warehouse,
					"qty": item_obj.qty * item_obj.conversion_factor,
					"voucher_type": self.doctype,
					"company": self.company,
				}
			)

			if self.doctype in ["Purchase Order", "Sales Order"]:
				args.update(
					{
						"posting_date": self.transaction_date,
					}
				)
			else:
				args.update(
					{
						"posting_date": self.posting_date,
						"posting_time": self.posting_time,
						"serial_no": item_obj.serial_no,
						"batch_no": item_obj.batch_no,
						"allow_zero_valuation_rate": item_obj.allow_zero_valuation_rate,
					}
				)

			rate = get_incoming_rate(args=args)
			item_obj.rate = rate * item_obj.conversion_factor
		else:
			self.set_rate_based_on_price_list(item_obj, item_details)

	def add_taxes_from_item_template(self, item_obj: object, item_details: dict) -> None:
		if item_details.item_tax_rate and frappe.get_single_value(
			"Accounts Settings", "add_taxes_from_item_tax_template"
		):
			item_tax_template = frappe.json.loads(item_details.item_tax_rate)
			for tax_head, _rate in item_tax_template.items():
				found = [x for x in self.taxes if x.account_head == tax_head]
				if not found:
					self.append("taxes", {"charge_type": "On Net Total", "account_head": tax_head, "rate": 0})

	def set_rate_based_on_price_list(self, item_obj: object, item_details: dict) -> None:
		if item_obj.price_list_rate and item_obj.discount_percentage:
			item_obj.rate = flt(
				item_obj.price_list_rate * (1 - item_obj.discount_percentage / 100.0),
				item_obj.precision("rate"),
			)

	def copy_from_first_row(self, row, fields):
		if self.items and row:
			fields.extend([x.get("fieldname") for x in get_dimensions(True)[0]])
			first_row = self.items[0]
			[setattr(row, k, first_row.get(k)) for k in fields if hasattr(first_row, k)]

	def add_free_item(self, item_obj: object, item_details: dict) -> None:
		free_items = item_details.get("free_item_data")
		if free_items and len(free_items):
			existing_free_items = [x for x in self.items if x.is_free_item]
			for free_item in free_items:
				_matches = [
					x
					for x in existing_free_items
					if x.item_code == free_item.get("item_code")
					and x.pricing_rules == free_item.get("pricing_rules")
				]
				if _matches:
					row_to_modify = _matches[0]
				else:
					row_to_modify = self.append("items")

				for k, _v in free_item.items():
					setattr(row_to_modify, k, free_item.get(k))

				self.copy_from_first_row(row_to_modify, ["expense_account", "income_account"])

	def conversion_factor(self, item_obj: object, item_details: dict) -> None:
		if frappe.get_meta(item_obj.doctype).has_field("stock_qty"):
			item_obj.stock_qty = flt(
				item_obj.qty * item_obj.conversion_factor, item_obj.precision("stock_qty")
			)

			if self.doctype != "Material Request":
				item_obj.total_weight = flt(item_obj.stock_qty * item_obj.weight_per_unit)
				self.calculate_net_weight()

			# TODO: for handling customization not to fetch price list rate
			if frappe.flags.dont_fetch_price_list_rate:
				return

			if not frappe.flags.dont_fetch_price_list_rate and frappe.get_meta(self.doctype).has_field(
				"price_list_currency"
			):
				self._apply_price_list(item_obj, True)
			self.calculate_stock_uom_rate(item_obj)

	def calculate_stock_uom_rate(self, item_obj: object) -> None:
		if item_obj.rate:
			item_obj.stock_uom_rate = flt(item_obj.rate) / flt(item_obj.conversion_factor)

	def set_item_rate_and_discounts(self, item_obj: object, item_details: dict) -> None:
		effective_item_rate = item_details.price_list_rate
		item_rate = item_details.rate

		# Field order precedance
		# blanket_order_rate -> margin_type -> discount_percentage -> discount_amount
		if item_obj.parenttype in ["Sales Order", "Quotation"] and item_obj.blanket_order_rate:
			effective_item_rate = item_obj.blanket_order_rate

		if item_obj.margin_type == "Percentage":
			item_obj.rate_with_margin = flt(effective_item_rate) + flt(effective_item_rate) * (
				flt(item_obj.margin_rate_or_amount) / 100
			)
		else:
			item_obj.rate_with_margin = flt(effective_item_rate) + flt(item_obj.margin_rate_or_amount)

		item_obj.base_rate_with_margin = flt(item_obj.rate_with_margin) * flt(self.conversion_rate)
		item_rate = flt(item_obj.rate_with_margin, item_obj.precision("rate"))

		if item_obj.discount_percentage and not item_obj.discount_amount:
			item_obj.discount_amount = (
				flt(item_obj.rate_with_margin) * flt(item_obj.discount_percentage) / 100
			)

		if item_obj.discount_amount and item_obj.discount_amount > 0:
			item_rate = flt(
				(item_obj.rate_with_margin) - (item_obj.discount_amount), item_obj.precision("rate")
			)
			item_obj.discount_percentage = (
				100 * flt(item_obj.discount_amount) / flt(item_obj.rate_with_margin)
			)

		item_obj.rate = item_rate

	def calculate_net_weight(self):
		self.total_net_weight = sum([x.get("total_weight") or 0 for x in self.items])
		self.apply_shipping_rule()

	def _apply_price_list(self, item_obj: object, reset_plc_conversion: bool) -> None:
		if self.doctype == "Material Request":
			return

		if not reset_plc_conversion:
			self.plc_conversion_rate = ""

		if not self.items or not (item_obj.get("selling_price_list") or item_obj.get("buying_price_list")):
			return

		if self.get("in_apply_price_list"):
			return

		self.in_apply_price_list = True

		from erpnext.stock.get_item_details import apply_price_list

		args = {
			"items": [x.as_dict() for x in self.items],
			"customer": self.customer or self.party_name,
			"quotation_to": self.quotation_to,
			"customer_group": self.customer_group,
			"territory": self.territory,
			"supplier": self.supplier,
			"supplier_group": self.supplier_group,
			"currency": self.currency,
			"conversion_rate": self.conversion_rate,
			"price_list": self.selling_price_list or self.buying_price_list,
			"price_list_currency": self.price_list_currency,
			"plc_conversion_rate": self.plc_conversion_rate,
			"company": self.company,
			"transaction_date": self.transaction_date or self.posting_date,
			"campaign": self.campaign,
			"sales_partner": self.sales_partner,
			"ignore_pricing_rule": self.ignore_pricing_rule,
			"doctype": self.doctype,
			"name": self.name,
			"is_return": self.is_return,
			"update_stock": self.update_stock if self.doctype in ["Sales Invoice", "Purchase Invoice"] else 0,
			"conversion_factor": self.conversion_factor,
			"pos_profile": self.pos_profile if self.doctype == "Sales Invoice" else "",
			"coupon_code": self.coupon_code,
			"is_internal_supplier": self.is_internal_supplier,
			"is_internal_customer": self.is_internal_customer,
		}
		# TODO: test method call impact on document
		apply_price_list(cts=args, as_doc=True, doc=self)


def delete_events(ref_type, ref_name):
	events = (
		frappe.db.sql_list(
			""" SELECT
			distinct `tabEvent`.name
		from
			`tabEvent`, `tabEvent Participants`
		where
			`tabEvent`.name = `tabEvent Participants`.parent
			and `tabEvent Participants`.reference_doctype = %s
			and `tabEvent Participants`.reference_docname = %s
		""",
			(ref_type, ref_name),
		)
		or []
	)

	if events:
		frappe.delete_doc("Event", events, for_reload=True)


def validate_uom_is_integer(doc, uom_field, qty_fields, child_dt=None):
	if isinstance(qty_fields, str):
		qty_fields = [qty_fields]

	distinct_uoms = tuple(set(uom for uom in (d.get(uom_field) for d in doc.get_all_children()) if uom))
	integer_uoms = set(
		d[0]
		for d in frappe.db.get_values(
			"UOM", (("name", "in", distinct_uoms), ("must_be_whole_number", "=", 1)), cache=True
		)
	)

	if not integer_uoms:
		return

	for d in doc.get_all_children(parenttype=child_dt):
		if d.get(uom_field) in integer_uoms:
			for f in qty_fields:
				qty = d.get(f)
				if qty:
					precision = d.precision(f)
					if abs(cint(qty) - flt(qty, precision)) > 0.0000001:
						frappe.throw(
							_(
								"Row {1}: Quantity ({0}) cannot be a fraction. To allow this, disable '{2}' in UOM {3}."
							).format(
								flt(qty, precision),
								d.idx,
								frappe.bold(_("Must be Whole Number")),
								frappe.bold(d.get(uom_field)),
							),
							UOMMustBeIntegerError,
						)
