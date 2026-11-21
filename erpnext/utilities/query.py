import frappe
from frappe.permissions import get_allowed_docs_for_doctype, get_user_permissions
from frappe.query_builder.functions import IfNull
from pypika.terms import Criterion, ExistsCriterion


def get_user_permission_conditions_qb(doctype, table):
	user_permissions = get_user_permissions(frappe.session.user)
	if not user_permissions:
		return []

	link_fields = [
		frappe._dict(fieldname="name", options=doctype),
		*frappe.get_meta(doctype).get_link_fields(),
	]
	refused = get_refused_link_conditions(table, link_fields, doctype, user_permissions)
	conditions = [Criterion.any(refused).negate()] if refused else []
	return conditions + get_child_user_permission_conditions_qb(doctype, table, user_permissions)


def get_child_user_permission_conditions_qb(doctype, table, user_permissions):
	conditions = []
	for table_field in frappe.get_meta(doctype).get_table_fields():
		child = frappe.qb.DocType(table_field.options).as_(f"restricted_{table_field.fieldname}")
		link_fields = frappe.get_meta(table_field.options).get_link_fields()
		refused = get_refused_link_conditions(child, link_fields, doctype, user_permissions)
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


def get_refused_link_conditions(table, link_fields, doctype, user_permissions):
	strict = frappe.get_system_settings("apply_strict_user_permissions")
	conditions = []
	for field in link_fields:
		if field.ignore_user_permissions:
			continue
		allowed = get_allowed_docs_for_doctype(user_permissions.get(field.options, []), doctype)
		if allowed:
			value = IfNull(table[field.fieldname], "")
			conditions.append(value.notin(allowed) if strict else (value != "") & value.notin(allowed))
	return conditions
