# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, copy, json
from frappe import throw, _
from six import string_types
from frappe.utils import flt, cint, get_datetime
from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses
from erpnext.stock.get_item_details import get_conversion_factor

class MultiplePricingRuleConflict(frappe.ValidationError): pass

apply_on_table = {
    'Item Code': 'items',
    'Item Group': 'item_groups',
    'Brand': 'brands'
}

def get_pricing_rules(args, doc=None):
	pricing_rules = []
	values =  {}

	for apply_on in ['Item Code', 'Item Group', 'Brand']:
		pricing_rules.extend(_get_pricing_rules(apply_on, args, values))
		if pricing_rules and not apply_multiple_pricing_rules(pricing_rules):
			break

	rules = []

	if not pricing_rules: return []

	if apply_multiple_pricing_rules(pricing_rules):
		for pricing_rule in pricing_rules:
			pricing_rule = filter_pricing_rules(args, pricing_rule, doc)
			if pricing_rule:
				rules.append(pricing_rule)
	else:
		pricing_rule = filter_pricing_rules(args, pricing_rules, doc)
		if pricing_rule:
			rules.append(pricing_rule)

	return rules

def _get_pricing_rules(apply_on, args, values):
	apply_on_field = frappe.scrub(apply_on)

	if not args.get(apply_on_field): return []

	child_doc = '`tabPricing Rule {0}`'.format(apply_on)

	conditions = item_variant_condition = item_conditions = ""
	values[apply_on_field] = args.get(apply_on_field)
	if apply_on_field in ['item_code', 'brand']:
		item_conditions = "{child_doc}.{apply_on_field}= %({apply_on_field})s".format(child_doc=child_doc,
			apply_on_field = apply_on_field)

		if apply_on_field == 'item_code':
			if "variant_of" not in args:
				args.variant_of = frappe.get_cached_value("Item", args.item_code, "variant_of")

			if args.variant_of:
				item_variant_condition = ' or {child_doc}.item_code=%(variant_of)s '.format(child_doc=child_doc)
				values['variant_of'] = args.variant_of
	elif apply_on_field == 'item_group':
		item_conditions = _get_tree_conditions(args, "Item Group", child_doc, False)

	conditions += get_other_conditions(conditions, values, args)
	warehouse_conditions = _get_tree_conditions(args, "Warehouse", '`tabPricing Rule`')
	if warehouse_conditions:
		warehouse_conditions = " and {0}".format(warehouse_conditions)

	if not args.price_list: args.price_list = None

	conditions += " and ifnull(`tabPricing Rule`.for_price_list, '') in (%(price_list)s, '')"
	values["price_list"] = args.get("price_list")

	pricing_rules = frappe.db.sql("""select `tabPricing Rule`.*,
			{child_doc}.{apply_on_field}, {child_doc}.uom
		from `tabPricing Rule`, {child_doc}
		where ({item_conditions} or (`tabPricing Rule`.apply_rule_on_other is not null
			and `tabPricing Rule`.{apply_on_other_field}=%({apply_on_field})s) {item_variant_condition})
			and {child_doc}.parent = `tabPricing Rule`.name
			and `tabPricing Rule`.disable = 0 and
			`tabPricing Rule`.{transaction_type} = 1 {warehouse_cond} {conditions}
		order by `tabPricing Rule`.priority desc,
			`tabPricing Rule`.name desc""".format(
			child_doc = child_doc,
			apply_on_field = apply_on_field,
			item_conditions = item_conditions,
			item_variant_condition = item_variant_condition,
			transaction_type = args.transaction_type,
			warehouse_cond = warehouse_conditions,
			apply_on_other_field = "other_{0}".format(apply_on_field),
			conditions = conditions), values, as_dict=1) or []

	return pricing_rules

def apply_multiple_pricing_rules(pricing_rules):
	apply_multiple_rule = [d.apply_multiple_pricing_rules
		for d in pricing_rules if d.apply_multiple_pricing_rules]

	if not apply_multiple_rule: return False

	if (apply_multiple_rule
		and len(apply_multiple_rule) == len(pricing_rules)):
		return True

