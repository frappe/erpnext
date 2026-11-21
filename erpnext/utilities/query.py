import frappe


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
