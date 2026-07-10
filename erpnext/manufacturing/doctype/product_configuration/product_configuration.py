import operator

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

import erpnext
from erpnext.manufacturing.doctype.product_configuration.formula import build_context, evaluate
from erpnext.manufacturing.doctype.product_configuration_template.product_configuration_template import (
	attribute_masters,
)

TEMPLATE_DOCTYPE = "Product Configuration Template"
RULE_DOCTYPE = "Product Configuration Rule"
NUMERIC_VALUE_TYPES = ("Float", "Int", "Currency", "Check")

COMPARATORS = {
	"==": operator.eq,
	"!=": operator.ne,
	">": operator.gt,
	">=": operator.ge,
	"<": operator.lt,
	"<=": operator.le,
}


class ProductConfiguration(Document):
	def validate(self):
		if not self.title:
			self.title = self.template

	@frappe.whitelist()
	def fetch_template_attributes(self) -> int:
		self.set("attribute_values", [])
		for row in self.template_attributes():
			self.append("attribute_values", {"attribute": row.attribute, "value": row.default_value})
		return len(self.attribute_values)

	@frappe.whitelist()
	def calculate_components(self) -> dict:
		self.validate_mandatory_values()
		self.validate_value_limits()
		context = self.formula_context()
		self.set("components", [])
		for component in apply_rules(self.template, context):
			self.append("components", component)
		self.status = "Calculated"
		return {"components": len(self.components)}

	@frappe.whitelist()
	def create_bom(self) -> str:
		item = frappe.db.get_value(TEMPLATE_DOCTYPE, self.template, "configurable_item")
		if not item:
			frappe.throw(_("Set Configurable Item on template {0} to create a BOM").format(self.template))
		if not self.components:
			frappe.throw(_("Calculate the components before creating a BOM"))

		bom = frappe.new_doc("BOM")
		bom.item = item
		bom.company = erpnext.get_default_company() or frappe.db.get_value(
			"Item Default", {"parent": item, "parenttype": "Item"}, "company"
		)
		for component in self.components:
			bom.append(
				"items",
				{"item_code": component.component_item, "qty": component.qty, "uom": component.uom},
			)
		bom.insert()

		self.bom = bom.name
		self.status = "BOM Created"
		self.save()
		return bom.name

	def validate_mandatory_values(self):
		values = {row.attribute: row.value for row in self.attribute_values}
		missing = [
			row.attribute
			for row in self.template_attributes()
			if row.mandatory and values.get(row.attribute) in (None, "")
		]
		if missing:
			frappe.throw(_("Fill values for the mandatory attributes: {0}").format(", ".join(missing)))

	def validate_value_limits(self):
		limits = {row.attribute: row for row in self.template_attributes()}
		masters = attribute_masters([row.attribute for row in self.attribute_values])
		problems = []
		for row in self.attribute_values:
			problem = value_problem(row, limits.get(row.attribute), masters.get(row.attribute))
			if problem:
				problems.append(problem)
		if problems:
			frappe.throw(_("Fix these values before calculating: {0}").format("; ".join(problems)))

	def template_attributes(self) -> list:
		return frappe.get_all(
			"Product Configuration Template Attribute",
			filters={"parent": self.template, "parenttype": TEMPLATE_DOCTYPE},
			fields=["attribute", "default_value", "mandatory", "min_value", "max_value"],
			order_by="idx asc",
		)

	def formula_context(self) -> dict:
		values = {
			row.variable_name: cast_value(row.value, row.value_type)
			for row in self.attribute_values
			if row.variable_name
		}
		return build_context(values, template_variables(self.template))


def value_problem(row, limits, master) -> str | None:
	if row.value in (None, "") or not master:
		return None
	if master.value_type == "Select":
		return select_problem(row, master)
	if master.value_type in NUMERIC_VALUE_TYPES:
		return range_problem(row, limits)
	return None


def select_problem(row, master) -> str | None:
	options = [option.strip() for option in (master.select_options or "").splitlines() if option.strip()]
	if options and row.value not in options:
		return _("{0} must be one of {1}").format(row.attribute, ", ".join(options))
	return None


