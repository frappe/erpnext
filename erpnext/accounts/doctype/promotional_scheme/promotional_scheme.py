# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull

pricing_rule_fields = [
	"apply_on",
	"mixed_conditions",
	"is_cumulative",
	"other_item_code",
	"other_item_group",
	"apply_rule_on_other",
	"other_brand",
	"selling",
	"buying",
	"applicable_for",
	"valid_from",
	"valid_upto",
	"customer",
	"customer_group",
	"territory",
	"sales_partner",
	"campaign",
	"supplier",
	"supplier_group",
	"company",
	"currency",
	"apply_multiple_pricing_rules",
]

other_fields = [
	"min_qty",
	"max_qty",
	"min_amount",
	"max_amount",
	"priority",
	"warehouse",
	"threshold_percentage",
	"rule_description",
]

price_discount_fields = [
	"rate_or_discount",
	"apply_discount_on",
	"apply_discount_on_rate",
	"rate",
	"discount_amount",
	"discount_percentage",
	"validate_applied_rule",
	"apply_multiple_pricing_rules",
	"for_price_list",
]

product_discount_fields = [
	"free_item",
	"free_qty",
	"free_item_uom",
	"free_item_rate",
	"same_item",
	"is_recursive",
	"recurse_for",
	"apply_recursion_over",
	"apply_multiple_pricing_rules",
	"round_free_qty",
]


class TransactionExists(frappe.ValidationError):
	pass


