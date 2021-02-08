import frappe
from frappe.utils import cint
from erpnext.portal.product_configurator.item_variants_cache import ItemVariantsCacheManager
from erpnext.shopping_cart.product_info import get_product_info_for_website

def get_field_filter_data():
	product_settings = get_product_settings()
	filter_fields = [row.fieldname for row in product_settings.filter_fields]

	meta = frappe.get_meta('Item')
	fields = [df for df in meta.fields if df.fieldname in filter_fields]

	filter_data = []
	for f in fields:
		doctype = f.get_link_doctype()

		# apply enable/disable/show_in_website filter
		meta = frappe.get_meta(doctype)
		filters = {}
		if meta.has_field('enabled'):
			filters['enabled'] = 1
		if meta.has_field('disabled'):
			filters['disabled'] = 0
		if meta.has_field('show_in_website'):
			filters['show_in_website'] = 1

		values = [d.name for d in frappe.get_all(doctype, filters)]
		filter_data.append([f, values])

	return filter_data


def get_attribute_filter_data():
	product_settings = get_product_settings()
	attributes = [row.attribute for row in product_settings.filter_attributes]
	attribute_docs = [
		frappe.get_doc('Item Attribute', attribute) for attribute in attributes
	]

	# mark attribute values as checked if they are present in the request url
	if frappe.form_dict:
		for attr in attribute_docs:
			if attr.name in frappe.form_dict:
				value = frappe.form_dict[attr.name]
				if value:
					enabled_values = value.split(',')
				else:
					enabled_values = []

				for v in enabled_values:
					for item_attribute_row in attr.item_attribute_values:
						if v == item_attribute_row.attribute_value:
							item_attribute_row.checked = True

	return attribute_docs


def get_products_for_website(field_filters=None, attribute_filters=None, search=None):
	if attribute_filters:
		item_codes = get_item_codes_by_attributes(attribute_filters)
		items_by_attributes = get_items([['name', 'in', item_codes]])

	if field_filters:
		items_by_fields = get_items_by_fields(field_filters)

	if attribute_filters and not field_filters:
		return items_by_attributes

	if field_filters and not attribute_filters:
		return items_by_fields

	if field_filters and attribute_filters:
		items_intersection = []
		item_codes_in_attribute = [item.name for item in items_by_attributes]

		for item in items_by_fields:
			if item.name in item_codes_in_attribute:
				items_intersection.append(item)

		return items_intersection

	if search:
		return get_items(search=search)

	return get_items()


@frappe.whitelist(allow_guest=True)
def get_products_html_for_website(field_filters=None, attribute_filters=None):
	field_filters = frappe.parse_json(field_filters)
	attribute_filters = frappe.parse_json(attribute_filters)

	items = get_products_for_website(field_filters, attribute_filters)
	html = ''.join(get_html_for_items(items))

	if not items:
		html = frappe.render_template('erpnext/www/all-products/not_found.html', {})

	return html


def get_item_codes_by_attributes(attribute_filters, template_item_code=None):
	items = []

	for attribute, values in attribute_filters.items():
		attribute_values = values

		if not isinstance(attribute_values, list):
			attribute_values = [attribute_values]

		if not attribute_values: continue

		wheres = []
		query_values = []
		for attribute_value in attribute_values:
			wheres.append('( attribute = %s and attribute_value = %s )')
			query_values += [attribute, attribute_value]

		attribute_query = ' or '.join(wheres)

		if template_item_code:
			variant_of_query = 'AND t2.variant_of = %s'
			query_values.append(template_item_code)
		else:
			variant_of_query = ''

		query = '''
			SELECT
				t1.parent
			FROM
				`tabItem Variant Attribute` t1
			WHERE
				1 = 1
				AND (
					{attribute_query}
				)
				AND EXISTS (
					SELECT
						1
					FROM
						`tabItem` t2
					WHERE
						t2.name = t1.parent
						{variant_of_query}
				)
			GROUP BY
				t1.parent
			ORDER BY
				NULL
		'''.format(attribute_query=attribute_query, variant_of_query=variant_of_query)

		item_codes = set([r[0] for r in frappe.db.sql(query, query_values)])
		items.append(item_codes)

	res = list(set.intersection(*items))

	return res


