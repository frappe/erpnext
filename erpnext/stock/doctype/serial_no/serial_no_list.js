frappe.listview_settings['Serial No'] = {
	add_fields: ["item_code", "warehouse", "warranty_expiry_date", "delivery_document_type"],
	get_indicator: (doc) => {
		if (doc.delivery_document_type) {
			return [__("Delivered"), "green", "delivery_document_type,is,set"];
		} else if (doc.warranty_expiry_date && frappe.datetime.get_diff(doc.warranty_expiry_date, frappe.datetime.nowdate()) <= 0) {
			return [__("Expired"), "red", "warranty_expiry_date,not in,|warranty_expiry_date,<=,Today|delivery_document_type,is,not set"];
		} else if (!doc.warehouse) {
			return [__("Inactive"), "grey", "warehouse,is,not set"];
		} else {
			return [__("Active"), "green", "delivery_document_type,is,not set"];
		}
	}
};
