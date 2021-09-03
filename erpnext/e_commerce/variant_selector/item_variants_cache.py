import frappe


class ItemVariantsCacheManager:
	def __init__(self, item_code):
		self.item_code = item_code

	def get_item_variants_data(self):
		val = frappe.cache().hget('item_variants_data', self.item_code)

		if not val:
			self.build_cache()

		return frappe.cache().hget('item_variants_data', self.item_code)


	def get_attribute_value_item_map(self):
		val = frappe.cache().hget('attribute_value_item_map', self.item_code)

		if not val:
			self.build_cache()

		return frappe.cache().hget('attribute_value_item_map', self.item_code)


	def get_item_attribute_value_map(self):
		val = frappe.cache().hget('item_attribute_value_map', self.item_code)

		if not val:
			self.build_cache()

		return frappe.cache().hget('item_attribute_value_map', self.item_code)


	def get_optional_attributes(self):
		val = frappe.cache().hget('optional_attributes', self.item_code)

		if not val:
			self.build_cache()

		return frappe.cache().hget('optional_attributes', self.item_code)

	def get_ordered_attribute_values(self):
		val = frappe.cache().get_value('ordered_attribute_values_map')
		if val: return val

		all_attribute_values = frappe.db.get_all('Item Attribute Value',
			['attribute_value', 'idx', 'parent'], order_by='idx asc')

		ordered_attribute_values_map = frappe._dict({})
		for d in all_attribute_values:
			ordered_attribute_values_map.setdefault(d.parent, []).append(d.attribute_value)

		frappe.cache().set_value('ordered_attribute_values_map', ordered_attribute_values_map)
		return ordered_attribute_values_map

	def build_cache(self):
		parent_item_code = self.item_code

		attributes = [a.attribute for a in frappe.db.get_all('Item Variant Attribute',
			{'parent': parent_item_code}, ['attribute'], order_by='idx asc')
		]

		item_variants_data = frappe.db.get_all('Item Variant Attribute',
			{'variant_of': parent_item_code}, ['parent', 'attribute', 'attribute_value'],
			order_by='name',
			as_list=1
		)

		disabled_items = set([i.name for i in frappe.db.get_all('Item', {'disabled': 1})])

		attribute_value_item_map = frappe._dict({})
		item_attribute_value_map = frappe._dict({})

		item_variants_data = [r for r in item_variants_data if r[0] not in disabled_items]
		for row in item_variants_data:
			item_code, attribute, attribute_value = row
			# (attr, value) => [item1, item2]
			attribute_value_item_map.setdefault((attribute, attribute_value), []).append(item_code)
			# item => {attr1: value1, attr2: value2}
			item_attribute_value_map.setdefault(item_code, {})[attribute] = attribute_value

		optional_attributes = set()
		for item_code, attr_dict in item_attribute_value_map.items():
			for attribute in attributes:
				if attribute not in attr_dict:
					optional_attributes.add(attribute)

		frappe.cache().hset('attribute_value_item_map', parent_item_code, attribute_value_item_map)
		frappe.cache().hset('item_attribute_value_map', parent_item_code, item_attribute_value_map)
		frappe.cache().hset('item_variants_data', parent_item_code, item_variants_data)
		frappe.cache().hset('optional_attributes', parent_item_code, optional_attributes)

	def clear_cache(self):
		keys = ['attribute_value_item_map', 'item_attribute_value_map', 'item_variants_data', 'optional_attributes']

		for key in keys:
			frappe.cache().hdel(key, self.item_code)

	def rebuild_cache(self):
		self.clear_cache()
		enqueue_build_cache(self.item_code)


def build_cache(item_code):
	frappe.cache().hset('item_cache_build_in_progress', item_code, 1)
	i = ItemVariantsCacheManager(item_code)
	i.build_cache()
	frappe.cache().hset('item_cache_build_in_progress', item_code, 0)

def enqueue_build_cache(item_code):
	if frappe.cache().hget('item_cache_build_in_progress', item_code):
		return
	frappe.enqueue(build_cache, item_code=item_code, queue='long')
