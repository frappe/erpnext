frappe.pages['stock-balance'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Stock Summary'),
		single_column: true
	});
	page.start = 0;

	page.warehouse_field = page.add_field({
		fieldname: 'warehouse',
		label: __('Warehouse'),
		fieldtype:'Link',
		options:'Warehouse',
		change: function() {
			page.item_dashboard.start = 0;
			page.item_dashboard.refresh();
		}
	});

	page.item_field = page.add_field({
		fieldname: 'item_code',
		label: __('Item'),
		fieldtype:'Link',
		options:'Item',
		change: function() {
			page.item_dashboard.start = 0;
			page.item_dashboard.refresh();
		}
	});

	page.item_group_field = page.add_field({
		fieldname: 'item_group',
		label: __('Item Group'),
		fieldtype:'Link',
		options:'Item Group',
		change: function() {
			page.item_dashboard.start = 0;
			page.item_dashboard.refresh();
		}
	});

	page.sort_selector = new frappe.ui.SortSelector({
		parent: page.wrapper.find('.page-form'),
		args: {
			sort_by: 'projected_qty',
			sort_order: 'asc',
			options: [
				{fieldname: 'projected_qty', label: __('Projected qty')},
				{fieldname: 'reserved_qty', label: __('Reserved for sale')},
				{fieldname: 'reserved_qty_for_production', label: __('Reserved for manufacturing')},
				{fieldname: 'reserved_qty_for_sub_contract', label: __('Reserved for sub contracting')},
				{fieldname: 'actual_qty', label: __('Actual qty in stock')},
			]
		},
		change: function(sort_by, sort_order) {
			page.item_dashboard.sort_by = sort_by;
			page.item_dashboard.sort_order = sort_order;
			page.item_dashboard.start = 0;
			page.item_dashboard.refresh();
		}
	});

	// page.sort_selector.wrapper.css({'margin-right': '15px', 'margin-top': '4px'});

	frappe.require('item-dashboard.bundle.js', function() {
		page.item_dashboard = new erpnext.stock.ItemDashboard({
			parent: page.main,
			page_length: 20,
			method: 'erpnext.stock.dashboard.item_dashboard.get_data',
			template: 'item_dashboard_list'
		})

		page.item_dashboard.before_refresh = function() {
			this.item_code = page.item_field.get_value();
			this.warehouse = page.warehouse_field.get_value();
			this.item_group = page.item_group_field.get_value();
		}

		page.item_dashboard.refresh();

		// item click
		var setup_click = function(doctype) {
			page.main.on('click', 'a[data-type="'+ doctype.toLowerCase() +'"]', function() {
				var name = $(this).attr('data-name');
				var field = page[doctype.toLowerCase() + '_field'];
				if(field.get_value()===name) {
					frappe.set_route('Form', doctype, name)
				} else {
					field.set_input(name);
					page.item_dashboard.refresh();
				}
			});
		}

		setup_click('Item');
		setup_click('Warehouse');
	});


}
