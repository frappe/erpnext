# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import frappe
from frappe.utils import floor


class ProductFiltersBuilder:
	def __init__(self, item_group=None):
		if not item_group:
			self.doc = frappe.get_doc("E Commerce Settings")
		else:
			self.doc = frappe.get_doc("Item Group", item_group)

		self.item_group = item_group

	def get_field_filters(self):
		from erpnext.setup.doctype.item_group.item_group import get_child_groups_for_website

		if not self.item_group and not self.doc.enable_field_filters:
			return

		fields, filter_data = [], []
		filter_fields = [row.fieldname for row in self.doc.filter_fields]  # fields in settings

		# filter valid field filters i.e. those that exist in Website Item
		web_item_meta = frappe.get_meta("Website Item", cached=True)
		fields = [
			web_item_meta.get_field(field) for field in filter_fields if web_item_meta.has_field(field)
		]

		for df in fields:
			item_filters, item_or_filters = {"published": 1}, []
			link_doctype_values = self.get_filtered_link_doctype_records(df)

			if df.fieldtype == "Link":
				if self.item_group:
					include_child = frappe.db.get_value("Item Group", self.item_group, "include_descendants")
					if include_child:
						include_groups = get_child_groups_for_website(self.item_group, include_self=True)
						include_groups = [x.name for x in include_groups]
						item_or_filters.extend(
							[
								["item_group", "in", include_groups],
								["Website Item Group", "item_group", "=", self.item_group],  # consider website item groups
							]
						)
					else:
						item_or_filters.extend(
							[
								["item_group", "=", self.item_group],
								["Website Item Group", "item_group", "=", self.item_group],  # consider website item groups
							]
						)

				# exclude variants if mentioned in settings
				if frappe.db.get_single_value("E Commerce Settings", "hide_variants"):
					item_filters["variant_of"] = ["is", "not set"]

				# Get link field values attached to published items
				item_values = frappe.get_all(
					"Website Item",
					fields=[df.fieldname],
					filters=item_filters,
					or_filters=item_or_filters,
					distinct="True",
					pluck=df.fieldname,
				)

				values = list(set(item_values) & link_doctype_values)  # intersection of both
			else:
				# table multiselect
				values = list(link_doctype_values)

			# Remove None
			if None in values:
				values.remove(None)

			if values:
				filter_data.append([df, values])

		return filter_data

	def get_filtered_link_doctype_records(self, field):
		"""
		Get valid link doctype records depending on filters.
		Apply enable/disable/show_in_website filter.
		Returns:
		        set: A set containing valid record names
		"""
		link_doctype = field.get_link_doctype()
		meta = frappe.get_meta(link_doctype, cached=True) if link_doctype else None
		if meta:
			filters = self.get_link_doctype_filters(meta)
			link_doctype_values = set(d.name for d in frappe.get_all(link_doctype, filters))

		return link_doctype_values if meta else set()

	def get_link_doctype_filters(self, meta):
		"Filters for Link Doctype eg. 'show_in_website'."
		filters = {}
		if not meta:
			return filters

		if meta.has_field("enabled"):
			filters["enabled"] = 1
		if meta.has_field("disabled"):
			filters["disabled"] = 0
		if meta.has_field("show_in_website"):
			filters["show_in_website"] = 1

		return filters

	def get_attribute_filters(self):
		if not self.item_group and not self.doc.enable_attribute_filters:
			return

		attributes = [row.attribute for row in self.doc.filter_attributes]

		if not attributes:
			return []

		result = frappe.get_all(
			"Item Variant Attribute",
			filters={"attribute": ["in", attributes], "attribute_value": ["is", "set"]},
			fields=["attribute", "attribute_value"],
			distinct=True,
		)

		attribute_value_map = {}
		for d in result:
			attribute_value_map.setdefault(d.attribute, []).append(d.attribute_value)

		out = []
		for name, values in attribute_value_map.items():
			out.append(frappe._dict(name=name, item_attribute_values=values))
		return out

	def get_discount_filters(self, discounts):
		discount_filters = []

		# [25.89, 60.5] min max
		min_discount, max_discount = discounts[0], discounts[1]
		# [25, 60] rounded min max
		min_range_absolute, max_range_absolute = floor(min_discount), floor(max_discount)

		min_range = int(min_discount - (min_range_absolute % 10))  # 20
		max_range = int(max_discount - (max_range_absolute % 10))  # 60

		min_range = (
			(min_range + 10) if min_range != min_range_absolute else min_range
		)  # 30 (upper limit of 25.89 in range of 10)
		max_range = (max_range + 10) if max_range != max_range_absolute else max_range  # 60

		for discount in range(min_range, (max_range + 1), 10):
			label = f"{discount}% and below"
			discount_filters.append([discount, label])

		return discount_filters
