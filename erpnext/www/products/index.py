import frappe, json

def get_context(context):
	context.items = get_products_for_website()

	product_settings = frappe.get_cached_doc('Products Settings')
	context.field_filters = get_field_filter_data() \
		if product_settings.enable_field_filters else []

	context.attribute_filters = get_attribute_filter_data() \
		if product_settings.enable_attribute_filters else []

	context.product_settings = product_settings
	context.page_length = product_settings.products_per_page


def get_field_filter_data():
	product_settings = frappe.get_cached_doc('Products Settings')
	filter_fields = [row.fieldname for row in product_settings.filter_fields]

	meta = frappe.get_meta('Item')
	fields = [df for df in meta.fields if df.fieldname in filter_fields]

	filter_data = []
	for f in fields:
		doctype = f.options
		values = [d.name for d in frappe.get_all(doctype)]
		filter_data.append([f, values])

	return filter_data


def get_attribute_filter_data():
	product_settings = frappe.get_cached_doc('Products Settings')
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


def get_products_for_website(field_filters=None, attribute_filters=None):
	search = None

	if not (field_filters or attribute_filters):
		if frappe.form_dict:
			search = frappe.form_dict.search
			field_filters = parse_if_json(frappe.form_dict.field_filters)
			attribute_filters = parse_if_json(frappe.form_dict.attribute_filters)

	if attribute_filters:
		item_codes = get_item_codes_by_attributes(attribute_filters)

		items_by_attributes = get_items({
			'name': ['in', item_codes],
			'show_variant_in_website': 1
		})

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
		search = '%' + search + '%'
		return get_items(or_filters={
			'name': ['like', search],
			'item_name': ['like', search],
			'description': ['like', search],
			'item_group': ['like', search]
		})

	return get_items()


@frappe.whitelist(allow_guest=True)
def get_products_html_for_website(field_filters=None, attribute_filters=None):
	field_filters = parse_if_json(field_filters)
	attribute_filters = parse_if_json(attribute_filters)

	items = get_products_for_website(field_filters, attribute_filters)
	html = ''.join(get_html_for_items(items))

	if not items:
		html = frappe.render_template('erpnext/www/products/not_found.html', {})

	return html


@frappe.whitelist(allow_guest=True)
def get_items_by_attributes(attribute_filters, template_item_code=None):
	attribute_filters = parse_if_json(attribute_filters)

	for attribute, value in attribute_filters.items():
		attribute_filters[attribute] = [value]

	item_codes = get_item_codes_by_attributes(attribute_filters, template_item_code)
	# items = get_items({
	# 	'name': ['in', item_codes]
	# })

	return item_codes

	# return ''.join(get_html_for_items(items))

@frappe.whitelist(allow_guest=True)
def get_attributes_and_values(item_code):
	attributes = frappe.db.get_all('Item Variant Attribute',
		fields=['attribute'],
		filters={
			'parenttype': 'Item',
			'parent': item_code
		},
		order_by='idx asc'
	)

	attribute_names = [a.attribute for a in attributes]

	values = frappe.db.get_all('Item Attribute Value',
		fields=['attribute_value', 'parent'],
		filters={
			'parent': ['in', attribute_names]
		}
	)

	for a in attributes:
		a.setdefault('values', [])
		for value in values:
			attribute = value.parent
			if attribute == a.attribute:
				a['values'].append(value.attribute_value)

	return attributes

@frappe.whitelist(allow_guest=True)
def get_item_codes_by_attributes(attribute_filters, template_item_code=None):
	items = []

	for attribute, values in attribute_filters.iteritems():
		attribute_values = values

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

		# query = '''
		# 	select
		# 		parent
		# 	from `tabItem Variant Attribute`
		# 	where
		# 		 {variant_query}
		# 	group by parent
		# '''.format(where=where, variant_query=variant_query)

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

		print(query)

		item_codes = set([r[0] for r in frappe.db.sql(query, query_values)])
		items.append(item_codes)

	res = list(set.intersection(*items))

	return res

