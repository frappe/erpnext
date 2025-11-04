frappe.treeview_settings["BOM"] = {
	get_tree_nodes: "erpnext.manufacturing.doctype.bom.bom.get_children",
	filters: [
		{
			fieldname: "bom",
			fieldtype: "Link",
			options: "BOM",
			label: __("BOM"),
		},
	],
	title: "BOM",
	breadcrumb: "Manufacturing",
	disable_add_node: true,
	root_label: "BOM", //fieldname from filters
	get_tree_root: false,
	show_expand_all: false,
	get_label: function (node) {
		if (node.data.qty) {
			const escape = frappe.utils.escape_html;
			let label = escape(node.data.item_code);
			if (node.data.item_name && node.data.item_code !== node.data.item_name) {
				label += `: ${escape(node.data.item_name)}`;
			}
			return `${label} <span class="badge badge-pill badge-light">${node.data.qty} ${escape(
				__(node.data.stock_uom)
			)}</span>`;
		} else {
			return node.data.item_code || node.data.value;
		}
	},
	onload: function (me) {
		var label = frappe.get_route()[0] + "/" + frappe.get_route()[1];
		if (frappe.pages[label]) {
			delete frappe.pages[label];
		}

		var filter = me.opts.filters[0];
		if (frappe.route_options && frappe.route_options[filter.fieldname]) {
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
			label: __("Edit"),
			condition: function (node) {
				return node.expandable;
			},
			click: function (node) {
				frappe.set_route("Form", "BOM", node.data.value);
			},
		},
	],
	menu_items: [
		{
			label: __("New BOM"),
			action: function () {
				frappe.new_doc("BOM", true);
			},
			condition: 'frappe.boot.user.can_create.indexOf("BOM") !== -1',
		},
	],
	onrender: function (node) {
		if (node.is_root && node.data.value != "BOM") {
			frappe.model.with_doc("BOM", node.data.value, function () {
				var bom = frappe.model.get_doc("BOM", node.data.value);
				node.data.image = bom.image || "";
				node.data.description = bom.description || "";
				node.data.item_code = bom.item || "";
			});
		}
	},
	view_template: "bom_item_preview",
};
