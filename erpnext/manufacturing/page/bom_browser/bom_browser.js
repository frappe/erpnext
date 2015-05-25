// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.pages['bom-browser'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'BOM Browser',
		single_column: true
	});

	page.main.css({
		"min-height": "300px",
		"padding-bottom": "25px"
	});

	page.tree_area = $('<div class="padding"><p class="text-muted">'+
		__("Select BOM to start")
		+'</p></div>').appendTo(page.main);

	frappe.breadcrumbs.add(frappe.breadcrumbs.last_module || "Manufacturing");

	var make_tree = function() {
		erpnext.bom_tree = new erpnext.BOMTree(page.$bom_select.val(), page, page.tree_area);
	}

	page.$bom_select = wrapper.page.add_field({fieldname: "bom",
		fieldtype:"Link", options: "BOM", label: __("BOM")}).$input
		.change(function() {
			make_tree();
		});

	page.set_secondary_action(__('Refresh'), function() {
		make_tree();
	});
}


frappe.pages['bom-browser'].on_page_show = function(wrapper){
	// set from route
	var bom = null;
	if(frappe.get_route()[1]) {
		var bom = frappe.get_route().splice(1).join("/");
	}
	if(frappe.route_options && frappe.route_options.bom) {
		var bom = frappe.route_options.bom;
	}
	if(bom) {
		wrapper.page.$bom_select.val(bom).trigger("change");
	}
};

erpnext.BOMTree = Class.extend({
	init: function(root, page, parent) {
		$(parent).empty();
		var me = this;
		me.page = page;
		me.bom = page.$bom_select.val();
		me.can_read = frappe.model.can_read("BOM");
		me.can_create = frappe.boot.user.can_create.indexOf("BOM") !== -1 ||
					frappe.boot.user.in_create.indexOf("BOM") !== -1;
		me.can_write = frappe.model.can_write("BOM");
		me.can_delete = frappe.model.can_delete("BOM");

		this.tree = new frappe.ui.Tree({
			parent: $(parent),
			label: me.bom,
			args: {parent: me.bom},
			method: 'erpnext.manufacturing.page.bom_browser.bom_browser.get_children',
			toolbar: [
				{toggle_btn: true},
				{
					label:__("Edit"),
					condition: function(node) {
						return node.expandable;
					},
					click: function(node) {
						frappe.set_route("Form", "BOM", node.data.parent);
					}
				}
			],
			get_label: function(node) {
				if(node.data.qty) {
					return node.data.qty + " x " + node.data.value;
				} else {
					return node.data.value;
				}
			}
		});
	}
});
