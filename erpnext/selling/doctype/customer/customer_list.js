frappe.listview_settings['Customer'] = {
	hide_name_column: true,
	add_fields: ["customer_name", "territory", "customer_group", "customer_type", "image"],
	onload: function(listview) {
                 $('.btn-primary').hide()
    },

    formatters: {
        customer_id(val) {
        	return val.toString();
        },
    },

};
