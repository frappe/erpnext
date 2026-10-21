# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, throw
from frappe.model import get_permitted_fields
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.jinja import safe_render_flags, set_filters, validate_template
from jinja2 import DebugUndefined
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
		if not cint(self.disabled) and not any(
			cint(self.get(module)) for module in ("buying", "selling", "hr")
		):
			throw(_("At least one of the Applicable Modules should be selected"))


@frappe.whitelist()
def get_terms_and_conditions(template_name: str, doc: str | dict):
	doc = frappe.parse_json(doc)

	tnc = frappe.get_cached_doc("Terms and Conditions", template_name)
	tnc.check_permission()

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
	author_query = frappe.get_list(
		doctype, fields=["name"], user=author, order_by="", limit_page_length=0, run=False
	)
	query = frappe.get_list(
		doctype,
		fields=fields,
		filters=filters,
		order_by=order_by,
		limit_page_length=limit_page_length,
		run=False,
	)
	return query.where(frappe.qb.DocType(doctype).name.isin(author_query)).run(as_dict=True)
