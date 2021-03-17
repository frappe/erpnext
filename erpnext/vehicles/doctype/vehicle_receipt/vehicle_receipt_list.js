frappe.listview_settings['Vehicle Receipt'] = {
	onload: function(listview) {
		listview.page.fields_dict.item_code.get_query = () => erpnext.queries.item({"is_vehicle": 1});
	}
};
