# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html
from frappe.utils.jinja import safe_render_flags, set_filters
from jinja2 import DebugUndefined, nodes
from jinja2.sandbox import SandboxedEnvironment

from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import (
	format_terms_value,
	get_attribute_path,
	has_global,
)

LETTER_UTILS = (
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


class DunningLetterText(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		body_text: DF.TextEditor | None
		closing_text: DF.TextEditor | None
		is_default_language: DF.Check
		language: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	pass


def render_letter_text(template, context, dunning_type):
	if not template:
		return ""

	try:
		with safe_render_flags():
			return get_letter_environment().from_string(template).render(context)
	except Exception as e:
		# the error can echo template text, which must not reach the message as HTML
		frappe.throw(
			_("Dunning Letter Text of Dunning Type {0} could not be rendered: {1}").format(
				frappe.bold(dunning_type), escape_html(str(e))
			)
		)


def validate_letter_globals(template):
	jenv = get_letter_environment()
	for node in jenv.parse(template).find_all(nodes.Getattr):
		path = get_attribute_path(node)
		if path and path[0] == "frappe" and not has_global(jenv.globals, path):
			frappe.throw(_("{0} cannot be used in Dunning Letter Text").format(frappe.bold(".".join(path))))


def get_letter_environment():
	# Letter authors must not inherit the renderer's database or server capabilities.
	jenv = SandboxedEnvironment(undefined=DebugUndefined)
	set_filters(jenv)
	jenv.globals.update(
		_=frappe._,
		frappe=dict(
			format=format_terms_value,
			format_value=format_terms_value,
			format_date=frappe.utils.global_date_format,
			bold=frappe.bold,
			utils={name: getattr(frappe.utils, name) for name in LETTER_UTILS},
		),
	)
	return jenv
