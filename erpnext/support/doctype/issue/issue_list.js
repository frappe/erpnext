frappe.listview_settings['Issue'] = {
	colwidths: { "subject": 6 },
	get_indicator: function(doc) {
		return [__(doc.status), erpnext.utils.guess_colour_from_status(doc.status),
			"status,=," + doc.status];
	},
	onload: function(listview) {
		frappe.route_options = {
			"status": "Unreplied"
		};

		var method = "erpnext.support.doctype.issue.issue.set_multiple_status";

		listview.page.add_menu_item(__("Set as Unreplied"), function() {
			listview.call_for_selected_items(method, {"status": "Unreplied"});
		});

		listview.page.add_menu_item(__("Set as Closed"), function() {
			listview.call_for_selected_items(method, {"status": "Closed"});
		});
	}
}
