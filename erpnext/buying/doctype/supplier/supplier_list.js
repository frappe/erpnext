frappe.listview_settings['Supplier'] = {
	add_fields: ["supplier_name", "supplier_type", 'status'],
	get_indicator: function(doc) {
		if(doc.status==="Open") {
			return [doc.status, "red", "status,=," + doc.status];
		}
	}
};
