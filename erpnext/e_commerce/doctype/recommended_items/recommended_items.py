# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class RecommendedItems(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		item_code: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		route: DF.SmallText | None
		website_item: DF.Link | None
		website_item_image: DF.Attach | None
		website_item_name: DF.Data | None
		website_item_thumbnail: DF.Data | None
	# end: auto-generated types
	pass
