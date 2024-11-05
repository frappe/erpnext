# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _, scrub
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.database.schema import validate_column_name
from frappe.model import core_doctypes_list
from frappe.model.document import Document
from frappe.utils import cstr

from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import (
	get_allowed_types_from_settings,
)


class AccountingDimension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.accounting_dimension_detail.accounting_dimension_detail import (
			AccountingDimensionDetail,
		)

		dimension_defaults: DF.Table[AccountingDimensionDetail]
		disabled: DF.Check
		document_type: DF.Link
		fieldname: DF.Data | None
		label: DF.Data | None
	# end: auto-generated types

	def before_insert(self):
		self.set_fieldname_and_label()

	def validate(self):
		if self.document_type in (
			*core_doctypes_list,
			"Accounting Dimension",
			"Project",
			"Cost Center",
			"Accounting Dimension Detail",
			"Company",
			"Account",
		):
			msg = _("Not allowed to create accounting dimension for {0}").format(self.document_type)
			frappe.throw(msg)

		exists = frappe.db.get_value("Accounting Dimension", {"document_type": self.document_type}, ["name"])

		if exists and self.is_new():
			frappe.throw(_("Document Type already used as a dimension"))

		if not self.is_new():
			self.validate_document_type_change()

		validate_column_name(self.fieldname)
		self.validate_dimension_defaults()

	def validate_document_type_change(self):
		doctype_before_save = frappe.db.get_value("Accounting Dimension", self.name, "document_type")
		if doctype_before_save != self.document_type:
			message = _("Cannot change Reference Document Type.")
			message += _("Please create a new Accounting Dimension if required.")
			frappe.throw(message)

	def validate_dimension_defaults(self):
		companies = []
		for default in self.get("dimension_defaults"):
			if default.company not in companies:
				companies.append(default.company)
			else:
				frappe.throw(_("Company {0} is added more than once").format(frappe.bold(default.company)))

	def after_insert(self):
		if frappe.flags.in_test:
			make_dimension_in_accounting_doctypes(doc=self)
		else:
			frappe.enqueue(
				make_dimension_in_accounting_doctypes, doc=self, queue="long", enqueue_after_commit=True
			)

	def on_trash(self):
		if frappe.flags.in_test:
			delete_accounting_dimension(doc=self)
		else:
			frappe.enqueue(delete_accounting_dimension, doc=self, queue="long", enqueue_after_commit=True)

	def set_fieldname_and_label(self):
		if not self.label:
			self.label = cstr(self.document_type)

		if not self.fieldname:
			self.fieldname = scrub(self.label)

	def on_update(self):
		frappe.flags.accounting_dimensions = None


def make_dimension_in_accounting_doctypes(doc, doclist=None):
	if not doclist:
		doclist = get_doctypes_with_dimensions()

	doc_count = len(get_accounting_dimensions())
	count = 0
	repostable_doctypes = get_allowed_types_from_settings()

	for doctype in doclist:
		if (doc_count + 1) % 2 == 0:
			insert_after_field = "dimension_col_break"
		else:
			insert_after_field = "accounting_dimensions_section"

		df = {
			"fieldname": doc.fieldname,
			"label": doc.label,
			"fieldtype": "Link",
			"options": doc.document_type,
			"insert_after": insert_after_field,
			"owner": "Administrator",
			"allow_on_submit": 1 if doctype in repostable_doctypes else 0,
		}

		meta = frappe.get_meta(doctype, cached=False)
		fieldnames = [d.fieldname for d in meta.get("fields")]

		if df["fieldname"] not in fieldnames:
			if doctype == "Budget":
				add_dimension_to_budget_doctype(df.copy(), doc)
			else:
				create_custom_field(doctype, df, ignore_validate=True)

		count += 1

		frappe.publish_progress(count * 100 / len(doclist), title=_("Creating Dimensions..."))
		frappe.clear_cache(doctype=doctype)


def add_dimension_to_budget_doctype(df, doc):
	df.update(
		{
			"insert_after": "cost_center",
			"depends_on": f"eval:doc.budget_against == '{doc.document_type}'",
		}
	)

	create_custom_field("Budget", df, ignore_validate=True)

	property_setter = frappe.db.exists("Property Setter", "Budget-budget_against-options")

	if property_setter:
		property_setter_doc = frappe.get_doc("Property Setter", "Budget-budget_against-options")
		property_setter_doc.value = property_setter_doc.value + "\n" + doc.document_type
		property_setter_doc.save()

		frappe.clear_cache(doctype="Budget")
	else:
		frappe.get_doc(
			{
				"doctype": "Property Setter",
				"doctype_or_field": "DocField",
				"doc_type": "Budget",
				"field_name": "budget_against",
				"property": "options",
				"property_type": "Text",
				"value": "\nCost Center\nProject\n" + doc.document_type,
			}
		).insert(ignore_permissions=True)


