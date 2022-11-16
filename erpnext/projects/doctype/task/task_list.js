frappe.listview_settings['Task'] = {
	add_fields: ["project", "status", "priority", "exp_start_date", "exp_end_date", "subject", "progress",
		"depends_on_tasks"],

	get_indicator: function(doc) {
		var colors = {
			"Open": "orange",
			"Overdue": "red",
			"Pending Review": "lightblue",
			"Working": "purple",
			"Completed": "green",
			"Cancelled": "darkgrey"
		}
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	},

	onload: function(listview) {
		var set_status_method = "erpnext.projects.doctype.task.task.set_multiple_status";

		listview.page.add_actions_menu_item(__("Set as Open"), function() {
			listview.call_for_selected_items(set_status_method, {"status": "Open"});
		});

		listview.page.add_actions_menu_item(__("Set as Completed"), function() {
			listview.call_for_selected_items(set_status_method, {"status": "Completed"});
		});

		listview.page.fields_dict.parent_task.get_query = () => {
			var filters = {};

			var project = listview.page.fields_dict.project.get_value('project');
			var issue = listview.page.fields_dict.issue.get_value('issue');
			if (project) {
				filters['project'] = project;
			} else if (issue) {
				filters['issue'] = issue;
			}

			filters['is_group'] = 1;
			return {filters: filters};
		}
	},

	gantt_custom_popup_html: function(ganttobj, task) {
		var html = `<h5><a style="text-decoration:underline"\
			href="/app/task/${ganttobj.id}"">${ganttobj.name}</a></h5>`;

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
