frappe.listview_settings['Task'] = {
	add_fields: ["project", "status", "priority", "exp_start_date",
		"exp_end_date", "subject", "progress", "depends_on_tasks"],
	filters: [["status", "=", "Open"]],
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
	},
	gantt_custom_popup_html: function(ganttobj, task) {
		var html = `<h5>${ganttobj.name}</h5>`;
		if(task.project) html += `<p>Project: ${task.project}</p>`;
		html += `<p>Progress: ${ganttobj.progress}</p>`;

		if(task._assign_list) {
			html += task._assign_list.reduce(
				(html, user) => html + frappe.avatar(user)
			, '');
		}

		return html;
	}

};
