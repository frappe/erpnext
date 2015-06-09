import frappe

def execute():
	variant_item = frappe.db.get_all("Item",
			fields=["name"],
			filters={"has_variants": 1})
			
	for d in variant_item:
		pass
		
	def get_variant_item_codes(self):
		"""Get all possible suffixes for variants"""
		variant_dict = {}
		for d in self.attributes:
			variant_dict.setdefault(d.attribute, []).append(d.attribute_value)

		all_attributes = [d.name for d in frappe.get_all("Item Attribute", order_by = "priority asc")]

		# sort attributes by their priority
		attributes = filter(None, map(lambda d: d if d in variant_dict else None, all_attributes))

		def add_attribute_suffixes(item_code, my_attributes, attributes):
			attr = frappe.get_doc("Item Attribute", attributes[0])
			for value in attr.item_attribute_values:
				if value.attribute_value in variant_dict[attr.name]:
					_my_attributes = copy.deepcopy(my_attributes)
					_my_attributes.append([attr.name, value.attribute_value])
					if len(attributes) > 1:
						add_attribute_suffixes(item_code + "-" + value.abbr, _my_attributes, attributes[1:])
					else:
						self.append('variants', {"variant": item_code + "-" + value.abbr, 
							"attributes": json.dumps(_my_attributes)})
		add_attribute_suffixes(self.item, [], attributes)