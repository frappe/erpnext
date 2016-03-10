frappe.listview_settings['Task'] = {
	add_fields: ["project", "status", "priority", "exp_end_date"],
	onload: function(listview) {
		var method = "erpnext.projects.doctype.task.task.set_multiple_status";

		listview.page.add_menu_item(__("Set as Open"), function() {
			listview.call_for_selected_items(method, {"status": "Open"});
		});

		listview.page.add_menu_item(__("Set as Closed"), function() {
			listview.call_for_selected_items(method, {"status": "Closed"});
		});
	},
	get_indicator: function(doc) {
		var colors = {
			"Open": "orange",
			"Overdue": "red",
			"Pending Review": "orange",
			"Working": "orange",
			"Closed": "green",
			"Cancelled": "dark grey"
		}
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	}

};
