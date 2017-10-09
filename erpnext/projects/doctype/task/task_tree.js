frappe.provide("frappe.treeview_settings");

frappe.treeview_settings['Task'] = {
	get_tree_nodes: "erpnext.projects.doctype.task.task.get_children",
	add_tree_node: "erpnext.projects.doctype.task.task.add_node",
	get_tree_root: false,
	root_label: "Tasks",
	ignore_fields:["parent_task"],
	onload: function(me){
		me.make_tree();
	}
};