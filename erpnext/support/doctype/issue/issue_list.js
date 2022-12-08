frappe.listview_settings['Issue'] = {
	colwidths: {"subject": 6},
	add_fields: ['priority', 'status'],
	onload: function(listview) {
		frappe.route_options = {
			"status": ["!=", "Closed"]
		};

		var method = "erpnext.support.doctype.issue.issue.set_multiple_status";

		listview.page.add_menu_item(__("Set as Open"), function() {
			listview.call_for_selected_items(method, {"status": "Open"});
		});

		listview.page.add_menu_item(__("Set as Closed"), function() {
			listview.call_for_selected_items(method, {"status": "Closed"});
		});
	},
	get_indicator: function(doc) {
		let priority_text = doc.priority ? " (" + __(doc.priority) + ")" : "";

		if (doc.status === 'Open') {
			let color;
			if (["High", "Urgent"].includes(doc.priority)) {
				color = "red";
			} else if (doc.priority == "Low") {
				color = "yellow";
			} else {
				color = "orange";
			}

			return [__(doc.status) + priority_text, color, `status,=,Open`];
		} else if (doc.status === 'In Progress') {
			return [__(doc.status) + priority_text, "purple", "status,=," + doc.status];
		} else if (doc.status === 'To Update') {
			return [__(doc.status) + priority_text, "lightblue", "status,=," + doc.status];
		} else if (doc.status === 'Closed') {
			return [__(doc.status) + priority_text, "green", "status,=," + doc.status];
		} else if (doc.status === 'Replied') {
			return [__(doc.status) + priority_text, "blue", "status,=," + doc.status];
		} else {
			return [__(doc.status) + priority_text, "darkgrey", "status,=," + doc.status];
		}
	}
}