def _get_tree_conditions(args, parenttype, table, allow_blank=True):
	field = frappe.scrub(parenttype)
	condition = ""
	if args.get(field):
		if not frappe.flags.tree_conditions:
			frappe.flags.tree_conditions = {}
		key = (parenttype, args.get(field))
		if key in frappe.flags.tree_conditions:
			return frappe.flags.tree_conditions[key]

		try:
			lft, rgt = frappe.db.get_value(parenttype, args.get(field), ["lft", "rgt"])
		except TypeError:
			frappe.throw(_("Invalid {0}").format(args.get(field)))

		parent_groups = frappe.db.sql_list("""select name from `tab%s`
			where lft<=%s and rgt>=%s""" % (parenttype, '%s', '%s'), (lft, rgt))

		if parent_groups:
			if allow_blank: parent_groups.append('')
			condition = "ifnull({table}.{field}, '') in ({parent_groups})".format(
				table=table,
				field=field,
				parent_groups=", ".join([frappe.db.escape(d) for d in parent_groups])
			)

			frappe.flags.tree_conditions[key] = condition
	return condition

def get_other_conditions(conditions, values, args):
	for field in ["company", "customer", "supplier", "campaign", "sales_partner"]:
		if args.get(field):
			conditions += " and ifnull(`tabPricing Rule`.{0}, '') in (%({1})s, '')".format(field, field)
			values[field] = args.get(field)
		else:
			conditions += " and ifnull(`tabPricing Rule`.{0}, '') = ''".format(field)

	for parenttype in ["Customer Group", "Territory", "Supplier Group"]:
		group_condition = _get_tree_conditions(args, parenttype, '`tabPricing Rule`')
		if group_condition:
			conditions += " and " + group_condition

	if args.get("transaction_date"):
		conditions += """ and %(transaction_date)s between ifnull(`tabPricing Rule`.valid_from, '2000-01-01')
			and ifnull(`tabPricing Rule`.valid_upto, '2500-12-31')"""
		values['transaction_date'] = args.get('transaction_date')

	return conditions

def filter_pricing_rules(args, pricing_rules, doc=None):
	if not isinstance(pricing_rules, list):
		pricing_rules = [pricing_rules]

	original_pricing_rule = copy.copy(pricing_rules)

	# filter for qty
	if pricing_rules:
		stock_qty = flt(args.get('stock_qty'))
		amount = flt(args.get('price_list_rate')) * flt(args.get('qty'))

		if pricing_rules[0].apply_rule_on_other:
			field = frappe.scrub(pricing_rules[0].apply_rule_on_other)

			if (field and pricing_rules[0].get('other_' + field) != args.get(field)): return

		pr_doc = frappe.get_doc('Pricing Rule', pricing_rules[0].name)

		if pricing_rules[0].mixed_conditions and doc:
			stock_qty, amount = get_qty_and_rate_for_mixed_conditions(doc, pr_doc, args)

		elif pricing_rules[0].is_cumulative:
			items = [args.get(frappe.scrub(pr_doc.get('apply_on')))]
			data = get_qty_amount_data_for_cumulative(pr_doc, args, items)

			if data:
				stock_qty += data[0]
				amount += data[1]

		if pricing_rules[0].apply_rule_on_other and not pricing_rules[0].mixed_conditions and doc:
			pricing_rules = get_qty_and_rate_for_other_item(doc, pr_doc, pricing_rules) or []
		else:
			pricing_rules = filter_pricing_rules_for_qty_amount(stock_qty, amount, pricing_rules, args)

		if not pricing_rules:
			for d in original_pricing_rule:
				if not d.threshold_percentage: continue

				msg = validate_quantity_and_amount_for_suggestion(d, stock_qty,
					amount, args.get('item_code'), args.get('transaction_type'))

				if msg:
					return {'suggestion': msg, 'item_code': args.get('item_code')}

		# add variant_of property in pricing rule
		for p in pricing_rules:
			if p.item_code and args.variant_of:
				p.variant_of = args.variant_of
			else:
				p.variant_of = None

	# find pricing rule with highest priority
	if pricing_rules:
		max_priority = max([cint(p.priority) for p in pricing_rules])
		if max_priority:
			pricing_rules = list(filter(lambda x: cint(x.priority)==max_priority, pricing_rules))

	# apply internal priority
	all_fields = ["item_code", "item_group", "brand", "customer", "customer_group", "territory",
		"supplier", "supplier_group", "campaign", "sales_partner", "variant_of"]

	if len(pricing_rules) > 1:
		for field_set in [["item_code", "variant_of", "item_group", "brand"],
			["customer", "customer_group", "territory"], ["supplier", "supplier_group"]]:
				remaining_fields = list(set(all_fields) - set(field_set))
				if if_all_rules_same(pricing_rules, remaining_fields):
					pricing_rules = apply_internal_priority(pricing_rules, field_set, args)
					break

	if pricing_rules and not isinstance(pricing_rules, list):
		pricing_rules = list(pricing_rules)

	if len(pricing_rules) > 1:
		rate_or_discount = list(set([d.rate_or_discount for d in pricing_rules]))
		if len(rate_or_discount) == 1 and rate_or_discount[0] == "Discount Percentage":
			pricing_rules = list(filter(lambda x: x.for_price_list==args.price_list, pricing_rules)) \
				or pricing_rules

	if len(pricing_rules) > 1 and not args.for_shopping_cart:
		frappe.throw(_("Multiple Price Rules exists with same criteria, please resolve conflict by assigning priority. Price Rules: {0}")
			.format("\n".join([d.name for d in pricing_rules])), MultiplePricingRuleConflict)
	elif pricing_rules:
		return pricing_rules[0]

