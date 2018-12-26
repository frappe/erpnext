import frappe, json

def get_context(context):
	context.items = get_products_for_website()

	attributes = frappe.get_all('Item Attribute', {'show_in_website': 1})
	context.attributes_for_filters = [
		frappe.get_doc('Item Attribute', attribute) for attribute in attributes
	]


@frappe.whitelist(allow_guest=True)
def get_products_for_website(attribute_data=None):

	if attribute_data and isinstance(attribute_data, frappe.string_types):
		attribute_data = json.loads(attribute_data)
	else:
		if frappe.form_dict:
			attribute_data = frappe.form_dict

	print(attribute_data)

	if attribute_data:
		item_codes = get_items_with_attributes(attribute_data)

		return get_items({
			'name': ['in', item_codes],
			'show_variant_in_website': 1
		})

	return get_items()


@frappe.whitelist(allow_guest=True)
def get_products_html_for_website(attribute_data=None):
	items = get_products_for_website(attribute_data)
	html = ''
	for item in items:
		html += frappe.render_template('erpnext/templates/pages/products_item.html', {
			'item': item
		})
	return html


def get_items(filters=None):
	if not filters:
		filters = {'variant_of': '', 'show_in_website': 1}

	return frappe.get_all('Item',
		fields=['name', 'item_name', 'image', 'route', 'description'],
		filters=filters,
		limit=10
	)


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
