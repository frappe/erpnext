frappe.listview_settings['FBR POS Log'] = {
	add_fields: ["log_type"],
	get_indicator: function(doc) {
		return [__(doc.log_type), doc.log_type == "Success" ? "green" : "red", "log_type,=," + doc.log_type];
	},
};
