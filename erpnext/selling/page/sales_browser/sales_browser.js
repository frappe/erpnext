// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

pscript['onload_Sales Browser'] = function(wrapper){
	frappe.ui.make_app_page({
		parent: wrapper,
	})

	wrapper.appframe.add_module_icon("Selling")

	wrapper.appframe.set_title_right(__('Refresh'), function() {
			wrapper.make_tree();
		});


	$(wrapper)
		.find(".layout-side-section")
		.html('<div class="text-muted">'+
			__('Click on a link to get options to expand get options ') +
			__('Add') + ' / ' + __('Edit') + ' / '+ __('Delete') + '.</div>')

	wrapper.make_tree = function() {
		var ctype = frappe.get_route()[1] || 'Territory';
		return frappe.call({
			method: 'erpnext.selling.page.sales_browser.sales_browser.get_children',
			args: {ctype: ctype},
			callback: function(r) {
				var root = r.message[0]["value"];
				erpnext.sales_chart = new erpnext.SalesChart(ctype, root,
					$(wrapper)
						.find(".layout-main-section")
						.css({
							"min-height": "300px",
							"padding-bottom": "25px"
						}));
			}
		});
	}

	wrapper.make_tree();
}

pscript['onshow_Sales Browser'] = function(wrapper){
	// set route
	var ctype = frappe.get_route()[1] || 'Territory';

	wrapper.appframe.set_title(__('{0} Tree',[__(ctype)]));

	if(erpnext.sales_chart && erpnext.sales_chart.ctype != ctype) {
		wrapper.make_tree();
	}
};

erpnext.SalesChart = Class.extend({
	init: function(ctype, root, parent) {
		$(parent).empty();
		var me = this;
		me.ctype = ctype;
		me.can_read = frappe.model.can_read(this.ctype);
		me.can_create = frappe.boot.user.can_create.indexOf(this.ctype) !== -1 ||
					frappe.boot.user.in_create.indexOf(this.ctype) !== -1;
		me.can_write = frappe.model.can_write(this.ctype);
		me.can_delete = frappe.model.can_delete(this.ctype);

		this.tree = new frappe.ui.Tree({
			parent: $(parent),
			label: __(root),
			args: {ctype: ctype},
			method: 'erpnext.selling.page.sales_browser.sales_browser.get_children',
			toolbar: [
				{toggle_btn: true},
				{
					label:__("Edit"),
					condition: function(node) {
						return !node.root && me.can_read;
					},
					click: function(node) {
						frappe.set_route("Form", me.ctype, node.label);
					}
				},
				{
					label:__("Add Child"),
					condition: function(node) { return me.can_create && node.expandable; },
					click: function(node) {
						me.new_node();
					}
				},
				{
					label:__("Rename"),
					condition: function(node) { return !node.root && me.can_write; },
					click: function(node) {
						frappe.model.rename_doc(me.ctype, node.label, function(new_name) {
							node.$a.html(new_name);
						});
					}
				},
				{
					label:__("Delete"),
					condition: function(node) { return !node.root && me.can_delete; },
					click: function(node) {
						frappe.model.delete_doc(me.ctype, node.label, function() {
							node.parent.remove();
						});
					}
				}

			]
		});
	},
	new_node: function() {
		var me = this;

		var fields = [
			{fieldtype:'Data', fieldname: 'name_field',
				label:__('New {0} Name',[__(me.ctype)]), reqd:true},
			{fieldtype:'Select', fieldname:'is_group', label:__('Group Node'), options:'No\nYes',
				description: __("Further nodes can be only created under 'Group' type nodes")},
			{fieldtype:'Button', fieldname:'create_new', label:__('Create New') }
		]

		if(me.ctype == "Sales Person") {
			fields.splice(-1, 0, {fieldtype:'Link', fieldname:'employee', label:__('Employee'),
				options:'Employee', description: __("Please enter Employee Id of this sales parson")});
		}

		// the dialog
		var d = new frappe.ui.Dialog({
			title: __('New {0}',[__(me.ctype)]),
			fields: fields
		})

		d.set_value("is_group", "No");
		// create
		$(d.fields_dict.create_new.input).click(function() {
			var btn = this;
			var v = d.get_values();
			if(!v) return;

			var node = me.tree.get_selected_node();

			v.parent = node.label;
			v.ctype = me.ctype;

			return frappe.call({
				method: 'erpnext.selling.page.sales_browser.sales_browser.add_node',
				args: v,
				callback: function(r) {
					if(!r.exc) {
						d.hide();
						if(node.expanded) {
							node.toggle_node();
						}
						node.reload();
					}
				}
			});
		});
		d.show();
	},
});
