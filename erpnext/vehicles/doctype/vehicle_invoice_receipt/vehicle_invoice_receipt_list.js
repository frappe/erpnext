frappe.listview_settings['Vehicle Invoice Receipt'] = {
	onload: function(listview) {
		listview.page.fields_dict.item_code.get_query = () => erpnext.queries.item({
			"is_vehicle": 1, "include_in_vehicle_booking": 1
		});
	}
};
