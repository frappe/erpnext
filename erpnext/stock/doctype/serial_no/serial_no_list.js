frappe.listview_settings['Serial No'] = {
	add_fields: ["status", "item_code", "warehouse", "warranty_expiry_date", "delivery_document_type"],
	get_indicator: (doc) => {
		/*if (doc.status) {
			return [__("Used"), "red", "status,=,Used"];
		} else*/ if (doc.status) {
			return [__("Free"), "green", "status,=,Free"];
		} else if (doc.status) {
			return [__("Broken"), "red", "status,=,Broken"];
		} else if (doc.status) {
			return [__("Lost"), "red", "status,=,Lost"];
		} else if (doc.status) {
			return [__("On Site"), "blue", "status,=,On Site"];
		} else if (doc.status) {
			return [__("To Be Tested"), "yellow", "status,=,To Be Tested"];
		}
	}
};
