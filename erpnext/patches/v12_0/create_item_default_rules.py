import frappe
from frappe import scrub
from erpnext import get_default_company
from erpnext.setup.doctype.item_default_rule.item_default_rule import filter_fields


def execute():
	frappe.reload_doc('setup', 'doctype', 'item_default_rule')

	rules = {}

	# From Item Defaults child table
	item_defaults = frappe.get_all("Item Default", fields="*")
	for d in item_defaults:
		update_rule_value(rules, d.parenttype, d.parent, d)

	# From Item Tax child table
	item_taxes = frappe.get_all("Item Tax", fields="*", filters={"parenttype": ['in', ['Item', 'Item Group']]},
		order_by="idx")
	for t in item_taxes:
		add_rule_tax(rules, t.parenttype, t.parent, t)

	# From Item masters
	items = frappe.get_all("Item", fields=["name", "show_item_code"])
	for d in items:
		update_rule_value(rules, "Item", d.name, d)

	# From Item Groups
	item_groups = frappe.get_all("Item Group", fields="*")
	for d in item_groups:
		update_rule_value(rules, "Item Group", d.name, d)

	# From Brands
	brands = frappe.get_all("Brand", fields="*")
	for d in brands:
		update_rule_value(rules, "Brand", d.name, d)

	# From Item Sources
	item_sources = frappe.get_all("Item Source", fields="*")
	for d in item_sources:
		update_rule_value(rules, "Item Source", d.name, d)

	# From Transaction Types
	transaction_types = frappe.get_all("Transaction Type", fields="*")
	for d in transaction_types:
		update_rule_value(rules, "Transaction Type", d.name, d)

	# Remove rules with only one value: Income Account set as company default
	default_income_account = frappe.db.get_value("Company", get_default_company(), 'default_income_account')
	to_remove = []
	for rule_name, rule_detail in rules.items():
		remove = True
		for k, v in rule_detail.items():
			if k in filter_fields or k == 'item_default_rule_name':
				continue
			if k == "income_account" and v == default_income_account:
				continue
			if k == "show_item_code" and rule_detail.get('item_code') and not rule_detail.get('item_group') \
					and not rule_detail.get('item_source') and not rule_detail.get('brand') and not rule_detail.get('transaction_type'):
				continue

			remove = False

		if remove:
			to_remove.append(rule_name)

	for rule_name in to_remove:
		rules.pop(rule_name)

	print(frappe.as_json(rules))

	# Insert the rules in database
	for rule_detail in rules.values():
		doc = frappe.new_doc("Item Default Rule")
		doc.update(rule_detail)
		doc.insert()


def update_rule_value(rules, dt, name, d):
	rule_meta = frappe.get_meta("Item Default Rule")
	rule_name = get_rule_name(dt, name)
	for k, v in d.items():
		if k in ["company"]:
			continue

		if rule_meta.has_field(k) and k not in filter_fields and v:
			rule_template = get_rule_template(rule_name, dt, name)
			rule_dict = rules.setdefault(rule_name, rule_template)
			rule_dict[k] = v


def add_rule_tax(rules, dt, name, tax):
	item_tax_meta = frappe.get_meta("Item Tax")
	tax_detail = {}
	for k, v in tax.items():
		if item_tax_meta.has_field(k) and v:
			tax_detail[k] = v

	if tax_detail:
		rule_name = get_rule_name(dt, name)
		rule_template = get_rule_template(rule_name, dt, name)
		rule_dict = rules.setdefault(rule_name, rule_template)
		rule_tax_list = rule_dict.setdefault('taxes', [])

		rule_tax_list.append(tax_detail)


def get_rule_template(rule_name, dt, name):
	rule_template = {
		'item_default_rule_name': rule_name,
	}
	if not (dt == "Item Group" and name == "All Item Groups"):
		filter_fieldname = "item_code" if dt == "Item" else scrub(dt)
		rule_template[filter_fieldname] = name

	return rule_template


def get_rule_name(dt, name):
	if dt == "Item Group" and name == "All Item Groups":
		return "Applicable to All Items"
	else:
		return "{0}: {1}".format(dt, name)
