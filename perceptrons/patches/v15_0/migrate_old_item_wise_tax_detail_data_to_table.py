import click
import frappe
from frappe import parse_json
from frappe.model.document import bulk_insert
from frappe.utils import flt

DOCTYPES_TO_PATCH = {
	"Sales Taxes and Charges": [
		"Sales Invoice",
		"POS Invoice",
		"Sales Order",
		"Delivery Note",
		"Quotation",
	],
	"Purchase Taxes and Charges": [
		"Purchase Invoice",
		"Purchase Order",
		"Purchase Receipt",
		"Supplier Quotation",
	],
}


TAX_WITHHOLDING_DOCS = (
	"Purchase Invoice",
	"Purchase Order",
	"Purchase Receipt",
)


def execute():
	for tax_doctype, doctypes in DOCTYPES_TO_PATCH.items():
		for doctype in doctypes:
			docnames = frappe.get_all(
				tax_doctype,
				filters={
					"item_wise_tax_detail": ["is", "set"],
					"docstatus": ["=", 1],
					"parenttype": ["=", doctype],
				},
				pluck="parent",
			)

			total_docs = len(docnames)
			if not total_docs:
				continue

			chunk_size = 1000

			with click.progressbar(
				range(0, total_docs, chunk_size), label=f"Migrating {total_docs} {doctype}s"
			) as bar:
				for index in bar:
					chunk = docnames[index : index + chunk_size]
					doc_info = get_doc_details(chunk, doctype)
					if not doc_info:
						# no valid invoices found
						continue

					docs = [d.name for d in doc_info]  # valid invoices

					# Delete existing item-wise tax details to avoid duplicates
					delete_existing_tax_details(docs, doctype)

					taxes = get_taxes_for_docs(docs, tax_doctype, doctype)
					items = get_items_for_docs(docs, doctype)
					compiled_docs = compile_docs(doc_info, taxes, items, doctype, tax_doctype)
					rows_to_insert = []

					for doc in compiled_docs:
						if not (doc.taxes and doc.items):
							continue
						rows_to_insert.extend(ItemTax().get_item_wise_tax_details(doc))

					if rows_to_insert:
						bulk_insert("Item Wise Tax Detail", rows_to_insert, commit_chunks=True)


def get_taxes_for_docs(parents, tax_doctype, doctype):
	tax = frappe.qb.DocType(tax_doctype)

	return (
		frappe.qb.from_(tax)
		.select("*")
		.where(tax.parenttype == doctype)
		.where(tax.parent.isin(parents))
		.run(as_dict=True)
	)


def get_items_for_docs(parents, doctype):
	item = frappe.qb.DocType(f"{doctype} Item")
	additional_fields = []

	if doctype in TAX_WITHHOLDING_DOCS:
		additional_fields.append(item.apply_tds)

	return (
		frappe.qb.from_(item)
		.select(
			item.name,
			item.parent,
			item.item_code,
			item.item_name,
			item.base_net_amount,
			item.qty,
			item.item_tax_rate,
			*additional_fields,
		)
		.where(item.parenttype == doctype)
		.where(item.parent.isin(parents))
		.run(as_dict=True)
	)


def get_doc_details(parents, doctype):
	inv = frappe.qb.DocType(doctype)
	additional_fields = []
	if doctype in TAX_WITHHOLDING_DOCS:
		additional_fields.append(inv.base_tax_withholding_net_total)

	return (
		frappe.qb.from_(inv)
		.select(
			inv.name,
			inv.base_net_total,
			inv.company,
			*additional_fields,
		)
		.where(inv.name.isin(parents))
		.run(as_dict=True)
	)


def compile_docs(doc_info, taxes, items, doctype, tax_doctype):
	"""
	Compile docs, so that each one could be accessed as if it's a single doc.
	"""
	response = frappe._dict()
	for doc in doc_info:
		response[doc.name] = frappe._dict(**doc, taxes=[], items=[], doctype=doctype, tax_doctype=tax_doctype)

	for tax in taxes:
		response[tax.parent]["taxes"].append(tax)

	for item in items:
		response[item.parent]["items"].append(item)

	return response.values()


def delete_existing_tax_details(doc_names, doctype):
	"""
	Delete existing Item Wise Tax Detail records for the given documents
	to avoid duplicates when re-running the migration.
	"""
	if not doc_names:
		return

	frappe.db.delete("Item Wise Tax Detail", {"parent": ["in", doc_names], "parenttype": doctype})


