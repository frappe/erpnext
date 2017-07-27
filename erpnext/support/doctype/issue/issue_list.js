frappe.listview_settings['Issue'] = {
	colwidths: {"subject": 6},
	onload: function(listview) {
		frappe.route_options = {
			"status": "Open"
		};

		var method = "erpnext.support.doctype.issue.issue.set_multiple_status";

		listview.page.add_menu_item(__("Set as Open"), function() {
			listview.call_for_selected_items(method, {"status": "Open"});
		});

		listview.page.add_menu_item(__("Set as Closed"), function() {
			listview.call_for_selected_items(method, {"status": "Closed"});
		});
	}
}