class PromotionalScheme(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.campaign_item.campaign_item import CampaignItem
		from erpnext.accounts.doctype.customer_group_item.customer_group_item import CustomerGroupItem
		from erpnext.accounts.doctype.customer_item.customer_item import CustomerItem
		from erpnext.accounts.doctype.pricing_rule_brand.pricing_rule_brand import PricingRuleBrand
		from erpnext.accounts.doctype.pricing_rule_item_code.pricing_rule_item_code import (
			PricingRuleItemCode,
		)
		from erpnext.accounts.doctype.pricing_rule_item_group.pricing_rule_item_group import (
			PricingRuleItemGroup,
		)
		from erpnext.accounts.doctype.promotional_scheme_price_discount.promotional_scheme_price_discount import (
			PromotionalSchemePriceDiscount,
		)
		from erpnext.accounts.doctype.promotional_scheme_product_discount.promotional_scheme_product_discount import (
			PromotionalSchemeProductDiscount,
		)
		from erpnext.accounts.doctype.sales_partner_item.sales_partner_item import SalesPartnerItem
		from erpnext.accounts.doctype.supplier_group_item.supplier_group_item import SupplierGroupItem
		from erpnext.accounts.doctype.supplier_item.supplier_item import SupplierItem
		from erpnext.accounts.doctype.territory_item.territory_item import TerritoryItem

		applicable_for: DF.Literal[
			"",
			"Customer",
			"Customer Group",
			"Territory",
			"Sales Partner",
			"Campaign",
			"Supplier",
			"Supplier Group",
		]
		apply_on: DF.Literal["", "Item Code", "Item Group", "Brand", "Transaction"]
		apply_rule_on_other: DF.Literal["", "Item Code", "Item Group", "Brand"]
		brands: DF.Table[PricingRuleBrand]
		buying: DF.Check
		campaign: DF.TableMultiSelect[CampaignItem]
		company: DF.Link
		currency: DF.Link | None
		customer: DF.TableMultiSelect[CustomerItem]
		customer_group: DF.TableMultiSelect[CustomerGroupItem]
		disable: DF.Check
		is_cumulative: DF.Check
		item_groups: DF.Table[PricingRuleItemGroup]
		items: DF.Table[PricingRuleItemCode]
		mixed_conditions: DF.Check
		other_brand: DF.Link | None
		other_item_code: DF.Link | None
		other_item_group: DF.Link | None
		price_discount_slabs: DF.Table[PromotionalSchemePriceDiscount]
		product_discount_slabs: DF.Table[PromotionalSchemeProductDiscount]
		sales_partner: DF.TableMultiSelect[SalesPartnerItem]
		selling: DF.Check
		supplier: DF.TableMultiSelect[SupplierItem]
		supplier_group: DF.TableMultiSelect[SupplierGroupItem]
		territory: DF.TableMultiSelect[TerritoryItem]
		valid_from: DF.Date | None
		valid_upto: DF.Date | None
	# end: auto-generated types

	def validate(self):
		if not self.selling and not self.buying:
			frappe.throw(_("Either 'Selling' or 'Buying' must be selected"), title=_("Mandatory"))
		if not (self.price_discount_slabs or self.product_discount_slabs):
			frappe.throw(_("Price or product discount slabs are required"))

		self.validate_applicable_for()
		self.validate_pricing_rules()
		self.validate_mixed_with_recursion()

	def validate_applicable_for(self):
		if self.applicable_for:
			applicable_for = frappe.scrub(self.applicable_for)

			if not self.get(applicable_for):
				msg = f"The field {frappe.bold(self.applicable_for)} is required"
				frappe.throw(_(msg))

	def validate_pricing_rules(self):
		if self.is_new():
			return

		invalid_pricing_rule = self.get_invalid_pricing_rules()

		if not invalid_pricing_rule:
			return

		if frappe.db.exists(
			"Pricing Rule Detail",
			{
				"pricing_rule": ["in", invalid_pricing_rule],
				"docstatus": ["<", 2],
			},
		):
			raise_for_transaction_exists(self.name)

		for doc in invalid_pricing_rule:
			frappe.delete_doc("Pricing Rule", doc)

		frappe.msgprint(
			_("The following invalid Pricing Rules are deleted:")
			+ "<br><br><ul><li>"
			+ "</li><li>".join(invalid_pricing_rule)
			+ "</li></ul>"
		)

	def get_invalid_pricing_rules(self):
		pr = frappe.qb.DocType("Pricing Rule")
		conditions = []
		conditions.append(pr.promotional_scheme == self.name)

		if self.applicable_for:
			applicable_for = frappe.scrub(self.applicable_for)
			applicable_for_list = [d.get(applicable_for) for d in self.get(applicable_for)]

			conditions.append(
				(IfNull(pr.applicable_for, "") != self.applicable_for)
				| (
					(IfNull(pr.applicable_for, "") == self.applicable_for)
					& IfNull(pr[applicable_for], "").notin(applicable_for_list)
				)
			)
		else:
			conditions.append(IfNull(pr.applicable_for, "") != "")

		return frappe.qb.from_(pr).select(pr.name).where(Criterion.all(conditions)).run(pluck=True)

	def on_update(self):
		self.validate()
		pricing_rules = (
			frappe.get_all(
				"Pricing Rule",
				fields=["promotional_scheme_id", "name", "creation"],
				filters={"promotional_scheme": self.name, "applicable_for": self.applicable_for},
				order_by="creation asc",
			)
			or {}
		)
		self.update_pricing_rules(pricing_rules)

	def validate_mixed_with_recursion(self):
		if self.mixed_conditions:
			if self.product_discount_slabs:
				for slab in self.product_discount_slabs:
					if slab.is_recursive:
						frappe.throw(
							_("Recursive Discounts with Mixed condition is not supported by the system")
						)

	def update_pricing_rules(self, pricing_rules):
		rules = {}
		count = 0
		names = []
		for rule in pricing_rules:
			names.append(rule.name)
			rules[rule.get("promotional_scheme_id")] = names

		docs = get_pricing_rules(self, rules)

		for doc in docs:
			doc.run_method("validate")
			if doc.get("__islocal"):
				count += 1
				doc.insert()
			else:
				doc.save()
				frappe.msgprint(_("Pricing Rule {0} is updated").format(doc.name))

		if count:
			frappe.msgprint(_("New {0} pricing rules are created").format(count))

	def on_trash(self):
		for rule in frappe.get_all("Pricing Rule", {"promotional_scheme": self.name}):
			frappe.delete_doc("Pricing Rule", rule.name)


def raise_for_transaction_exists(name):
	msg = f"""You can't change the {frappe.bold(_('Applicable For'))}
		because transactions are present against the Promotional Scheme {frappe.bold(name)}. """
	msg += "Kindly disable this Promotional Scheme and create new for new Applicable For."

	frappe.throw(_(msg), TransactionExists)


def get_pricing_rules(doc, rules=None):
	if rules is None:
		rules = {}
	new_doc = []
	for child_doc, fields in {
		"price_discount_slabs": price_discount_fields,
		"product_discount_slabs": product_discount_fields,
	}.items():
		if doc.get(child_doc):
			new_doc.extend(_get_pricing_rules(doc, child_doc, fields, rules))

	return new_doc


def _get_pricing_rules(doc, child_doc, discount_fields, rules=None):
	if rules is None:
		rules = {}
	new_doc = []
	args = get_args_for_pricing_rule(doc)
	applicable_for = frappe.scrub(doc.get("applicable_for"))

	for _idx, d in enumerate(doc.get(child_doc)):
		if d.name in rules:
			if not args.get(applicable_for):
				docname = get_pricing_rule_docname(d)
				pr = prepare_pricing_rule(args, doc, child_doc, discount_fields, d, docname)
				new_doc.append(pr)
			else:
				for applicable_for_value in args.get(applicable_for):
					docname = get_pricing_rule_docname(d, applicable_for, applicable_for_value)
					pr = prepare_pricing_rule(
						args,
						doc,
						child_doc,
						discount_fields,
						d,
						docname,
						applicable_for,
						applicable_for_value,
					)
					new_doc.append(pr)

		elif args.get(applicable_for):
			applicable_for_values = args.get(applicable_for) or []
			for applicable_for_value in applicable_for_values:
				pr = prepare_pricing_rule(
					args,
					doc,
					child_doc,
					discount_fields,
					d,
					applicable_for=applicable_for,
					value=applicable_for_value,
				)

				new_doc.append(pr)
		else:
			pr = prepare_pricing_rule(args, doc, child_doc, discount_fields, d)
			new_doc.append(pr)

	return new_doc


def get_pricing_rule_docname(
	row: dict, applicable_for: str | None = None, applicable_for_value: str | None = None
) -> str:
	fields = ["promotional_scheme_id", "name"]
	filters = {"promotional_scheme_id": row.name}

	if applicable_for:
		fields.append(applicable_for)
		filters[applicable_for] = applicable_for_value

	docname = frappe.get_all("Pricing Rule", fields=fields, filters=filters)
	return docname[0].name if docname else ""


def prepare_pricing_rule(
	args, doc, child_doc, discount_fields, d, docname=None, applicable_for=None, value=None
):
	if docname:
		pr = frappe.get_doc("Pricing Rule", docname)
	else:
		pr = frappe.new_doc("Pricing Rule")

	pr.title = doc.name
	temp_args = args.copy()

	if value:
		temp_args[applicable_for] = value

	return set_args(temp_args, pr, doc, child_doc, discount_fields, d)


def set_args(args, pr, doc, child_doc, discount_fields, child_doc_fields):
	pr.update(args)
	for field in other_fields + discount_fields:
		target_field = field
		if target_field in ["min_amount", "max_amount"]:
			target_field = "min_amt" if field == "min_amount" else "max_amt"

		pr.set(target_field, child_doc_fields.get(field))

	pr.promotional_scheme_id = child_doc_fields.name
	pr.promotional_scheme = doc.name
	pr.disable = child_doc_fields.disable if child_doc_fields.disable else doc.disable
	pr.price_or_product_discount = "Price" if child_doc == "price_discount_slabs" else "Product"

	for field in ["items", "item_groups", "brands"]:
		if doc.get(field):
			pr.set(field, [])

		apply_on = frappe.scrub(doc.get("apply_on"))
		for d in doc.get(field):
			pr.append(field, {apply_on: d.get(apply_on), "uom": d.uom})

	return pr


def get_args_for_pricing_rule(doc):
	args = {"promotional_scheme": doc.name}
	applicable_for = frappe.scrub(doc.get("applicable_for"))

	for d in pricing_rule_fields:
		if d == applicable_for:
			items = []
			for applicable_for_values in doc.get(applicable_for):
				items.append(applicable_for_values.get(applicable_for))
			args[d] = items
		else:
			args[d] = doc.get(d)
	return args
