# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Query-builder helpers for permission & filter conditions.

These are ERPNext-local because they are only consumed by ERPNext. They return
``pypika`` criteria (rather than the raw SQL strings produced by
``frappe.desk.reportview.get_match_cond`` / ``get_filters_cond``) so the conditions
can be applied to any ``frappe.qb`` query via ``.where(...)`` — including joins and
aliased queries where the permission-checked doctype is not the single base of
``frappe.qb.get_query``.

They are thin wrappers over ``frappe.database.query.Engine`` (``get_permission_conditions``
/ ``apply_filters``), which pre-date this code. Where the permission-checked doctype *is*
the base of the query, prefer ``frappe.qb.get_query(doctype, ignore_permissions=False)``
directly instead of these helpers.
"""

import json

import frappe
from frappe import _


def get_match_conditions_qb(doctype, table=None, user=None):
	"""Return user-permission match conditions for ``doctype`` as query-builder criteria.

	Query-builder equivalent of ``frappe.desk.reportview.get_match_cond`` /
	``build_match_conditions`` (which return raw SQL strings). Returns a list of pypika
	criteria (0 or 1 elements) covering role permissions, user permissions, sharing and the
	if-owner constraint as well as ``permission_query_conditions`` hooks/server scripts.

	Args:
	        doctype: doctype to build permission conditions for.
	        table: pypika table the conditions should reference. Defaults to
	                ``frappe.qb.DocType(doctype)``.
	        user: user to evaluate permissions for. Defaults to the session user.
	"""
	from frappe.database.query import Engine

	engine = Engine()
	engine.get_query(doctype, user=user, ignore_permissions=False, db_query_compat=True)
	condition = engine.get_permission_conditions(doctype, table or engine.table)
	return [condition] if condition is not None else []


def get_user_permission_conditions_qb(doctype, table=None):
	from frappe.database.query import Engine

	engine = Engine()
	engine.get_query(doctype)
	table = table or engine.table
	return engine.get_user_permission_conditions(doctype, table) + get_child_user_permission_conditions_qb(
		doctype, table
	)


def get_child_user_permission_conditions_qb(doctype, table):
	from frappe.permissions import get_user_permissions
	from pypika.terms import Criterion, ExistsCriterion

	user_permissions = get_user_permissions(frappe.session.user)
	if not user_permissions:
		return []

	conditions = []
	for table_field in frappe.get_meta(doctype).get_table_fields():
		child = frappe.qb.DocType(table_field.options).as_(f"restricted_{table_field.fieldname}")
		refused = get_refused_link_conditions(child, table_field.options, doctype, user_permissions)
		if refused:
			rows = (
				frappe.qb.from_(child)
				.select(child.name)
				.where(
					(child.parent == table.name)
					& (child.parenttype == doctype)
					& (child.parentfield == table_field.fieldname)
					& Criterion.any(refused)
				)
			)
			conditions.append(ExistsCriterion(rows).negate())
	return conditions


def get_refused_link_conditions(child, child_doctype, doctype, user_permissions):
	from frappe.permissions import get_allowed_docs_for_doctype
	from frappe.query_builder.functions import IfNull

	strict = frappe.get_system_settings("apply_strict_user_permissions")
	conditions = []
	for field in frappe.get_meta(child_doctype).get_link_fields():
		if field.ignore_user_permissions:
			continue
		allowed = get_allowed_docs_for_doctype(user_permissions.get(field.options, []), doctype)
		if allowed:
			value = IfNull(child[field.fieldname], "")
			conditions.append(value.notin(allowed) if strict else (value != "") & value.notin(allowed))
	return conditions


def get_filter_conditions_qb(doctype, filters, ignore_permissions=None):
	"""Return ``filters`` for ``doctype`` as a list of query-builder criteria.

	Query-builder equivalent of ``frappe.desk.reportview.get_filters_cond`` (which returns a
	raw SQL string). Accepts the standard frappe filter forms (dict, or list of
	``[doctype, field, op, value]`` rows) and returns pypika criteria that can be applied to
	any ``frappe.qb`` query via ``.where(...)``.
	"""
	if not filters:
		return []

	from pypika.terms import Criterion

	# A pypika Criterion is already a usable condition; apply_filters would route it straight to
	# the query and never populate `collect`, silently returning []. Hand it back as-is instead.
	if isinstance(filters, Criterion):
		return [filters]

	filters = frappe.parse_json(filters)

	if isinstance(filters, dict):
		# Mirror get_filters_cond's dict normalization: a string value prefixed with "!" means
		# "not equal" (e.g. {"enabled": "!1"} -> enabled != "1"). apply_filters' dict path would
		# otherwise treat "!1" as a literal value and emit `enabled = "!1"`.
		filters = {
			field: ("!=", value[1:]) if isinstance(value, str) and value.startswith("!") else value
			for field, value in filters.items()
		}

	from frappe.database.query import Engine

	engine = Engine()
	engine.get_query(doctype, ignore_permissions=ignore_permissions, db_query_compat=True)
	criteria = []
	engine.apply_filters(filters, collect=criteria)
	return criteria


def get_event_conditions_qb(doctype, filters=None):
	"""Return user-permission match conditions + ``filters`` for event/calendar queries.

	Query-builder equivalent of ``frappe.desk.calendar.get_event_conditions(..., as_qb=True)``:
	a list of pypika criteria suitable for applying to a ``frappe.qb`` query via ``.where(...)``
	(e.g. calendar feeds that join across multiple doctypes).
	"""
	if not frappe.has_permission(doctype):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	return get_match_conditions_qb(doctype) + get_filter_conditions_qb(doctype, filters)