@frappe.whitelist(allow_guest=True)
def get_attributes_and_values(item_code):
	'''Build a list of attributes and their possible values.
	This will ignore the values upon selection of which there cannot exist one item.
	'''
	item_cache = ItemVariantsCacheManager(item_code)
	item_variants_data = item_cache.get_item_variants_data()

	attributes = get_item_attributes(item_code)
	attribute_list = [a.attribute for a in attributes]

	valid_options = {}
	for item_code, attribute, attribute_value in item_variants_data:
		if attribute in attribute_list:
			valid_options.setdefault(attribute, set()).add(attribute_value)

	item_attribute_values = frappe.db.get_all('Item Attribute Value',
		['parent', 'attribute_value', 'idx'], order_by='parent asc, idx asc')
	ordered_attribute_value_map = frappe._dict()
	for iv in item_attribute_values:
		ordered_attribute_value_map.setdefault(iv.parent, []).append(iv.attribute_value)

	# build attribute values in idx order
	for attr in attributes:
		valid_attribute_values = valid_options.get(attr.attribute, [])
		ordered_values = ordered_attribute_value_map.get(attr.attribute, [])
		attr['values'] = [v for v in ordered_values if v in valid_attribute_values]

	return attributes


@frappe.whitelist(allow_guest=True)
def get_next_attribute_and_values(item_code, selected_attributes):
	'''Find the count of Items that match the selected attributes.
	Also, find the attribute values that are not applicable for further searching.
	If less than equal to 10 items are found, return item_codes of those items.
	If one item is matched exactly, return item_code of that item.
	'''
	selected_attributes = frappe.parse_json(selected_attributes)

	item_cache = ItemVariantsCacheManager(item_code)
	item_variants_data = item_cache.get_item_variants_data()

	attributes = get_item_attributes(item_code)
	attribute_list = [a.attribute for a in attributes]
	filtered_items = get_items_with_selected_attributes(item_code, selected_attributes)

	next_attribute = None

	for attribute in attribute_list:
		if attribute not in selected_attributes:
			next_attribute = attribute
			break

	valid_options_for_attributes = frappe._dict({})

	for a in attribute_list:
		valid_options_for_attributes[a] = set()

		selected_attribute = selected_attributes.get(a, None)
		if selected_attribute:
			# already selected attribute values are valid options
			valid_options_for_attributes[a].add(selected_attribute)

	for row in item_variants_data:
		item_code, attribute, attribute_value = row
		if item_code in filtered_items and attribute not in selected_attributes and attribute in attribute_list:
			valid_options_for_attributes[attribute].add(attribute_value)

	optional_attributes = item_cache.get_optional_attributes()
	exact_match = []
	# search for exact match if all selected attributes are required attributes
	if len(selected_attributes.keys()) >= (len(attribute_list) - len(optional_attributes)):
		item_attribute_value_map = item_cache.get_item_attribute_value_map()
		for item_code, attr_dict in item_attribute_value_map.items():
			if item_code in filtered_items and set(attr_dict.keys()) == set(selected_attributes.keys()):
				exact_match.append(item_code)

	filtered_items_count = len(filtered_items)

	# get product info if exact match
	from erpnext.shopping_cart.product_info import get_product_info_for_website
	if exact_match:
		data = get_product_info_for_website(exact_match[0])
		product_info = data.product_info
		if product_info:
			product_info["allow_items_not_in_stock"] = cint(data.cart_settings.allow_items_not_in_stock)
		if not data.cart_settings.show_price:
			product_info = None
	else:
		product_info = None

	return {
		'next_attribute': next_attribute,
		'valid_options_for_attributes': valid_options_for_attributes,
		'filtered_items_count': filtered_items_count,
		'filtered_items': filtered_items if filtered_items_count < 10 else [],
		'exact_match': exact_match,
		'product_info': product_info
	}


def get_items_with_selected_attributes(item_code, selected_attributes):
	item_cache = ItemVariantsCacheManager(item_code)
	attribute_value_item_map = item_cache.get_attribute_value_item_map()

	items = []
	for attribute, value in selected_attributes.items():
		filtered_items = attribute_value_item_map.get((attribute, value), [])
		items.append(set(filtered_items))

	return set.intersection(*items)


def get_items_by_fields(field_filters):
	meta = frappe.get_meta('Item')
	filters = []
	for fieldname, values in field_filters.items():
		if not values: continue

		_doctype = 'Item'
		_fieldname = fieldname

		df = meta.get_field(fieldname)
		if df.fieldtype == 'Table MultiSelect':
			child_doctype = df.options
			child_meta = frappe.get_meta(child_doctype)
			fields = child_meta.get("fields", { "fieldtype": "Link", "in_list_view": 1 })
			if fields:
				_doctype = child_doctype
				_fieldname = fields[0].fieldname

		if len(values) == 1:
			filters.append([_doctype, _fieldname, '=', values[0]])
		else:
			filters.append([_doctype, _fieldname, 'in', values])

	return get_items(filters)


