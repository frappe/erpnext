frappe.listview_settings['Vehicle'] = {
	add_fields: ["item_code", "warehouse", "warranty_expiry_date", "delivery_document_type"],
	get_indicator: (doc) => {
		if (doc.delivery_document_type) {
			return [__("Delivered"), "green", "delivery_document_type,is,set"];
		} else if (doc.warranty_expiry_date && frappe.datetime.get_diff(doc.warranty_expiry_date, frappe.datetime.nowdate()) <= 0) {
			return [__("Expired"), "red", "warranty_expiry_date,not in,|warranty_expiry_date,<=,Today|delivery_document_type,is,not set"];
		} else if (!doc.warehouse) {
			return [__("Inactive"), "grey", "warehouse,is,not set"];
		} else {
			return [__("Active"), "blue", "delivery_document_type,is,not set"];
		}
	},
	onload: function(listview) {
		listview.page.fields_dict.variant_of.get_query = () => {
			return erpnext.queries.item({"is_vehicle": 1, "has_variants": 1, "include_disabled": 1});
		}

		listview.page.fields_dict.item_code.get_query = () => {
			var variant_of = listview.page.fields_dict.variant_of.get_value('variant_of');
			var filters = {"is_vehicle": 1, "include_disabled": 1};
			if (variant_of) {
				filters['variant_of'] = variant_of;
			}
			return erpnext.queries.item(filters);
		}
	}
};
