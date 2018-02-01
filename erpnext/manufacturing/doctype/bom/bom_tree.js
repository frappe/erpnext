frappe.treeview_settings["BOM"] = {
	get_tree_nodes: 'erpnext.manufacturing.doctype.bom.bom.get_children',
	filters: [
		{
			fieldname: "bom",
			fieldtype:"Link",
			options: "BOM",
			label: __("BOM")
		}
	],
	title: "BOM",
	breadcrumb: "Manufacturing",
	disable_add_node: true,
	root_label: "BOM", //fieldname from filters
	get_tree_root: false,
	get_label: function(node) {
		if(node.data.qty) {
			return node.data.qty + " x " + node.data.item_code;
		} else {
			return node.data.item_code || node.data.value;
		}
	},
	onload: function(me) {
		var label = frappe.get_route()[0] + "/" + frappe.get_route()[1];
		if(frappe.pages[label]) {
			delete frappe.pages[label];
		}

		var filter = me.opts.filters[0];
		if(frappe.route_options && frappe.route_options[filter.fieldname]) {
			var val = frappe.route_options[filter.fieldname];
			delete frappe.route_options[filter.fieldname];
			filter.default = "";
			me.args[filter.fieldname] = val;
			me.root_label = val;
			me.page.set_title(val);
		}
		me.make_tree();
	},
	toolbar: [
		{ toggle_btn: true },
		{
			label:__("Edit"),
			condition: function(node) {
				return node.expandable;
			},
			click: function(node) {

				frappe.set_route("Form", "BOM", node.data.value);
			}
		}
	],
	menu_items: [
		{
			label: __("New BOM"),
			action: function() {
				frappe.new_doc("BOM", true)
			},
			condition: 'frappe.boot.user.can_create.indexOf("BOM") !== -1'
		}
	],
	view_template: 'bom_item_preview'
}