def delete_accounting_dimension(doc):
	doclist = get_doctypes_with_dimensions()

	frappe.db.sql(
		"""
		DELETE FROM `tabCustom Field`
		WHERE fieldname = {}
		AND dt IN ({})""".format("%s", ", ".join(["%s"] * len(doclist))),  # nosec
		tuple([doc.fieldname, *doclist]),
	)

	frappe.db.sql(
		"""
		DELETE FROM `tabProperty Setter`
		WHERE field_name = {}
		AND doc_type IN ({})""".format("%s", ", ".join(["%s"] * len(doclist))),  # nosec
		tuple([doc.fieldname, *doclist]),
	)

	budget_against_property = frappe.get_doc("Property Setter", "Budget-budget_against-options")
	value_list = budget_against_property.value.split("\n")[3:]

	if doc.document_type in value_list:
		value_list.remove(doc.document_type)

	budget_against_property.value = "\nCost Center\nProject\n" + "\n".join(value_list)
	budget_against_property.save()

	for doctype in doclist:
		frappe.clear_cache(doctype=doctype)


@frappe.whitelist()
def disable_dimension(doc):
	if frappe.flags.in_test:
		toggle_disabling(doc=doc)
	else:
		frappe.enqueue(toggle_disabling, doc=doc)


def toggle_disabling(doc):
	doc = json.loads(doc)

	if doc.get("disabled"):
		df = {"read_only": 1}
	else:
		df = {"read_only": 0}

	doclist = get_doctypes_with_dimensions()

	for doctype in doclist:
		field = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": doc.get("fieldname")})
		if field:
			custom_field = frappe.get_doc("Custom Field", field)
			custom_field.update(df)
			custom_field.save()

		frappe.clear_cache(doctype=doctype)


def get_doctypes_with_dimensions():
	return frappe.get_hooks("accounting_dimension_doctypes")


def get_accounting_dimensions(as_list=True, filters=None):
	if not filters:
		filters = {"disabled": 0}

	if frappe.flags.accounting_dimensions is None:
		frappe.flags.accounting_dimensions = frappe.get_all(
			"Accounting Dimension",
			fields=["label", "fieldname", "disabled", "document_type"],
			filters=filters,
		)

	if as_list:
		return [d.fieldname for d in frappe.flags.accounting_dimensions]
	else:
		return frappe.flags.accounting_dimensions


def get_checks_for_pl_and_bs_accounts():
	if frappe.flags.accounting_dimensions_details is None:
		# nosemgrep
		frappe.flags.accounting_dimensions_details = frappe.db.sql(
			"""SELECT p.label, p.disabled, p.fieldname, c.default_dimension, c.company, c.mandatory_for_pl, c.mandatory_for_bs
			FROM `tabAccounting Dimension`p ,`tabAccounting Dimension Detail` c
			WHERE p.name = c.parent""",
			as_dict=1,
		)

	return frappe.flags.accounting_dimensions_details


def get_dimension_with_children(doctype, dimensions):
	if isinstance(dimensions, str):
		dimensions = [dimensions]

	all_dimensions = []

	for dimension in dimensions:
		lft, rgt = frappe.db.get_value(doctype, dimension, ["lft", "rgt"])
		children = frappe.get_all(doctype, filters={"lft": [">=", lft], "rgt": ["<=", rgt]}, order_by="lft")
		all_dimensions += [c.name for c in children]

	return all_dimensions


@frappe.whitelist()
def get_dimensions(with_cost_center_and_project=False):
	c = frappe.qb.DocType("Accounting Dimension Detail")
	p = frappe.qb.DocType("Accounting Dimension")
	dimension_filters = (
		frappe.qb.from_(p).select(p.label, p.fieldname, p.document_type).where(p.disabled == 0).run(as_dict=1)
	)
	default_dimensions = (
		frappe.qb.from_(c)
		.inner_join(p)
		.on(c.parent == p.name)
		.select(p.fieldname, c.company, c.default_dimension)
		.run(as_dict=1)
	)

	if isinstance(with_cost_center_and_project, str):
		if with_cost_center_and_project.lower().strip() == "true":
			with_cost_center_and_project = True
		else:
			with_cost_center_and_project = False

	if with_cost_center_and_project:
		dimension_filters.extend(
			[
				{"fieldname": "cost_center", "document_type": "Cost Center"},
				{"fieldname": "project", "document_type": "Project"},
			]
		)

	default_dimensions_map = {}
	for dimension in default_dimensions:
		default_dimensions_map.setdefault(dimension.company, {})
		default_dimensions_map[dimension.company][dimension.fieldname] = dimension.default_dimension

	return dimension_filters, default_dimensions_map


def create_accounting_dimensions_for_doctype(doctype):
	accounting_dimensions = frappe.db.get_all(
		"Accounting Dimension", fields=["fieldname", "label", "document_type", "disabled"]
	)

	if not accounting_dimensions:
		return

	for d in accounting_dimensions:
		field = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": d.fieldname})

		if field:
			continue

		df = {
			"fieldname": d.fieldname,
			"label": d.label,
			"fieldtype": "Link",
			"options": d.document_type,
			"insert_after": "accounting_dimensions_section",
		}

		create_custom_field(doctype, df, ignore_validate=True)

	frappe.clear_cache(doctype=doctype)
