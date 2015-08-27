frappe.listview_settings['Purchase Receipt'] = {
	add_fields: ["supplier", "supplier_name", "base_grand_total", "is_subcontracted",
		"transporter_name", "is_return"],
	get_indicator: function(doc) {
		if(cint(doc.is_return)==1) {
			return [__("Return"), "darkgrey", "is_return,=,Yes"];
		}
	}
};