def validate_quantity_and_amount_for_suggestion(args, qty, amount, item_code, transaction_type):
	fieldname, msg = '', ''
	type_of_transaction = 'purcahse' if transaction_type == "buying" else "sale"

	for field, value in {'min_qty': qty, 'min_amt': amount}.items():
		if (args.get(field) and value < args.get(field)
			and (args.get(field) - cint(args.get(field) * args.threshold_percentage * 0.01)) <= value):
			fieldname = field

	for field, value in {'max_qty': qty, 'max_amt': amount}.items():
		if (args.get(field) and value > args.get(field)
			and (args.get(field) + cint(args.get(field) * args.threshold_percentage * 0.01)) >= value):
			fieldname = field

	if fieldname:
		msg = _("""If you {0} {1} quantities of the item <b>{2}</b>, the scheme <b>{3}</b>
			will be applied on the item.""").format(type_of_transaction, args.get(fieldname), item_code, args.rule_description)

		if fieldname in ['min_amt', 'max_amt']:
			msg = _("""If you {0} {1} worth item <b>{2}</b>, the scheme <b>{3}</b> will be applied on the item.
				""").format(frappe.fmt_money(type_of_transaction, args.get(fieldname)), item_code, args.rule_description)

		frappe.msgprint(msg)

	return msg

def filter_pricing_rules_for_qty_amount(qty, rate, pricing_rules, args=None):
	rules = []

	for rule in pricing_rules:
		status = False
		conversion_factor = 1

		if rule.get("uom"):
			conversion_factor = get_conversion_factor(rule.item_code, rule.uom).get("conversion_factor", 1)

		if (flt(qty) >= (flt(rule.min_qty) * conversion_factor)
			and (flt(qty)<= (rule.max_qty * conversion_factor) if rule.max_qty else True)):
			status = True

		# if user has created item price against the transaction UOM
		if rule.get("uom") == args.get("uom"):
			conversion_factor = 1.0

		if status and (flt(rate) >= (flt(rule.min_amt) * conversion_factor)
			and (flt(rate)<= (rule.max_amt * conversion_factor) if rule.max_amt else True)):
			status = True
		else:
			status = False

		if status:
			rules.append(rule)

	return rules

def if_all_rules_same(pricing_rules, fields):
	all_rules_same = True
	val = [pricing_rules[0].get(k) for k in fields]
	for p in pricing_rules[1:]:
		if val != [p.get(k) for k in fields]:
			all_rules_same = False
			break

	return all_rules_same

def apply_internal_priority(pricing_rules, field_set, args):
	filtered_rules = []
	for field in field_set:
		if args.get(field):
			filtered_rules = filter(lambda x: x[field]==args[field], pricing_rules)
			if filtered_rules: break

	return filtered_rules or pricing_rules