def range_problem(row, limits) -> str | None:
	if not limits:
		return None
	value = flt(row.value)
	if limits.min_value and value < limits.min_value:
		return _("{0} must be at least {1}").format(row.attribute, limits.min_value)
	if limits.max_value and value > limits.max_value:
		return _("{0} must be at most {1}").format(row.attribute, limits.max_value)
	return None


def cast_value(value, value_type):
	if value in (None, ""):
		return 0 if value_type in NUMERIC_VALUE_TYPES else ""
	if value_type in ("Float", "Currency"):
		return flt(value)
	if value_type in ("Int", "Check"):
		return cint(value)
	return value


def template_variables(template: str) -> list:
	return frappe.get_all(
		"Product Configuration Template Variable",
		filters={"parent": template, "parenttype": TEMPLATE_DOCTYPE},
		fields=["variable_name", "formula"],
		order_by="idx asc",
	)


def build_dummy_context(template: str) -> dict:
	attributes = frappe.get_all(
		"Product Configuration Template Attribute",
		filters={"parent": template, "parenttype": TEMPLATE_DOCTYPE},
		fields=["variable_name"],
	)
	values = {row.variable_name: 1.0 for row in attributes if row.variable_name}
	return build_context(values, template_variables(template))


def apply_rules(template: str, context: dict) -> list:
	rules = frappe.get_all(
		RULE_DOCTYPE,
		filters={"template": template, "active": 1},
		fields=["name", "condition_logic"],
		order_by="priority asc, creation asc",
	)
	if not rules:
		return []

	rule_names = [rule.name for rule in rules]
	conditions = group_by_parent(
		frappe.get_all(
			"Product Configuration Rule Condition",
			filters={"parent": ["in", rule_names], "parenttype": RULE_DOCTYPE},
			fields=["parent", "variable_name", "operator", "value"],
		)
	)
	outputs = group_by_parent(
		frappe.get_all(
			"Product Configuration Rule Output",
			filters={"parent": ["in", rule_names], "parenttype": RULE_DOCTYPE},
			fields=["parent", "component_item", "uom", "quantity_formula"],
		)
	)

	matched = []
	for rule in rules:
		if rule_matches(rule, conditions.get(rule.name, []), context):
			matched.extend(run_outputs(rule, outputs.get(rule.name, []), context))
	return aggregate_components(matched)


def group_by_parent(rows: list) -> dict:
	grouped = {}
	for row in rows:
		grouped.setdefault(row.parent, []).append(row)
	return grouped


def rule_matches(rule, conditions: list, context: dict) -> bool:
	checks = [condition_holds(condition, context) for condition in conditions]
	if not checks:
		return True
	return all(checks) if rule.condition_logic == "All conditions" else any(checks)


def condition_holds(condition, context: dict) -> bool:
	left = context.get(condition.variable_name)
	if condition.operator in COMPARATORS:
		try:
			return COMPARATORS[condition.operator](left, coerce_value(condition.value, left))
		except TypeError:
			return False

	options = [item.strip() for item in (condition.value or "").split(",")]
	matched = str(left) in options
	return matched if condition.operator == "in" else not matched


def coerce_value(raw, reference):
	if isinstance(reference, bool):
		return raw
	if isinstance(reference, int | float):
		try:
			return float(raw)
		except (TypeError, ValueError):
			return raw
	return raw


def run_outputs(rule, outputs: list, context: dict) -> list:
	components = []
	for output in outputs:
		result = evaluate(output.quantity_formula, context)
		if not result["ok"]:
			frappe.throw(_("Invalid quantity formula in rule {0}: {1}").format(rule.name, result["error"]))

		qty = flt(result["value"])
		if qty <= 0:
			continue

		components.append(
			{
				"component_item": output.component_item,
				"qty": qty,
				"uom": output.uom,
				"source_rule": rule.name,
			}
		)
	return components


def aggregate_components(components: list) -> list:
	aggregated = {}
	order = []
	for component in components:
		key = (component["component_item"], component["uom"])
		if key in aggregated:
			aggregated[key]["qty"] += component["qty"]
		else:
			aggregated[key] = dict(component)
			order.append(key)
	return [aggregated[key] for key in order]
