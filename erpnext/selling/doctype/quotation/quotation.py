# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from collections import Counter

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.query_builder.functions import IfNull, NullIf
from frappe.utils import add_days, cint, flt, getdate, nowdate
from pypika import Case, Order
from pypika.terms import ExistsCriterion

from erpnext.controllers.selling_controller import SellingController

from .mapper import (
	get_ordered_items,
)

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class Quotation(SellingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.item_wise_tax_detail.item_wise_tax_detail import ItemWiseTaxDetail
		from erpnext.accounts.doctype.payment_schedule.payment_schedule import PaymentSchedule
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.sales_taxes_and_charges.sales_taxes_and_charges import (
			SalesTaxesandCharges,
		)
		from erpnext.crm.doctype.competitor_detail.competitor_detail import CompetitorDetail
		from erpnext.selling.doctype.quotation_item.quotation_item import QuotationItem
		from erpnext.setup.doctype.quotation_lost_reason_detail.quotation_lost_reason_detail import (
			QuotationLostReasonDetail,
		)
		from erpnext.stock.doctype.packed_item.packed_item import PackedItem

		additional_discount_percentage: DF.Float
		address_display: DF.TextEditor | None
		amended_from: DF.Link | None
		apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
		auto_repeat: DF.Link | None
		base_discount_amount: DF.Currency
		base_grand_total: DF.Currency
		base_in_words: DF.Data | None
		base_net_total: DF.Currency
		base_rounded_total: DF.Currency
		base_rounding_adjustment: DF.Currency
		base_total: DF.Currency
		base_total_taxes_and_charges: DF.Currency
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.TextEditor | None
		company_contact_person: DF.Link | None
		competitors: DF.TableMultiSelect[CompetitorDetail]
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		coupon_code: DF.Link | None
		currency: DF.Link
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		enq_det: DF.Text | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		has_unit_price_items: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		is_latest_revision: DF.Check
		item_wise_tax_details: DF.Table[ItemWiseTaxDetail]
		items: DF.Table[QuotationItem]
		language: DF.Link | None
		letter_head: DF.Link | None
		lost_reasons: DF.TableMultiSelect[QuotationLostReasonDetail]
		named_place: DF.Data | None
		naming_series: DF.Literal["SAL-QTN-.YYYY.-"]
		net_total: DF.Currency
		opportunity: DF.Link | None
		order_lost_reason: DF.SmallText | None
		order_type: DF.Literal["", "Sales", "Maintenance", "Shopping Cart"]
		original_quotation: DF.Link | None
		other_charges_calculation: DF.TextEditor | None
		packed_items: DF.Table[PackedItem]
		party_name: DF.DynamicLink | None
		payment_schedule: DF.Table[PaymentSchedule]
		payment_terms_template: DF.Link | None
		plc_conversion_rate: DF.Float
		price_list_currency: DF.Link
		pricing_rules: DF.Table[PricingRuleDetail]
		quotation_to: DF.Link
		quotation_version: DF.Int
		quote_revision_count: DF.Int
		referral_sales_partner: DF.Link | None
		revised_from: DF.Link | None
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		scan_barcode: DF.Data | None
		select_print_heading: DF.Link | None
		selling_price_list: DF.Link
		shipping_address: DF.TextEditor | None
		shipping_address_name: DF.Link | None
		shipping_rule: DF.Link | None
		status: DF.Literal[
			"Draft",
			"Open",
			"Replied",
			"Partially Ordered",
			"Ordered",
			"Lost",
			"Cancelled",
			"Expired",
			"Superseded",
		]
		supplier_quotation: DF.Link | None
		tax_category: DF.Link | None
		taxes: DF.Table[SalesTaxesandCharges]
		taxes_and_charges: DF.Link | None
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		territory: DF.Link | None
		title: DF.Data | None
		total: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		transaction_date: DF.Date
		utm_campaign: DF.Link | None
		utm_content: DF.Data | None
		utm_medium: DF.Link | None
		utm_source: DF.Link | None
		valid_till: DF.Date | None
	# end: auto-generated types

	revision_fields = ("original_quotation", "revised_from", "quotation_version")
	revision_commercial_fields = (
		"valid_till",
		"currency",
		"conversion_rate",
		"selling_price_list",
		"price_list_currency",
		"plc_conversion_rate",
		"apply_discount_on",
		"additional_discount_percentage",
		"discount_amount",
		"coupon_code",
		"tax_category",
		"taxes_and_charges",
		"shipping_rule",
		"incoterm",
		"named_place",
		"payment_terms_template",
		"tc_name",
		"terms",
	)
	revision_item_fields = (
		"item_code",
		"item_name",
		"description",
		"qty",
		"rate",
		"uom",
		"stock_uom",
		"conversion_factor",
		"price_list_rate",
		"discount_percentage",
		"discount_amount",
		"margin_type",
		"margin_rate_or_amount",
		"is_alternative",
		"is_free_item",
		"item_tax_template",
		"item_tax_rate",
		"product_bundle",
		"blanket_order",
		"blanket_order_rate",
	)
	revision_tax_fields = (
		"charge_type",
		"account_head",
		"description",
		"row_id",
		"rate",
		"included_in_print_rate",
		"cost_center",
	)
	revision_payment_fields = (
		"payment_term",
		"invoice_portion",
		"due_date",
		"mode_of_payment",
		"discount",
		"discount_type",
	)

	def save(self, *args, **kwargs):
		# Acquire the family lock before Frappe locks this particular version.
		self.lock_revision_family()
		return super().save(*args, **kwargs)

	def before_insert(self):
		self.initialize_revision()

	@frappe.whitelist(methods=["POST"])
	def make_revision(self) -> Document:
		source = frappe.get_doc("Quotation", self.name)
		self.validate_revision_source(source)
		frappe.has_permission("Quotation", "create", throw=True)

		draft = frappe.copy_doc(source, ignore_no_copy=False)
		draft.docstatus = 0
		draft.status = "Draft"
		draft.naming_series = source.naming_series
		draft.revised_from = source.name
		draft.original_quotation = source.original_quotation or source.name
		draft.is_latest_revision = 0
		draft.transaction_date = source.transaction_date
		for source_item, item in zip(source.items, draft.items, strict=True):
			item.prevdoc_doctype = source_item.prevdoc_doctype
			item.prevdoc_docname = source_item.prevdoc_docname
			item.ordered_qty = 0
			item.has_alternative_item = 0
		for child in draft.get_all_children():
			child.docstatus = 0
			child.parent = None
		return draft

	@frappe.whitelist()
	def get_revisions(self) -> list[str]:
		self.check_permission("read")
		original = self.original_quotation or self.name
		return frappe.get_list(
			"Quotation", or_filters={"name": original, "original_quotation": original}, pluck="name", limit=0
		)

	def before_update_after_submit(self):
		self.update_revision_fields()

	def before_cancel(self):
		self.validate_revision_cancellation()
		self.lost_reasons = []

	def get_status(self):
		status = super().get_status()
		if self.docstatus == 1 and status["status"] not in ("Lost", "Ordered", "Partially Ordered"):
			if not self.is_latest_revision:
				status["status"] = "Superseded"
			elif self.valid_till and getdate(self.valid_till) < getdate(nowdate()):
				status["status"] = "Expired"
		return status

	@staticmethod
	def validate_orderable(name: str) -> None:
		quotation = frappe.db.get_value(
			"Quotation", name, ["name", "is_latest_revision", "status"], as_dict=True
		)
		Quotation.check_orderable(quotation)

	@staticmethod
	def check_orderable(quotation) -> None:
		if quotation and (not quotation.is_latest_revision or quotation.status == "Superseded"):
			frappe.throw(
				_("Quotation {0} has been superseded. Use its current revision.").format(quotation.name)
			)
		if quotation and quotation.status == "Lost":
			frappe.throw(
				_("Quotation {0} is Lost and cannot be used for an order or invoice.").format(quotation.name)
			)

	@staticmethod
	def validate_quotation_references(doc: Document) -> None:
		if getattr(doc, "_action", None) == "update_after_submit" or doc.get("is_return"):
			return
		names = Quotation.lock_quotation_references(doc)
		if not names:
			return
		table = frappe.qb.DocType("Quotation")
		for quotation in (
			frappe.qb.from_(table)
			.select(table.name, table.is_latest_revision, table.status)
			.where(table.name.isin(names))
			.for_update()
			.run(as_dict=True)
		):
			Quotation.check_orderable(quotation)

	@staticmethod
	def lock_quotation_references(doc: Document) -> list[str]:
		fieldname = "quotation" if doc.doctype == "Sales Invoice" else "prevdoc_docname"
		names = sorted({row.get(fieldname) for row in doc.items if row.get(fieldname)})
		if not names:
			return []
		quotations = frappe.get_all(
			"Quotation", filters={"name": ["in", names]}, fields=["name", "original_quotation"]
		)
		# Lock before Frappe locks the order or invoice, matching revision submission.
		for original in sorted({row.original_quotation or row.name for row in quotations}):
			frappe.db.get_value("Quotation", original, "name", for_update=True)
		return names

	@staticmethod
	def lock_quotation(name: str) -> None:
		original = frappe.db.get_value("Quotation", name, "original_quotation") or name
		frappe.db.get_value("Quotation", original, "name", for_update=True)

	def set_indicator(self):
		if self.docstatus == 1:
			self.indicator_color = "blue"
			self.indicator_title = "Submitted"
		if self.valid_till and getdate(self.valid_till) < getdate(nowdate()):
			self.indicator_color = "gray"
			self.indicator_title = "Expired"

	def before_validate(self):
		self.set_has_unit_price_items()
		self.flags.allow_zero_qty = self.has_unit_price_items

	def validate(self):
		super().validate()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_valid_till()
		self.set_customer_name()
		if self.items:
			self.with_items = 1

		from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

		make_packing_list(self)
		self.update_revision_fields()
		self.set_status()

	def after_insert(self):
		self.carry_forward_communication()

	def before_submit(self):
		self.validate_revision_submission()
		self.set_has_alternative_item()

	def validate_valid_till(self):
		if self.valid_till and getdate(self.valid_till) < getdate(self.transaction_date):
			frappe.throw(_("Valid till date cannot be before transaction date"))

	def set_has_alternative_item(self):
		"""Mark 'Has Alternative Item' for rows."""
		if not any(row.is_alternative for row in self.get("items")):
			return

		items_with_alternatives = self.get_rows_with_alternatives()
		for row in self.get("items"):
			if not row.is_alternative and row.name in items_with_alternatives:
				row.has_alternative_item = 1

	def set_has_unit_price_items(self):
		"""
		If permitted in settings and any item has 0 qty, the SO has unit price items.
		"""
		if not frappe.get_single_value("Selling Settings", "allow_zero_qty_in_quotation"):
			return

		self.has_unit_price_items = any(
			not row.qty for row in self.get("items") if (row.item_code and not row.qty)
		)

	def get_ordered_status(self):
		ordered_items = get_ordered_items(self.name)

		if not ordered_items:
			return "Open"

		self._items = (
			self.get_valid_items()
			if any(row.is_alternative for row in self.get("items"))
			else self.get("items")
		)

		for row in self._items:
			if row.name not in ordered_items or row.stock_qty > ordered_items[row.name]:
				return "Partially Ordered"

		return "Ordered"

	def get_valid_items(self):
		"""
		Filters out items in an alternatives set that were not ordered.
		"""

		def is_in_sales_order(row):
			in_sales_order = bool(
				frappe.db.exists(
					"Sales Order Item",
					{"quotation_item": row.name, "item_code": row.item_code, "docstatus": 1},
				)
			)
			return in_sales_order

		def can_map(row) -> bool:
			if row.is_alternative or row.has_alternative_item:
				return is_in_sales_order(row)

			return True

		return list(filter(can_map, self.get("items")))

	def is_fully_ordered(self):
		return self.get_ordered_status() == "Ordered"

	def is_partially_ordered(self):
		return self.get_ordered_status() == "Partially Ordered"

	def update_lead(self):
		if self.quotation_to == "Lead" and self.party_name:
			frappe.get_doc("Lead", self.party_name).set_status(update=True)

	def set_customer_name(self):
		if self.party_name and self.quotation_to == "Customer":
			self.customer_name = frappe.db.get_value("Customer", self.party_name, "customer_name")
		elif self.party_name and self.quotation_to == "Lead":
			lead_name, company_name = frappe.db.get_value(
				"Lead", self.party_name, ["lead_name", "company_name"]
			)
			self.customer_name = company_name or lead_name
		elif self.party_name and self.quotation_to == "Prospect":
			self.customer_name = self.party_name
		elif self.party_name and self.quotation_to == "CRM Deal":
			self.customer_name = frappe.db.get_value("CRM Deal", self.party_name, "organization")

	def update_opportunity(self, status):
		for opportunity in set(d.prevdoc_docname for d in self.get("items")):
			if opportunity:
				self.update_opportunity_status(status, opportunity)

		if self.opportunity:
			self.update_opportunity_status(status)

	def update_opportunity_status(self, status, opportunity=None):
		if not opportunity:
			opportunity = self.opportunity

		opp = frappe.get_doc("Opportunity", opportunity)
		opp.set_status(status=status, update=True)

	@frappe.whitelist()
	def declare_enquiry_lost(
		self, lost_reasons_list: list, competitors: list, detailed_reason: str | None = None
	):
		self.check_permission("write")
		self.lock_quotation(self.name)
		if not frappe.db.get_value("Quotation", self.name, "is_latest_revision", for_update=True):
			frappe.throw(_("Only the current quotation can be marked as Lost."))

		if not (self.is_fully_ordered() or self.is_partially_ordered()):
			get_lost_reasons = frappe.get_list("Quotation Lost Reason", fields=["name"])
			lost_reasons_lst = [reason.get("name") for reason in get_lost_reasons]
			self.db_set("status", "Lost")

			if detailed_reason:
				self.db_set("order_lost_reason", detailed_reason)

			for reason in lost_reasons_list:
				if reason.get("lost_reason") in lost_reasons_lst:
					self.append("lost_reasons", reason)
				else:
					frappe.throw(
						_("Invalid lost reason {0}, please create a new lost reason").format(
							frappe.bold(reason.get("lost_reason"))
						)
					)

			for competitor in competitors:
				self.append("competitors", competitor)

			self.update_opportunity("Lost")
			self.update_lead()
			self.save()

		else:
			frappe.throw(_("Cannot set as Lost as Sales Order is made."))

	def on_submit(self):
		# Check for Approving Authority
		frappe.get_cached_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total, self
		)
		self.sync_revision_status()

		# update enquiry status
		self.update_opportunity("Quotation")
		self.update_lead()

	def on_cancel(self):
		super().on_cancel()

		# update enquiry status
		self.set_status(update=True)
		self.sync_revision_status()
		self.update_opportunity("Open")
		self.update_lead()

	def carry_forward_communication(self):
		from erpnext.crm.utils import copy_comments, link_communications

		if not (
			self.opportunity
			and frappe.get_single_value("CRM Settings", "carry_forward_communication_and_comments")
		):
			return

		copy_comments("Opportunity", self.opportunity, self)
		link_communications("Opportunity", self.opportunity, self)

	def print_other_charges(self, docname):
		print_lst = []
		for d in self.get("taxes"):
			lst1 = []
			lst1.append(d.description)
			lst1.append(d.total)
			print_lst.append(lst1)
		return print_lst

	def on_recurring(self, reference_doc, auto_repeat_doc):
		self.valid_till = None

	def get_rows_with_alternatives(self):
		rows_with_alternatives = []
		table_length = len(self.get("items"))

		for idx, row in enumerate(self.get("items")):
			if row.is_alternative:
				continue

			if idx == (table_length - 1):
				break

			if self.get("items")[idx + 1].is_alternative:
				rows_with_alternatives.append(row.name)

		return rows_with_alternatives

	def initialize_revision(self) -> None:
		self.is_latest_revision = int(not self.revised_from)
		if self.amended_from:
			source = frappe.get_doc("Quotation", self.amended_from)
			source.check_permission("read")
			for field in Quotation.revision_fields:
				self.set(field, source.get(field))
			self.is_latest_revision = int(not self.original_quotation)
			return

		if not self.revised_from:
			self.original_quotation = None
			self.quotation_version = 0
			return

		source = frappe.get_doc("Quotation", self.revised_from)
		self.original_quotation = source.original_quotation or source.name

		# Serialize the first allocation as well as later revisions of the same quotation.
		self.lock_revision_family()
		source = frappe.get_doc("Quotation", self.revised_from, for_update=True)
		self.validate_revision_source(source)
		self.validate_revision_party(source)
		prefix = f"{self.original_quotation}-REV-"
		self.quotation_version = cint(getseries(prefix, 1))
		name = f"{prefix}{self.quotation_version}"
		if len(name) > 140:
			frappe.throw(_("Quotation name is too long to append a revision suffix."))
		self.set_new_name(set_name=name)

	def update_revision_fields(self) -> None:
		previous = self.flags.pop("quotation_before_update", None)
		if previous:
			# Update Items persists children before saving the parent. Preserve the original
			# snapshot for both the commercial-change count and the Version history.
			self._doc_before_save = previous
		else:
			previous = self.get_doc_before_save()

		if previous:
			for field in Quotation.revision_fields:
				if self.get(field) != previous.get(field):
					frappe.throw(_("Quotation version references cannot be changed."))
		elif self.amended_from:
			previous = frappe.get_doc("Quotation", self.amended_from)

		if self.revised_from:
			self.validate_revision_party(frappe.get_cached_doc("Quotation", self.revised_from))

		if self._action == "submit":
			self.is_latest_revision = 1
		elif self.is_new():
			self.is_latest_revision = int(not self.original_quotation)
		else:
			self.is_latest_revision = cint(previous.is_latest_revision)
		self.quote_revision_count = (
			cint(previous.get("quote_revision_count")) + int(self.has_commercial_changes(previous))
			if previous
			else 0
		)

	def has_commercial_changes(self, previous: Document) -> bool:
		return self.get_revision_values(previous) != self.get_revision_values(self)

	def get_revision_values(self, doc: Document) -> tuple:
		items = [self.get_revision_field_values(row, Quotation.revision_item_fields) for row in doc.items]
		if not any(row.is_alternative for row in doc.items):
			items = Counter(items)
		taxes = [
			(
				*self.get_revision_field_values(row, Quotation.revision_tax_fields),
				flt(row.tax_amount) if row.charge_type == "Actual" else None,
			)
			for row in doc.taxes
		]
		payments = [
			self.get_revision_field_values(row, Quotation.revision_payment_fields)
			for row in doc.payment_schedule
		]
		return (
			self.get_revision_field_values(doc, Quotation.revision_commercial_fields),
			items,
			taxes,
			payments,
		)

	@staticmethod
	def get_revision_field_values(doc: Document, fieldnames: tuple[str, ...]) -> tuple:
		values = []
		for fieldname in fieldnames:
			field = doc.meta.get_field(fieldname)
			value = doc.get(fieldname)
			if field and field.fieldtype in ("Float", "Currency", "Percent", "Int", "Check"):
				value = flt(value)
			else:
				value = str(value or "")
			values.append(value)
		return tuple(values)

	@staticmethod
	def validate_revision_source(source: Document) -> None:
		source.check_permission("read")
		if source.docstatus != 1:
			frappe.throw(_("Only submitted quotations can be revised."))
		if not source.is_latest_revision or source.status not in ("Open", "Expired"):
			frappe.throw(_("Only the current Open or Expired quotation can be revised."))
		source.validate_revision_transactions()

	def validate_revision_party(self, source: Document) -> None:
		if any(self.get(field) != source.get(field) for field in ("company", "quotation_to", "party_name")):
			frappe.throw(_("A quotation revision must use the same company and party as its source."))

	def validate_revision_submission(self) -> None:
		self.lock_revision_family()
		if not self.original_quotation:
			return

		source = frappe.get_doc("Quotation", self.revised_from, for_update=True)
		if source.docstatus != 1 or source.status == "Lost":
			frappe.throw(_("The source quotation must remain submitted and must not be Lost."))
		self.validate_revision_transactions()
		current = self.get_current_revision()
		if current and current.status == "Lost":
			frappe.throw(_("The current quotation is Lost and cannot be replaced by a draft revision."))
		if current and cint(current.quotation_version) >= cint(self.quotation_version):
			frappe.throw(
				_("Quotation {0} is already the current version. Create a revision from it instead.").format(
					current.name
				)
			)

	def validate_revision_cancellation(self) -> None:
		self.lock_revision_family()
		quotation = frappe.qb.DocType("Quotation")
		drafts = (
			frappe.qb.from_(quotation)
			.select(quotation.name)
			.where(
				(quotation.docstatus == 0)
				& ((quotation.original_quotation == self.name) | (quotation.revised_from == self.name))
			)
			.limit(1)
			.for_update()
			.run(pluck=True)
		)
		if drafts:
			frappe.throw(
				_("Delete draft revision {0} before cancelling quotation {1}.").format(drafts[0], self.name)
			)

	def sync_revision_status(self) -> None:
		original = self.original_quotation or self.name
		self.lock_revision_family()
		members = self.get_revision_family()
		current = next((row.name for row in members if row.docstatus == 1), None)
		for row in members:
			is_current = int(
				row.name == current or (not current and row.name == original and row.docstatus == 0)
			)
			if cint(row.is_latest_revision) == is_current:
				continue
			quotation = self if row.name == self.name else frappe.get_doc("Quotation", row.name)
			quotation.db_set("is_latest_revision", is_current)
			quotation.set_status(update=True)

	def validate_revision_transactions(self) -> None:
		self.lock_revision_family()
		names = [row.name for row in self.get_revision_family()]
		# Older direct invoices without a quotation reference cannot be matched retrospectively.
		for doctype, fieldname in (("Sales Order", "prevdoc_docname"), ("Sales Invoice", "quotation")):
			item = frappe.qb.DocType(f"{doctype} Item")
			if (
				frappe.qb.from_(item)
				.select(item.name)
				.where((item.docstatus == 1) & item[fieldname].isin(names))
				.limit(1)
				.for_update()
				.run()
			):
				frappe.throw(_("A quotation with a submitted {0} cannot be revised.").format(_(doctype)))

	def lock_revision_family(self) -> None:
		original = self.original_quotation or self.name
		if original:
			frappe.db.get_value("Quotation", original, "name", for_update=True)

	def get_current_revision(self):
		return next((row for row in self.get_revision_family() if row.docstatus == 1), None)

	def get_revision_family(self):
		original = self.original_quotation or self.name
		quotation = frappe.qb.DocType("Quotation")
		return (
			frappe.qb.from_(quotation)
			.select(
				quotation.name,
				quotation.docstatus,
				quotation.status,
				quotation.quotation_version,
				quotation.is_latest_revision,
			)
			.where((quotation.name == original) | (quotation.original_quotation == original))
			.orderby(quotation.quotation_version, quotation.creation, order=Order.desc)
			.for_update()
			.run(as_dict=True)
		)

	@staticmethod
	def get_report_revision_condition(quotation, period_end_dates, date_field="transaction_date"):
		"""Select the latest submitted version within each reporting period."""
		period_end = Case()
		for end_date in period_end_dates:
			next_day = getdate(add_days(end_date, 1))
			period_end = period_end.when(quotation[date_field] < next_day, next_day)

		revision = frappe.qb.DocType("Quotation").as_("later_revision")
		original = IfNull(NullIf(quotation.original_quotation, ""), quotation.name)
		newer_version = (revision.quotation_version > quotation.quotation_version) | (
			(revision.quotation_version == quotation.quotation_version)
			& (revision.creation > quotation.creation)
		)
		later_revisions = (
			frappe.qb.from_(revision)
			.select(revision.name)
			.where(
				(revision.original_quotation == original)
				& (revision.docstatus == 1)
				& (revision[date_field] < period_end)
				& newer_version
			)
		)
		return ExistsCriterion(later_revisions).negate()


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Quotations"),
			"list_template": "templates/includes/list/list.html",
		}
	)

	return list_context


def set_expired_status():
	quotation = frappe.qb.DocType("Quotation")
	so = frappe.qb.DocType("Sales Order")
	so_item = frappe.qb.DocType("Sales Order Item")

	# submitted Sales Orders raised against the quotation (correlated to the quotation being updated)
	so_against_quo = (
		frappe.qb.from_(so)
		.from_(so_item)
		.select(so.name)
		.where(
			(so_item.docstatus == 1)
			& (so.docstatus == 1)
			& (so_item.parent == so.name)
			& (so_item.prevdoc_docname == quotation.name)
		)
	)

	# expire submitted, non-expired/lost quotations whose validity has ended and that have no SO
	(
		frappe.qb.update(quotation)
		.set(quotation.status, "Expired")
		.where(
			(quotation.docstatus == 1)
			& (quotation.status.notin(["Expired", "Lost", "Superseded"]))
			& (quotation.valid_till < nowdate())
			& ExistsCriterion(so_against_quo).negate()
		)
	).run()