def get_qty_and_rate_for_mixed_conditions(doc, pr_doc, args):
	sum_qty, sum_amt = [0, 0]
	items = get_pricing_rule_items(pr_doc) or []
	apply_on = frappe.scrub(pr_doc.get('apply_on'))

	if items and doc.get("items"):
		for row in doc.get('items'):
			if row.get(apply_on) not in items: continue

			if pr_doc.mixed_conditions:
				amt = args.get('qty') * args.get("price_list_rate")
				if args.get("item_code") != row.get("item_code"):
					amt = row.get('qty') * row.get("price_list_rate")

				sum_qty += row.get("stock_qty") or args.get("stock_qty")
				sum_amt += amt

		if pr_doc.is_cumulative:
			data = get_qty_amount_data_for_cumulative(pr_doc, doc, items)

			if data and data[0]:
				sum_qty += data[0]
				sum_amt += data[1]

	return sum_qty, sum_amt

def get_qty_and_rate_for_other_item(doc, pr_doc, pricing_rules):
	for d in get_pricing_rule_items(pr_doc):
		for row in doc.items:
			if d == row.get(frappe.scrub(pr_doc.apply_on)):
				pricing_rules = filter_pricing_rules_for_qty_amount(row.get("stock_qty"),
					row.get("amount"), pricing_rules, row)

				if pricing_rules and pricing_rules[0]:
					return pricing_rules

def get_qty_amount_data_for_cumulative(pr_doc, doc, items=[]):
	sum_qty, sum_amt = [0, 0]
	doctype = doc.get('parenttype') or doc.doctype

	date_field = ('transaction_date'
		if doc.get('transaction_date') else 'posting_date')

	child_doctype = '{0} Item'.format(doctype)
	apply_on = frappe.scrub(pr_doc.get('apply_on'))

	values = [pr_doc.valid_from, pr_doc.valid_upto]
	condition = ""

	if pr_doc.warehouse:
		warehouses = get_child_warehouses(pr_doc.warehouse)

		condition += """ and `tab{child_doc}`.warehouse in ({warehouses})
			""".format(child_doc=child_doctype, warehouses = ','.join(['%s'] * len(warehouses)))

		values.extend(warehouses)

	if items:
		condition = " and `tab{child_doc}`.{apply_on} in ({items})".format(child_doc = child_doctype,
			apply_on = apply_on, items = ','.join(['%s'] * len(items)))

		values.extend(items)

	data_set = frappe.db.sql(""" SELECT `tab{child_doc}`.stock_qty,
			`tab{child_doc}`.amount
		FROM `tab{child_doc}`, `tab{parent_doc}`
		WHERE
			`tab{child_doc}`.parent = `tab{parent_doc}`.name and `tab{parent_doc}`.{date_field}
			between %s and %s and `tab{parent_doc}`.docstatus = 1
			{condition} group by `tab{child_doc}`.name
	""".format(parent_doc = doctype,
		child_doc = child_doctype,
		condition = condition,
		date_field = date_field
	), tuple(values), as_dict=1)

	for data in data_set:
		sum_qty += data.get('stock_qty')
		sum_amt += data.get('amount')

	return [sum_qty, sum_amt]

def validate_pricing_rules(doc):
	validate_pricing_rule_on_transactions(doc)

	for d in doc.items:
		validate_pricing_rule_on_items(doc, d)

	doc.calculate_taxes_and_totals()

def validate_pricing_rule_on_items(doc, item_row, do_not_validate = False):
	value = 0
	for pricing_rule in get_applied_pricing_rules(doc, item_row):
		pr_doc = frappe.get_doc('Pricing Rule', pricing_rule)

		if pr_doc.get('apply_on') == 'Transaction': continue

		if pr_doc.get('price_or_product_discount') == 'Product':
			apply_pricing_rule_for_free_items(doc, pr_doc)
		else:
			for field in ['discount_percentage', 'discount_amount', 'rate']:
				if not pr_doc.get(field): continue

				value += pr_doc.get(field)
			apply_pricing_rule(doc, pr_doc, item_row, value, do_not_validate)

