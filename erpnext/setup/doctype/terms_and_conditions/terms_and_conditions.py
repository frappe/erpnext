# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _, throw
from frappe.model import get_permitted_fields
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.data import make_filter_tuple
from frappe.utils.jinja import safe_render_flags, set_filters, validate_template
from jinja2 import DebugUndefined, nodes
from jinja2.sandbox import SandboxedEnvironment


class TermsandConditions(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		buying: DF.Check
		copy_attachments_to_transaction: DF.Check
		disabled: DF.Check
		selling: DF.Check
		terms: DF.TextEditor | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if self.terms:
			validate_template(self.terms, restrict_globals=True)
			validate_terms_globals(self.terms)
		if not cint(self.disabled) and not any(
			cint(self.get(module)) for module in ("buying", "selling", "hr")
		):
			throw(_("At least one of the Applicable Modules should be selected"))


@frappe.whitelist()
def get_terms_and_conditions(template_name, doc):
	if isinstance(doc, str):
		doc = json.loads(doc)

	tnc = frappe.get_cached_doc("Terms and Conditions", template_name)
	tnc.check_permission()
	validate_terms_and_conditions(template_name, get_terms_module(doc))

	if not tnc.terms:
		return

	if ".__" in tnc.terms:
		throw(_("Illegal template"))

	with safe_render_flags():
		return get_terms_environment(tnc.modified_by).from_string(tnc.terms).render(doc)


def get_terms_environment(author):
	# Terms editors must not inherit the renderer's database or server capabilities.
	jenv = SandboxedEnvironment(undefined=DebugUndefined)
	set_filters(jenv)

	def get_list(doctype, filters=None, fields=None, order_by=None, limit_page_length=20):
		return get_terms_list(author, doctype, filters, fields, order_by, limit_page_length)

	jenv.globals.update(
		_=frappe._,
		frappe=dict(
			format=format_terms_value,
			format_value=format_terms_value,
			format_date=frappe.utils.global_date_format,
			bold=frappe.bold,
			utils=dict(
				(name, getattr(frappe.utils, name))
				for name in (
					"cint",
					"cstr",
					"flt",
					"fmt_money",
					"formatdate",
					"format_date",
					"format_time",
					"format_datetime",
					"getdate",
					"get_datetime",
					"today",
					"nowdate",
					"add_days",
					"add_months",
					"add_years",
					"date_diff",
					"strip_html",
					"escape_html",
					"money_in_words",
				)
			),
			get_list=get_list,
			db=dict(get_list=get_list),
		),
	)
	return jenv


def validate_terms_globals(terms):
	"""Refuse `frappe` attributes that the terms sandbox does not provide, so the template can render."""
	jenv = get_terms_environment(None)
	for node in jenv.parse(terms).find_all(nodes.Getattr):
		path = get_attribute_path(node)
		if path and path[0] == "frappe" and not has_global(jenv.globals, path):
			throw(_("{0} cannot be used in Terms and Conditions").format(frappe.bold(".".join(path))))


def get_attribute_path(node):
	path = []
	while isinstance(node, nodes.Getattr):
		path.insert(0, node.attr)
		node = node.node

	return [node.name, *path] if isinstance(node, nodes.Name) else None


def has_global(jenv_globals, path):
	value = jenv_globals
	for name in path:
		# attributes of helpers are checked by the sandbox when rendering
		if not isinstance(value, dict):
			return True
		if name not in value:
			return False
		value = value[name]

	return True


def format_terms_value(value, df=None, doc=None, currency=None, translated=False, format=None):
	"""Format supplied values without resolving document references through unchecked database reads."""
	return frappe.format_value(value, df=df, currency=currency, translated=translated, format=format)


def get_terms_list(author, doctype, filters=None, fields=None, order_by=None, limit_page_length=20):
	"""Read simple fields and records permitted to both the template editor and the caller."""
	author = author or "Guest"
	frappe.has_permission(doctype, "read", user=author, throw=True)
	frappe.has_permission(doctype, "read", throw=True)
	permitted_fields = set(get_permitted_fields(doctype, user=author, permission_type="read")) & set(
		get_permitted_fields(doctype, permission_type="read")
	)
	# A privileged renderer must not unmask a field for a less privileged editor.
	meta = frappe.get_meta(doctype)
	permitted_fields -= {df.fieldname for df in meta.fields if df.get("mask")}
	permitted_fields -= {df.fieldname for df in meta.fields if df.fieldtype == "Password"}
	fields = fields or ["name"]
	if isinstance(fields, str):
		fields = [fields]
	if not isinstance(filters, dict | type(None)):
		throw(_("Terms and Conditions queries require dictionary filters"), frappe.PermissionError)
	if fields == ["*"]:
		fields = sorted(permitted_fields)
	query_fields = set(fields) | set(filters or {})
	if order_by:
		for clause in order_by.split(","):
			parts = clause.strip().split()
			if len(parts) not in (1, 2) or (len(parts) == 2 and parts[1].lower() not in ("asc", "desc")):
				throw(_("Invalid Terms and Conditions query order"), frappe.PermissionError)
			query_fields.add(parts[0])
	if not query_fields.issubset(permitted_fields):
		throw(_("Not permitted to query these fields in Terms and Conditions"), frappe.PermissionError)
	if editor_reads_all_records(doctype, author):
		return frappe.get_list(
			doctype, fields=fields, filters=filters, order_by=order_by, limit_page_length=limit_page_length
		)

	# v15 list queries are SQL strings, so scope the caller's query to the editor's records by name.
	author_names = frappe.get_list(
		doctype, fields=["name"], filters=filters, user=author, order_by="", limit_page_length=0, pluck="name"
	)
	if not author_names:
		return []
	query_filters = [make_filter_tuple(doctype, key, value) for key, value in (filters or {}).items()]
	query_filters.append([doctype, "name", "in", author_names])
	return frappe.get_list(
		doctype,
		fields=fields,
		filters=query_filters,
		order_by=order_by,
		limit_page_length=limit_page_length,
	)


def editor_reads_all_records(doctype, author):
	"""Return True when the editor's read access to the doctype has no record-level restriction."""
	from frappe.desk.reportview import build_match_conditions

	role_permissions = frappe.permissions.get_role_permissions(frappe.get_meta(doctype), user=author)
	if not (role_permissions.get("read") or role_permissions.get("select")):
		return False

	return not build_match_conditions(doctype, user=author)


def validate_terms_and_conditions(template_name, module=None):
	if not template_name:
		return
	tnc = frappe.get_cached_doc("Terms and Conditions", template_name)
	if cint(tnc.disabled):
		throw(_("Terms and Conditions {0} is disabled").format(frappe.bold(template_name)))
	if module and not cint(tnc.get(module)):
		throw(
			_("Terms and Conditions {0} is not applicable to {1}").format(
				frappe.bold(template_name), _("Selling") if module == "selling" else _("Buying")
			)
		)


def clear_inapplicable_terms(doc):
	"""Clear a template mapped from the other side, and the terms rendered from it."""
	module = get_terms_module(doc)
	tc_name = doc.get("tc_name")
	if module and tc_name and not cint(frappe.get_cached_value("Terms and Conditions", tc_name, module)):
		doc.tc_name = None
		doc.terms = None


def get_terms_module(doc):
	doctype = doc.get("doctype")
	if doctype in (
		"Quotation",
		"Sales Order",
		"Delivery Note",
		"Sales Invoice",
		"POS Invoice",
		"POS Profile",
	):
		return "selling"
	if doctype in (
		"Supplier Quotation",
		"Purchase Order",
		"Purchase Receipt",
		"Purchase Invoice",
		"Request for Quotation",
		"Material Request",
	):
		return "buying"
	if doctype == "Blanket Order":
		return "selling" if doc.get("blanket_order_type") == "Selling" else "buying"