@frappe.whitelist(allow_guest=True)
def get_next_attribute_and_values(item_code, selected_attributes):
	selected_attributes = parse_if_json(selected_attributes)

	attributes = [a.attribute for a in frappe.db.get_all('Item Variant Attribute',
		{'parent': item_code}, ['attribute'], order_by='idx asc')
	]

	next_attribute = None

	for attribute in attributes:
		if attribute not in selected_attributes:
			next_attribute = attribute
			break

	item_attribute_value_map = get_item_attribute_value_map(item_code)
	item_variants_data = get_item_variants_data(item_code)

	items = []
	for attribute, value in selected_attributes.items():
		items.append(set(item_attribute_value_map[(attribute, value)]))

	filtered_items = set.intersection(*items)

	next_attribute_options = set([r[2] for r in item_variants_data if r[1] == next_attribute and r[0] in filtered_items])

	return next_attribute, list(next_attribute_options), len(filtered_items)


def get_item_variants_data(item_code):
	val = frappe.cache().hget('item_variants_data', item_code)

	if not val:
		build_cache(item_code)

	return frappe.cache().hget('item_variants_data', item_code)


def get_item_attribute_value_map(item_code):
	val = frappe.cache().hget('item_attribute_value_map', item_code)

	if not val:
		build_cache(item_code)

	return frappe.cache().hget('item_attribute_value_map', item_code)


def build_cache(item_code):
	val = frappe.db.sql('''
		select
			parent, attribute, attribute_value
		from
			`tabItem Variant Attribute`
		where
			variant_of = %s
	''', values=[item_code])

	data = frappe._dict({})
	for row in val:
		data.setdefault((row[1], row[2]), []).append(row[0])

	frappe.cache().hset('item_attribute_value_map', item_code, data)
	frappe.cache().hset('item_variants_data', item_code, val)


def get_items_by_fields(field_filters):
	filters = frappe._dict({})
	for fieldname, values in field_filters.iteritems():
		if not values: continue
		if len(values) == 1:
			filters[fieldname] = values[0]
		else:
			filters[fieldname] = ['in', values]

	return get_items(filters)


# def get_item_variant_data(item_code):
# 	return frappe.db.sql('''
# 		SELECT
# 			t2.variant_of,
# 			t1.parent,
# 			t1.attribute,
# 			t1.attribute_value
# 		FROM
# 			`tabItem Variant Attribute` t1
# 		INNER JOIN
# 			`tabItem` t2
# 				ON t1.parent = t2.name
# 		WHERE
# 			t2.variant_of = %s
# 	''', [item_code])


# def build_cache():
# 	import functools

# 	# templates = [d.name for d in frappe.db.get_all('Item', {'has_variants': 1})]
# 	query_values = []
# 	values = []
# 	templates = ['CAPVEL_ICT']
# 	for item in templates:
# 		print('building cache for ' + item)
# 		data = get_item_variant_data(item)
# 		if not data: continue

# 		flattened_data = []
# 		for d in data:
# 			flattened_data += d

# 		values.append(', '.join(['(' + ', '.join(['%s'] * len(data[0])) + ')'] * len(data)))
# 		# flattened_data = functools.reduce(lambda a, b: a + b, data)
# 		query_values += flattened_data
# 		break

# 	query = '''
# 		INSERT INTO
# 			`tabItem Variant Attribute Cache`
# 				(item_template, item_variant, attribute, attribute_value)
# 		VALUES
# 			{values}
# 	'''.format(values=','.join(values))

# 	frappe.db.sql(query, query_values)


def get_items(filters=None, or_filters=None):
	if not filters and not or_filters:
		filters = {'variant_of': '', 'show_in_website': 1}

	start = frappe.form_dict.start or 0
	page_length = frappe.db.get_single_value('Products Settings', 'products_per_page')

	return frappe.get_all('Item',
		fields=['name', 'item_name', 'image', 'route', 'description'],
		filters=filters,
		or_filters=or_filters,
		start=start,
		page_length=page_length
	)

def get_html_for_items(items):
	html = []
	for item in items:
		html.append(frappe.render_template('erpnext/www/products/item_row.html', {
			'item': item
		}))
	return html

def parse_if_json(dict_or_str):
	if dict_or_str and isinstance(dict_or_str, frappe.string_types):
		dict_or_str = json.loads(dict_or_str)

	return dict_or_str