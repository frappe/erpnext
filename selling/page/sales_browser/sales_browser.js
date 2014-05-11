// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

pscript['onload_Sales Browser'] = function(wrapper){
	wn.ui.make_app_page({
		parent: wrapper,
	})
	
	wrapper.appframe.add_module_icon("Selling")
	
	wrapper.appframe.set_title_right('Refresh', function() {  
			wrapper.make_tree();
		});


	$(wrapper)
		.find(".layout-side-section")
		.html('<div class="text-muted">'+ 
			wn._('Click on a link to get options to expand get options ') + 
			wn._('Add') + ' / ' + wn._('Edit') + ' / '+ wn._('Delete') + '.</div>')

	wrapper.make_tree = function() {
		var ctype = wn.get_route()[1] || 'Territory';
		return wn.call({
			method: 'selling.page.sales_browser.sales_browser.get_children',
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
	var ctype = wn.get_route()[1] || 'Territory';

	wrapper.appframe.set_title(ctype+' Tree')

	if(erpnext.sales_chart && erpnext.sales_chart.ctype != ctype) {
		wrapper.make_tree();
	}
};

erpnext.SalesChart = Class.extend({
	init: function(ctype, root, parent) {
		$(parent).empty();
		var me = this;
		me.ctype = ctype;
		this.tree = new wn.ui.Tree({
			parent: $(parent), 
			label: root,
			args: {ctype: ctype},
			method: 'selling.page.sales_browser.sales_browser.get_children',
			click: function(link) {
				if(me.cur_toolbar) 
					$(me.cur_toolbar).toggle(false);

				if(!link.toolbar) 
					me.make_link_toolbar(link);

				if(link.toolbar) {
					me.cur_toolbar = link.toolbar;
					$(me.cur_toolbar).toggle(true);					
				}
			}
		});
		this.tree.rootnode.$a
			.data('node-data', {value: root, expandable:1})
			.click();		
	},
	make_link_toolbar: function(link) {
		var data = $(link).data('node-data');
		if(!data) return;

		link.toolbar = $('<span class="tree-node-toolbar"></span>').insertAfter(link);
		
		// edit
		var node_links = [];
		
		if (wn.model.can_read(this.ctype)) {
			node_links.push('<a onclick="erpnext.sales_chart.open();">'+wn._('Edit')+'</a>');
		}

		if(data.expandable) {
			if (wn.boot.profile.can_create.indexOf(this.ctype) !== -1 ||
					wn.boot.profile.in_create.indexOf(this.ctype) !== -1) {
				node_links.push('<a onclick="erpnext.sales_chart.new_node();">' + wn._('Add Child') + '</a>');
			}
		}

		if (wn.model.can_write(this.ctype)) {
			node_links.push('<a onclick="erpnext.sales_chart.rename()">' + wn._('Rename') + '</a>');
		};
	
		if (wn.model.can_delete(this.ctype)) {
			node_links.push('<a onclick="erpnext.sales_chart.delete()">' + wn._('Delete') + '</a>');
		};
		
		link.toolbar.append(node_links.join(" | "));
	},
	new_node: function() {
		var me = this;
		
		var fields = [
			{fieldtype:'Data', fieldname: 'name_field', 
				label:'New ' + me.ctype + ' Name', reqd:true},
			{fieldtype:'Select', fieldname:'is_group', label:'Group Node', options:'No\nYes', 
				description: wn._("Further nodes can be only created under 'Group' type nodes")}, 
			{fieldtype:'Button', fieldname:'create_new', label:'Create New' }
		]
		
		if(me.ctype == "Sales Person") {
			fields.splice(-1, 0, {fieldtype:'Link', fieldname:'employee', label:'Employee',
				options:'Employee', description: wn._("Please enter Employee Id of this sales parson")});
		}
		
		// the dialog
		var d = new wn.ui.Dialog({
			title: wn._('New ') + wn._(me.ctype),
			fields: fields
		})		
	
		d.set_value("is_group", "No");
		// create
		$(d.fields_dict.create_new.input).click(function() {
			var btn = this;
			$(btn).set_working();
			var v = d.get_values();
			if(!v) return;
			
			var node = me.selected_node();
			
			v.parent = node.data('label');
			v.ctype = me.ctype;
			
			return wn.call({
				method: 'selling.page.sales_browser.sales_browser.add_node',
				args: v,
				callback: function() {
					$(btn).done_working();
					d.hide();
					node.trigger('reload');
				}	
			})			
		});
		d.show();		
	},
	selected_node: function() {
		return this.tree.$w.find('.tree-link.selected');
	},
	open: function() {
		var node = this.selected_node();
		wn.set_route("Form", this.ctype, node.data("label"));
	},
	rename: function() {
		var node = this.selected_node();
		wn.model.rename_doc(this.ctype, node.data('label'), function(new_name) {
			node.data('label', new_name).find(".tree-label").html(new_name);
		});
	},
	delete: function() {
		var node = this.selected_node();
		wn.model.delete_doc(this.ctype, node.data('label'), function() {
			node.parent().remove();
		});
	},
});