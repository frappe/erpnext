frappe.listview_settings['Payment Entry'] = {

	onload: function(listview) {
		listview.page.fields_dict.party_type.get_query = function() {
			return {
				"filters": {
					"name": ["in", Object.keys(frappe.boot.party_account_types)],
				}
			};
		};
	}
};