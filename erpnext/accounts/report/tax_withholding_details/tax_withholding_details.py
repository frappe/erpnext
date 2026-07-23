# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull


class TaxWithholdingDetailsReport:
	party_types = ("Customer", "Supplier")
	document_types = ("Purchase Invoice", "Sales Invoice", "Payment Entry", "Journal Entry")

	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.entries = []
		self.doc_info = {}
		self.party_details = {}

	@classmethod
	def execute(cls, filters=None):
		return cls(filters).run()

	def run(self):
		self.validate_filters()
		return self.get_columns(), self.get_data()

	def validate_filters(self):
		if not self.filters.from_date or not self.filters.to_date:
			frappe.throw(_("From Date and To Date are required"))

		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

	def get_data(self):
		self.entries = self.get_entries_query().run(as_dict=True)
		if not self.entries:
			return []

		self.doc_info = self.fetch_additional_doc_info()
		self.party_details = self.fetch_party_details()
		return self.build_rows()

	def build_rows(self):
		rows = []
		for entry in self.entries:
			doc_details = (
				self.doc_info.get((entry.transaction_type, entry.ref_no), {}) if entry.ref_no else {}
			)
			party_info = self.party_details.get((entry.party_type, entry.party), {})
			rows.append({**entry, **doc_details, **party_info})

		rows.sort(
			key=lambda x: (
				x["tax_withholding_category"] or "",
				x["transaction_date"] or "",
				x["withholding_name"] or "",
			)
		)
		return rows

	def get_entries_query(self):
		twe = frappe.qb.DocType("Tax Withholding Entry")
		query = (
			frappe.qb.from_(twe)
			.select(
				twe.party_type,
				twe.party,
				IfNull(twe.tax_id, "").as_("tax_id"),
				twe.tax_withholding_category,
				twe.taxable_amount.as_("total_amount"),
				twe.tax_rate.as_("rate"),
				twe.withholding_amount.as_("tax_amount"),
				IfNull(twe.taxable_doctype, "").as_("transaction_type"),
				IfNull(twe.taxable_name, "").as_("ref_no"),
				twe.taxable_date,
				IfNull(twe.withholding_doctype, "").as_("withholding_doctype"),
				IfNull(twe.withholding_name, "").as_("withholding_name"),
				twe.withholding_date.as_("transaction_date"),
			)
			.where(twe.docstatus == 1)
			.where(twe.withholding_date >= self.filters.from_date)
			.where(twe.withholding_date <= self.filters.to_date)
			.where(IfNull(twe.withholding_name, "") != "")
			.where(twe.status != "Duplicate")
		)

		if self.filters.company:
			query = query.where(twe.company == self.filters.company)
		if self.filters.party_type:
			query = query.where(twe.party_type == self.filters.party_type)
		if self.filters.party:
			query = query.where(twe.party == self.filters.party)

		return query

	def fetch_party_details(self):
		parties_by_type = {pt: set() for pt in self.party_types}
		for entry in self.entries:
			if entry.party_type in parties_by_type and entry.party:
				parties_by_type[entry.party_type].add(entry.party)

		party_map = {}
		for party_type, party_set in parties_by_type.items():
			if not party_set:
				continue

			query = self.get_party_query(party_type, party_set)
			if query is None:
				continue

			for row in query.run(as_dict=True):
				party_map[(party_type, row.pop("name"))] = row

		return party_map

	def get_party_query(self, party_type, party_set):
		doctype = frappe.qb.DocType(party_type)
		fields = [doctype.name]

		if party_type == "Supplier":
			fields.extend(
				[
					doctype.supplier_type.as_("party_entity_type"),
					doctype.supplier_name.as_("party_name"),
				]
			)
		elif party_type == "Customer":
			fields.extend(
				[
					doctype.customer_type.as_("party_entity_type"),
					doctype.customer_name.as_("party_name"),
				]
			)
		else:
			return None

		return frappe.qb.from_(doctype).select(*fields).where(doctype.name.isin(party_set))

	def fetch_additional_doc_info(self):
		docs_by_type = {dt: set() for dt in self.document_types}
		for entry in self.entries:
			if entry.ref_no and entry.transaction_type in docs_by_type:
				docs_by_type[entry.transaction_type].add(entry.ref_no)

		doc_info = {}
		for doctype_name, voucher_set in docs_by_type.items():
			if not voucher_set:
				continue

			query = self.get_doc_info_query(doctype_name, voucher_set)
			if query is None:
				continue

			for row in query.run(as_dict=True):
				doc_info[(doctype_name, row.pop("name"))] = row

		return doc_info

	def get_doc_info_query(self, doctype_name, voucher_set):
		if doctype_name == "Purchase Invoice":
			get_doc_fields = self.get_purchase_invoice_fields
		elif doctype_name == "Sales Invoice":
			get_doc_fields = self.get_sales_invoice_fields
		elif doctype_name == "Payment Entry":
			get_doc_fields = self.get_payment_entry_fields
		elif doctype_name == "Journal Entry":
			get_doc_fields = self.get_journal_entry_fields
		else:
			return None

		doctype = frappe.qb.DocType(doctype_name)
		fields = [doctype.name, *get_doc_fields(doctype)]
		return frappe.qb.from_(doctype).select(*fields).where(doctype.name.isin(voucher_set))

	def get_purchase_invoice_fields(self, doctype):
		return [
			doctype.grand_total,
			doctype.base_total,
			doctype.bill_no.as_("supplier_invoice_no"),
			doctype.bill_date.as_("supplier_invoice_date"),
		]

	def get_sales_invoice_fields(self, doctype):
		return [doctype.grand_total, doctype.base_total]

	def get_payment_entry_fields(self, doctype):
		return [
			doctype.paid_amount_after_tax.as_("grand_total"),
			doctype.base_paid_amount.as_("base_total"),
		]

	def get_journal_entry_fields(self, doctype):
		return [doctype.total_debit.as_("grand_total"), doctype.total_debit.as_("base_total")]

	def get_columns(self):
		party_type = self.filters.get("party_type", "Party")
		return [
			{
				"label": _("Tax Withholding Category"),
				"options": "Tax Withholding Category",
				"fieldname": "tax_withholding_category",
				"fieldtype": "Link",
				"width": 90,
			},
			{"label": _("Tax Id"), "fieldname": "tax_id", "fieldtype": "Data", "width": 60},
			{
				"label": _(f"{party_type} Name"),
				"fieldname": "party_name",
				"fieldtype": "Data",
				"width": 180,
			},
			{
				"label": _(party_type),
				"fieldname": "party",
				"fieldtype": "Dynamic Link",
				"options": "party_type",
				"width": 180,
			},
			{
				"label": _(f"{party_type} Type"),
				"fieldname": "party_entity_type",
				"fieldtype": "Data",
				"width": 100,
			},
			{
				"label": _("Supplier Invoice No"),
				"fieldname": "supplier_invoice_no",
				"fieldtype": "Data",
				"width": 120,
			},
			{
				"label": _("Supplier Invoice Date"),
				"fieldname": "supplier_invoice_date",
				"fieldtype": "Date",
				"width": 120,
			},
			{"label": _("Tax Rate %"), "fieldname": "rate", "fieldtype": "Percent", "width": 60},
			{
				"label": _("Taxable Amount"),
				"fieldname": "total_amount",
				"fieldtype": "Currency",
				"width": 120,
			},
			{"label": _("Tax Amount"), "fieldname": "tax_amount", "fieldtype": "Currency", "width": 120},
			{
				"label": _("Grand Total (Company Currency)"),
				"fieldname": "base_total",
				"fieldtype": "Currency",
				"width": 150,
			},
			{
				"label": _("Grand Total (Transaction Currency)"),
				"fieldname": "grand_total",
				"fieldtype": "Currency",
				"width": 170,
			},
			{"label": _("Reference Date"), "fieldname": "taxable_date", "fieldtype": "Date", "width": 100},
			{
				"label": _("Transaction Type"),
				"fieldname": "transaction_type",
				"fieldtype": "Data",
				"width": 130,
			},
			{
				"label": _("Reference No."),
				"fieldname": "ref_no",
				"fieldtype": "Dynamic Link",
				"options": "transaction_type",
				"width": 180,
			},
			{
				"label": _("Date of Transaction"),
				"fieldname": "transaction_date",
				"fieldtype": "Date",
				"width": 100,
			},
			{
				"label": _("Withholding Document"),
				"fieldname": "withholding_name",
				"fieldtype": "Dynamic Link",
				"options": "withholding_doctype",
				"width": 150,
			},
		]


execute = TaxWithholdingDetailsReport.execute
