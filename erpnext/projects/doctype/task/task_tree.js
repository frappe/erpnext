frappe.provide("frappe.treeview_settings");

frappe.treeview_settings['Task'] = {
	get_tree_nodes: "erpnext.projects.doctype.task.task.get_children",
	add_tree_node: "erpnext.projects.doctype.task.task.add_node",
	filters: [
		{
			fieldname: "project",
			fieldtype:"Link",
			options: "Project",
			label: __("Project"),
		},
		{
			fieldname: "task",
			fieldtype:"Link",
			options: "Task",
			label: __("Task"),
			get_query: function() {
				var me = frappe.treeview_settings['Task'];
				var project = me.page.fields_dict.project.get_value();
				var args = [["Task", 'is_group', '=', 1]];
				if(project){
					args.push(["Task", 'project', "=", project]);
				}
				return {
					filters: args
				};
			}
		}
	],
	breadcrumb: "Projects",
	get_tree_root: false,
	root_label: "All Tasks",
	ignore_fields: ["parent_task"],
	onload: function(me) {
		frappe.treeview_settings['Task'].page = {};
		$.extend(frappe.treeview_settings['Task'].page, me.page);
		me.make_tree();
	},
	toolbar: [
		{
			label:__("Add Multiple"),
			condition: function(node) {
				return node.expandable;
			},
			click: function(node) {
				var d = new frappe.ui.Dialog({
					'fields': [
						{'fieldname': 'tasks', 'label': 'Tasks', 'fieldtype': 'Text'},
					],
					primary_action: function() {
						d.hide();
						return frappe.call({
							method: "erpnext.projects.doctype.task.task.add_multiple_tasks",
							args: {
								data: d.get_values(),
								parent: node.data.value
							},
							callback: function() { }
						});
					}
				});
				d.show();
			}
		}
	],
	extend_toolbar: true
};