class ItemTax:
	def get_item_wise_tax_details(self, doc):
		"""
		This method calculates tax amounts for each item-tax combination.
		"""
		item_wise_tax_details = []
		company_currency = frappe.get_cached_value("Company", doc.company, "default_currency")
		precision = frappe.get_precision(doc.tax_doctype, "tax_amount", currency=company_currency)

		tax_differences = frappe._dict()
		last_taxable_items = frappe._dict()

		# Initialize tax differences with expected amounts
		for tax_row in doc.taxes:
			if tax_row.base_tax_amount_after_discount_amount:
				multiplier = -1 if tax_row.get("add_deduct_tax") == "Deduct" else 1
				tax_differences[tax_row.name] = tax_row.base_tax_amount_after_discount_amount * multiplier

		idx = 1
		for item in doc.get("items"):
			item_proportion = item.base_net_amount / doc.base_net_total if doc.base_net_total else 0
			for tax_row in doc.taxes:
				tax_rate = 0
				tax_amount = 0

				if not tax_row.base_tax_amount_after_discount_amount:
					continue

				charge_type = tax_row.charge_type
				if tax_row.item_wise_tax_detail:
					# tax rate
					tax_rate = self._get_item_tax_rate(item, tax_row)
					# tax amount
					if tax_rate:
						multiplier = (
							item.qty if charge_type == "On Item Quantity" else item.base_net_amount / 100
						)
						tax_amount = multiplier * tax_rate
					else:
						# eg: charge_type == actual
						item_key = item.item_code or item.item_name
						item_tax_detail = self._get_item_tax_details(tax_row).get(item_key, {})
						tax_amount = item_tax_detail.get("tax_amount", 0) * item_proportion
				# Actual rows where no item_wise_tax_detail
				elif charge_type == "Actual":
					if tax_row.get("is_tax_withholding_account"):
						if not item.get("apply_tds") or not doc.get("base_tax_withholding_net_total"):
							item_proportion = 0
						else:
							item_proportion = item.base_net_amount / doc.base_tax_withholding_net_total

					tax_amount = tax_row.base_tax_amount_after_discount_amount * item_proportion

				if tax_row.get("add_deduct_tax") == "Deduct":
					tax_amount *= -1

				tax_doc = get_item_tax_doc(item, tax_row, tax_rate, tax_amount, idx, precision)
				item_wise_tax_details.append(tax_doc)

				# Update tax differences and track last taxable item
				if tax_amount:
					tax_differences[tax_row.name] -= tax_amount
					last_taxable_items[tax_row.name] = tax_doc

				idx += 1

		# Handle rounding errors by applying differences to last taxable items
		self._handle_rounding_differences(tax_differences, last_taxable_items)

		return item_wise_tax_details

	def _handle_rounding_differences(self, tax_differences, last_taxable_items):
		"""
		Handle rounding errors by applying the difference to the last taxable item
		"""
		for tax_row, diff in tax_differences.items():
			if not diff or tax_row not in last_taxable_items:
				continue

			rounded_difference = flt(diff, 5)

			if abs(rounded_difference) <= 0.5:
				last_item_tax_doc = last_taxable_items[tax_row]
				last_item_tax_doc.amount = flt(last_item_tax_doc.amount + rounded_difference, 5)

	def _get_item_tax_details(self, tax_row):
		# temp cache
		if not getattr(tax_row, "__tax_details", None):
			tax_row.__tax_details = parse_item_wise_tax_details(tax_row.get("item_wise_tax_detail") or "{}")

		return tax_row.__tax_details

	def _get_item_tax_rate(self, item, tax_row):
		# NOTE: Use item tax rate as same item code
		# could have different tax rates in same invoice

		item_tax_rates = frappe.parse_json(item.item_tax_rate or {})

		if item_tax_rates and tax_row.account_head in item_tax_rates:
			return item_tax_rates[tax_row.account_head]

		return flt(tax_row.rate)


def get_item_tax_doc(item, tax, rate, tax_value, idx, precision=2):
	return frappe.get_doc(
		{
			"doctype": "Item Wise Tax Detail",
			"name": frappe.generate_hash(),
			"idx": idx,
			"item_row": item.name,
			"tax_row": tax.name,
			"rate": rate,
			"amount": flt(tax_value, precision),
			"taxable_amount": item.base_net_amount,
			"docstatus": tax.docstatus,
			"parent": tax.parent,
			"parenttype": tax.parenttype,
			"parentfield": "item_wise_tax_details",
		}
	)


def parse_item_wise_tax_details(item_wise_tax_detail):
	updated_tax_details = {}
	try:
		item_iterator = parse_json(item_wise_tax_detail)
	except Exception:
		return updated_tax_details
	else:
		# This is stale data from 2009 found in a database
		if isinstance(item_iterator, int | float):
			return updated_tax_details

		for item, tax_data in item_iterator.items():
			if isinstance(tax_data, list) and len(tax_data) >= 2:
				updated_tax_details[item] = frappe._dict(
					tax_rate=tax_data[0] or 0,
					tax_amount=tax_data[1] or 0,
				)
			elif isinstance(tax_data, str):
				updated_tax_details[item] = frappe._dict(
					tax_rate=flt(tax_data),
					tax_amount=0.0,
				)
			elif isinstance(tax_data, dict):
				updated_tax_details[item] = tax_data

	return updated_tax_details
