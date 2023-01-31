# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document

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
]

product_discount_fields = [
	"free_item",
	"free_qty",
	"free_item_uom",
	"free_item_rate",
	"same_item",
	"is_recursive",
	"apply_multiple_pricing_rules",
]


class TransactionExists(frappe.ValidationError):
	pass


class PromotionalScheme(Document):
	def validate(self):
		if not self.selling and not self.buying:
			frappe.throw(_("Either 'Selling' or 'Buying' must be selected"), title=_("Mandatory"))
		if not (self.price_discount_slabs or self.product_discount_slabs):
			frappe.throw(_("Price or product discount slabs are required"))

		self.validate_applicable_for()
		self.validate_pricing_rules()

	def validate_applicable_for(self):
		if self.applicable_for:
			applicable_for = frappe.scrub(self.applicable_for)

			if not self.get(applicable_for):
				msg = f"The field {frappe.bold(self.applicable_for)} is required"
				frappe.throw(_(msg))

	def validate_pricing_rules(self):
		if self.is_new():
			return

		transaction_exists = False
		docnames = []

		# If user has changed applicable for
		if self._doc_before_save.applicable_for == self.applicable_for:
			return

		docnames = frappe.get_all("Pricing Rule", filters={"promotional_scheme": self.name})

		for docname in docnames:
			if frappe.db.exists(
				"Pricing Rule Detail", {"pricing_rule": docname.name, "docstatus": ("<", 2)}
			):
				raise_for_transaction_exists(self.name)

		if docnames and not transaction_exists:
			for docname in docnames:
				frappe.delete_doc("Pricing Rule", docname.name)

	def on_update(self):
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

	for idx, d in enumerate(doc.get(child_doc)):
		if d.name in rules:
			if not args.get(applicable_for):
				docname = get_pricing_rule_docname(d)
				pr = prepare_pricing_rule(args, doc, child_doc, discount_fields, d, docname)
				new_doc.append(pr)
			else:
				for applicable_for_value in args.get(applicable_for):
					docname = get_pricing_rule_docname(d, applicable_for, applicable_for_value)
					pr = prepare_pricing_rule(
						args, doc, child_doc, discount_fields, d, docname, applicable_for, applicable_for_value
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
	row: dict, applicable_for: str = None, applicable_for_value: str = None
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
