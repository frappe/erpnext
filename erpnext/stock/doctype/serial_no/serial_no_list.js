frappe.listview_settings['Serial No'] = {
	add_fields: ["is_cancelled", "item_code", "warehouse", "warranty_expiry_date", "delivery_document_type"],
	get_indicator: (doc) => {
		if (doc.is_cancelled) {
			return [__("Cancelled"), "red", "is_cancelled,=,Yes"];
		} else if (doc.delivery_document_type) {
			return [__("Delivered"), "green", "delivery_document_type,is,set|is_cancelled,=,No"];
		} else if (doc.warranty_expiry_date && frappe.datetime.get_diff(doc.warranty_expiry_date, frappe.datetime.nowdate()) <= 0) {
			return [__("Expired"), "red", "warranty_expiry_date,not in,|warranty_expiry_date,<=,Today|delivery_document_type,is,not set|is_cancelled,=,No"];
		} else {
			return [__("Active"), "green", "delivery_document_type,is,not set|is_cancelled,=,No"];
		}
	}
};