def validate_pricing_rule_on_transactions(doc):
	conditions = "apply_on = 'Transaction'"

	values = {}
	conditions = get_other_conditions(conditions, values, doc)

	pricing_rules = frappe.db.sql(""" Select `tabPricing Rule`.* from `tabPricing Rule`
		where {conditions} """.format(conditions = conditions), values, as_dict=1)

	if pricing_rules:
		pricing_rules = filter_pricing_rules_for_qty_amount(doc.total_qty,
			doc.total, pricing_rules)

		for d in pricing_rules:
			if d.price_or_product_discount == 'Price':
				if d.apply_discount_on:
					doc.set('apply_discount_on', d.apply_discount_on)

				for field in ['additional_discount_percentage', 'discount_amount']:
					if not d.get(field): continue

					pr_field = ('discount_percentage'
						if field == 'additional_discount_percentage' else field)

					if d.validate_applied_rule and doc.get(field) < d.get(pr_field):
						frappe.msgprint(_("User has not applied rule on the invoice {0}")
							.format(doc.name))
					else:
						doc.set(field, d.get(pr_field))
			elif d.price_or_product_discount == 'Product':
				apply_pricing_rule_for_free_items(doc, d)

def get_applied_pricing_rules(doc, item_row):
	return (item_row.get("pricing_rules").split(',')
		if item_row.get("pricing_rules") else [])

def apply_pricing_rule_for_free_items(doc, pricing_rule):
	if pricing_rule.get('free_item'):
		items = [d.item_code for d in doc.items
			if d.item_code == (d.item_code
			if pricing_rule.get('same_item') else pricing_rule.get('free_item')) and d.is_free_item]

		if not items:
			doc.append('items', {
				'item_code': pricing_rule.get('free_item'),
				'qty': pricing_rule.get('free_qty'),
				'uom': pricing_rule.get('free_item_uom'),
				'rate': pricing_rule.get('free_item_rate'),
				'is_free_item': 1
			})

			doc.set_missing_values()

def apply_pricing_rule(doc, pr_doc, item_row, value, do_not_validate=False):
	apply_on, items = get_apply_on_and_items(pr_doc, item_row)

	rule_applied = {}

	for item in doc.get("items"):
		if item.get(apply_on) in items:
			if not item.pricing_rules:
				item.pricing_rules = item_row.pricing_rules

			for field in ['discount_percentage', 'discount_amount', 'rate']:
				if not pr_doc.get(field): continue

				key = (item.name, item.pricing_rules)
				if not pr_doc.validate_applied_rule:
					rule_applied[key] = 1
					item.set(field, value)
				elif item.get(field) < value:
					if not do_not_validate and item.idx == item_row.idx:
						rule_applied[key] = 0
						frappe.msgprint(_("Row {0}: user has not applied rule <b>{1}</b> on the item <b>{2}</b>")
							.format(item.idx, pr_doc.title, item.item_code))

	if rule_applied and doc.get("pricing_rules"):
		for d in doc.get("pricing_rules"):
			key = (d.child_docname, d.pricing_rule)
			if key in rule_applied:
				d.rule_applied = 1

def get_apply_on_and_items(pr_doc, item_row):
	# for mixed or other items conditions
	apply_on = frappe.scrub(pr_doc.get('apply_on'))
	items = (get_pricing_rule_items(pr_doc)
		if pr_doc.mixed_conditions else [item_row.get(apply_on)])

	if pr_doc.apply_rule_on_other:
		apply_on = frappe.scrub(pr_doc.apply_rule_on_other)
		items = [pr_doc.get(apply_on)]

	return apply_on, items

def get_pricing_rule_items(pr_doc):
	apply_on = frappe.scrub(pr_doc.get('apply_on'))

	pricing_rule_apply_on = apply_on_table.get(pr_doc.get('apply_on'))

	return [item.get(apply_on) for item in pr_doc.get(pricing_rule_apply_on)] or []

@frappe.whitelist()
def validate_pricing_rule_for_different_cond(doc):
	if isinstance(doc, string_types):
		doc = json.loads(doc)

	doc = frappe.get_doc(doc)
	for d in doc.get("items"):
		validate_pricing_rule_on_items(doc, d, True)

	return doc