# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class SupportSearchSource(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		base_url: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		post_description_key: DF.Data | None
		post_route: DF.Data | None
		post_route_key_list: DF.Data | None
		post_title_key: DF.Data | None
		query_route: DF.Data | None
		response_result_key_path: DF.Data | None
		result_preview_field: DF.Data | None
		result_route_field: DF.Data | None
		result_title_field: DF.Data | None
		search_term_param_name: DF.Data | None
		source_doctype: DF.Link | None
		source_name: DF.Data | None
		source_type: DF.Literal["API", "Link"]
	# end: auto-generated types

	pass
