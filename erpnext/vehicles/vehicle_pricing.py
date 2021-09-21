import frappe
from frappe import _
from frappe.utils import flt, cstr, cint, getdate
from erpnext.vehicles.doctype.vehicle_withholding_tax_rule.vehicle_withholding_tax_rule import get_withholding_tax_amount
import json
from six import string_types


def calculate_total_price(doc, table_field, total_field):
	doc.set(total_field, 0)
	for d in doc.get(table_field):
		doc.round_floats_in(d)
		doc.set(total_field, flt(doc.get(total_field)) + flt(d.component_amount))

	doc.set(total_field, flt(doc.get(total_field), doc.precision(total_field)))


@frappe.whitelist()
def get_pricing_components(component_type, args, get_selling_components=True, get_buying_components=False, filters=None):
	args = validate_args(args)
	get_selling_components = cint(get_selling_components)
	get_buying_components = cint(get_buying_components)

	if isinstance(filters, string_types):
		filters = json.loads(filters)

	# prepare return value
	out = frappe._dict({
		'doc': frappe._dict({})
	})
	if get_selling_components:
		out.selling = []
	if get_buying_components:
		out.buying = []

	# get all active components
	component_filters = {
		'disabled': 0,
		'component_type': component_type
	}
	if filters:
		component_filters.update(filters)

	component_names = frappe.get_all("Vehicle Pricing Component", filters=component_filters,
		order_by='sorting_index asc, creation asc')
	component_names = [d.name for d in component_names]

	# get prices for components
	for component_name in component_names:
		component_doc = frappe.get_cached_doc("Vehicle Pricing Component", component_name)

		force = False
		if component_doc.component_type == "Registration" and component_doc.registration_component_type == "Choice Number":
			if cint(args.choice_number_required):
				force = True
			else:
				continue

		if get_selling_components:
			selling_component = get_component_details(component_name, args, "selling")
			if force or selling_component.component.price_list or selling_component.component.component_amount:
				out.selling.append(selling_component.component)
				out.doc.update(selling_component.doc)

		if get_buying_components:
			buying_component = get_component_details(component_name, args, "buying")
			if force or buying_component.component.price_list or buying_component.component.component_amount:
				out.buying.append(buying_component.component)
				out.doc.update(buying_component.doc)

	return out


@frappe.whitelist()
def get_component_details(component_name, args, selling_or_buying="selling"):
	args = validate_args(args)
	out = frappe._dict({
		'doc': frappe._dict(),
		'component': frappe._dict()
	})

	component_doc = frappe.get_cached_doc("Vehicle Pricing Component", component_name)

	price_list = get_applicable_price_list(component_doc, territory=args.territory, selling_or_buying=selling_or_buying)
	out.component.component = component_doc.name

	if component_doc.component_type == "Booking" and component_doc.booking_component_type == "Withholding Tax":
		out.component.price_list = None
		if not cint(args.do_not_apply_withholding_tax):
			out.component.component_amount = get_withholding_tax_amount(args.transaction_date, args.item_code,
				args.tax_status, args.company)
		else:
			out.component.component_amount = 0
	elif price_list:
		out.component.price_list = price_list
		out.component.component_amount = get_item_price(args.item_code, price_list, args.transaction_date)
	else:
		out.component.price_list = None
		out.component.component_amount = 0

	if component_doc.component_type == "Booking":
		if component_doc.booking_component_type == "Vehicle Retail":
			out.component.is_vehicle_retail = 1
		elif component_doc.booking_component_type == "Freight":
			out.component.is_freight = 1
		elif component_doc.booking_component_type == "Withholding Tax":
			out.component.is_withholding_tax = 1

	elif component_doc.component_type == "Registration":
		if component_doc.registration_component_type == "Choice Number":
			out.component.is_choice_number = 1
			out.doc.choice_number_required = 1
		elif component_doc.registration_component_type == "Ownership Transfer":
			out.component.is_ownership_transfer = 1

	return out


def get_applicable_price_list(component, territory=None, selling_or_buying="selling"):
	if isinstance(component, string_types):
		component = frappe.get_cached_doc("Vehicle Pricing Component", component)

	if selling_or_buying == "selling":
		fieldname = "selling_price_list"
	elif selling_or_buying == "buying":
		fieldname = "buying_price_list"
	else:
		fieldname = selling_or_buying

	default_price_list = component.get_default_price_list_row()
	if not territory and default_price_list:
		return default_price_list.get(fieldname)

	territory_price_lists = [d for d in component.price_lists if cstr(territory) == cstr(d.territory)]
	if territory_price_lists:
		return territory_price_lists[0].get(fieldname)

	return default_price_list.get(fieldname) if default_price_list else None


def get_item_price(item_code, price_list, transaction_date=None):
	from erpnext.stock.get_item_details import get_item_price

	transaction_date = getdate(transaction_date)

	price_args = {
		"item_code": item_code,
		"price_list": price_list,
		"transaction_date": transaction_date,
		"uom": frappe.get_cached_value("Item", item_code, "stock_uom")
	}
	item_price = get_item_price(price_args, item_code, ignore_party=True)

	return flt(item_price[0][1]) if item_price else 0


def validate_args(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	if not args.item_code:
		frappe.throw(_("Variant Item Code is mandatory"))
	if not args.company:
		frappe.throw(_("Company is mandatory"))

	args.transaction_date = getdate(args.transaction_date)

	return args


def validate_duplicate_components(components):
	visited = set()
	for d in components:
		if d.component:
			if d.component in visited:
				frappe.throw(_("Row #{0}: Duplicated Pricing Component {1}")
					.format(d.idx, frappe.bold(d.component)))

			visited.add(d.component)


def validate_component_type(component_type, components):
	for d in components:
		if d.component:
			if frappe.get_cached_value("Vehicle Pricing Component", d.component, "component_type") != component_type:
				frappe.throw(_("Row #{0}: Pricing Component {1} is a {2} component")
					.format(d.idx, frappe.bold(d.component), component_type))


def validate_disabled_component(components):
	for d in components:
		if d.component:
			if cint(frappe.get_cached_value("Vehicle Pricing Component", d.component, "disabled")):
				frappe.throw(_("Row #{0}: Pricing Component {1} is disabled")
					.format(d.idx, frappe.bold(d.component)))