def get_items(filters=None, search=None):
	start = frappe.form_dict.start or 0
	products_settings = get_product_settings()
	page_length = products_settings.products_per_page

	filters = filters or []
	# convert to list of filters
	if isinstance(filters, dict):
		filters = [['Item', fieldname, '=', value] for fieldname, value in filters.items()]

	enabled_items_filter = get_conditions({ 'disabled': 0 }, 'and')

	show_in_website_condition = ''
	if products_settings.hide_variants:
		show_in_website_condition = get_conditions({'show_in_website': 1 }, 'and')
	else:
		show_in_website_condition = get_conditions([
			['show_in_website', '=', 1],
			['show_variant_in_website', '=', 1]
		], 'or')

	search_condition = ''
	if search:
		# Default fields to search from
		default_fields = {'name', 'item_name', 'description', 'item_group'}

		# Get meta search fields
		meta = frappe.get_meta("Item")
		meta_fields = set(meta.get_search_fields())

		# Join the meta fields and default fields set
		search_fields = default_fields.union(meta_fields)
		try:
			if frappe.db.count('Item', cache=True) > 50000:
				search_fields.remove('description')
		except KeyError:
			pass

		# Build or filters for query
		search = '%{}%'.format(search)
		or_filters = [[field, 'like', search] for field in search_fields]

		search_condition = get_conditions(or_filters, 'or')

	filter_condition = get_conditions(filters, 'and')

	where_conditions = ' and '.join(
		[condition for condition in [enabled_items_filter, show_in_website_condition, \
			search_condition, filter_condition] if condition]
	)

	left_joins = []
	for f in filters:
		if len(f) == 4 and f[0] != 'Item':
			left_joins.append(f[0])

	left_join = ' '.join(['LEFT JOIN `tab{0}` on (`tab{0}`.parent = `tabItem`.name)'.format(l) for l in left_joins])

	results = frappe.db.sql('''
		SELECT
			`tabItem`.`name`, `tabItem`.`item_name`, `tabItem`.`item_code`,
			`tabItem`.`website_image`, `tabItem`.`image`,
			`tabItem`.`web_long_description`, `tabItem`.`description`,
			`tabItem`.`route`, `tabItem`.`item_group`
		FROM
			`tabItem`
		{left_join}
		WHERE
			{where_conditions}
		GROUP BY
			`tabItem`.`name`
		ORDER BY
			`tabItem`.`weightage` DESC
		LIMIT
			{page_length}
		OFFSET
			{start}
	'''.format(
			where_conditions=where_conditions,
			start=start,
			page_length=page_length,
			left_join=left_join
		)
	, as_dict=1)

	for r in results:
		r.description = r.web_long_description or r.description
		r.image = r.website_image or r.image
		product_info = get_product_info_for_website(r.item_code, skip_quotation_creation=True).get('product_info')
		if product_info:
			r.formatted_price = product_info['price'].get('formatted_price') if product_info['price'] else None

	return results


def get_conditions(filter_list, and_or='and'):
	from frappe.model.db_query import DatabaseQuery

	if not filter_list:
		return ''

	conditions = []
	DatabaseQuery('Item').build_filter_conditions(filter_list, conditions, ignore_permissions=True)
	join_by = ' {0} '.format(and_or)

	return '(' + join_by.join(conditions) + ')'

# utilities

def get_item_attributes(item_code):
	attributes = frappe.db.get_all('Item Variant Attribute',
		fields=['attribute'],
		filters={
			'parenttype': 'Item',
			'parent': item_code
		},
		order_by='idx asc'
	)

	optional_attributes = ItemVariantsCacheManager(item_code).get_optional_attributes()

	for a in attributes:
		if a.attribute in optional_attributes:
			a.optional = True

	return attributes

def get_html_for_items(items):
	html = []
	for item in items:
		html.append(frappe.render_template('erpnext/www/all-products/item_row.html', {
			'item': item
		}))
	return html

def get_product_settings():
	doc = frappe.get_cached_doc('Products Settings')
	doc.products_per_page = doc.products_per_page or 20
	return doc
