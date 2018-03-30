import frappe
from frappe.utils import cstr

def execute():
	'''
	Issue:
		While copying data from template item to variant item,
		the system appending description multiple times to the respective variant.

	Purpose:
		Check variant description,
		if variant have user defined description remove all system appended descriptions
		else replace multiple system generated descriptions with single description

	Steps:
		1. Get all variant items
		2. Create system generated variant description
		3. If variant have user defined description, remove all system generated descriptions
		4. If variant description only contains system generated description,
			replace multiple descriptions by new description.
	'''
	for item in frappe.db.sql(""" select name from tabItem
		where ifnull(variant_of, '') != '' """,as_dict=1):
			variant = frappe.get_doc("Item", item.name)
			temp_variant_description = '\n'

			if variant.attributes:
				for d in variant.attributes:
					temp_variant_description += "<div>" + d.attribute + ": " + cstr(d.attribute_value) + "</div>"

				variant_description = variant.description.replace(temp_variant_description, '').rstrip()
				if variant_description:
					splitted_desc = variant.description.strip().split(temp_variant_description)

					if len(splitted_desc) > 2:
						if splitted_desc[0] == '':
							variant_description = temp_variant_description + variant_description
						elif splitted_desc[1] == '' or splitted_desc[1] == '\n':
							variant_description += temp_variant_description
						variant.db_set('description', variant_description, update_modified=False)
					else:
						variant.db_set('description', variant_description, update_modified=False)

				else:
					variant.db_set('description', temp_variant_description, update_modified=False)