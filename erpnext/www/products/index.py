import frappe, json

def get_context(context):
	context.items = get_products_for_website()
	context.attributes_for_filters = get_filter_data()


def get_filter_data():
	attributes = frappe.get_all('Item Attribute', {'show_in_website': 1})
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


@frappe.whitelist(allow_guest=True)
def get_products_for_website(attribute_data=None):
	search = None
	if attribute_data and isinstance(attribute_data, frappe.string_types):
		attribute_data = json.loads(attribute_data)
	else:
		if frappe.form_dict:
			if frappe.form_dict.search:
				search = frappe.form_dict.search
			else:
				attribute_data = frappe.form_dict

	if attribute_data:
		item_codes = get_items_with_attributes(attribute_data)

		return get_items({
			'name': ['in', item_codes],
			'show_variant_in_website': 1
		})

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
def get_products_html_for_website(attribute_data=None):
	items = get_products_for_website(attribute_data)
	html = ''
	for item in items:
		html += frappe.render_template('erpnext/www/products/item_row.html', {
			'item': item
		})

	if not items:
		html = frappe.render_template('erpnext/www/products/not_found.html', {})

	return html


def get_items_with_attributes(attribute_data):
	items = []

	for attribute, value in attribute_data.iteritems():
		if isinstance(value, frappe.string_types):
			attribute_values = value.split(',')
		else:
			attribute_values = value

		if not attribute_values: continue

		wheres = []
		query_values = []
		for attribute_value in attribute_values:
			wheres.append('( attribute = %s and attribute_value = %s )')
			query_values += [attribute, attribute_value]

		where = ' or '.join(wheres)

		query = '''
			select
				parent
			from `tabItem Variant Attribute`
			where
				({where})
			group by parent
		'''.format(where=where)

		print(query)

		item_codes = set([r[0] for r in frappe.db.sql(query, query_values)])
		items.append(item_codes)

	res = list(set.intersection(*items))

	return res


def get_items(filters=None, or_filters=None):
	if not filters and not or_filters:
		filters = {'variant_of': '', 'show_in_website': 1}

	return frappe.get_all('Item',
		fields=['name', 'item_name', 'image', 'route', 'description'],
		filters=filters,
		or_filters=or_filters,
		limit=10
	)

