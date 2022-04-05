frappe.pages['warehouse-capacity-summary'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Warehouse Capacity Summary',
		single_column: true
	});
	page.set_secondary_action('Refresh', () => page.capacity_dashboard.refresh(), 'refresh');
	page.start = 0;

	page.company_field = page.add_field({
		fieldname: 'company',
		label: __('Company'),
		fieldtype: 'Link',
		options: 'Company',
		reqd: 1,
		default: frappe.defaults.get_default("company"),
		change: function() {
			page.capacity_dashboard.start = 0;
			page.capacity_dashboard.refresh();
		}
	});

	page.warehouse_field = page.add_field({
		fieldname: 'warehouse',
		label: __('Warehouse'),
		fieldtype: 'Link',
		options: 'Warehouse',
		change: function() {
			page.capacity_dashboard.start = 0;
			page.capacity_dashboard.refresh();
		}
	});

	page.item_field = page.add_field({
		fieldname: 'item_code',
		label: __('Item'),
		fieldtype: 'Link',
		options: 'Item',
		change: function() {
			page.capacity_dashboard.start = 0;
			page.capacity_dashboard.refresh();
		}
	});

	page.parent_warehouse_field = page.add_field({
		fieldname: 'parent_warehouse',
		label: __('Parent Warehouse'),
		fieldtype: 'Link',
		options: 'Warehouse',
		get_query: function() {
			return {
				filters: {
					"is_group": 1
				}
			};
		},
		change: function() {
			page.capacity_dashboard.start = 0;
			page.capacity_dashboard.refresh();
		}
	});

	page.sort_selector = new frappe.ui.SortSelector({
		parent: page.wrapper.find('.page-form'),
		args: {
			sort_by: 'stock_capacity',
			sort_order: 'desc',
			options: [
				{fieldname: 'stock_capacity', label: __('Capacity (Stock UOM)')},
				{fieldname: 'percent_occupied', label: __('% Occupied')},
				{fieldname: 'actual_qty', label: __('Balance Qty (Stock)')}
			]
		},
		change: function(sort_by, sort_order) {
			page.capacity_dashboard.sort_by = sort_by;
			page.capacity_dashboard.sort_order = sort_order;
			page.capacity_dashboard.start = 0;
			page.capacity_dashboard.refresh();
		}
	});

	frappe.require('item-dashboard.bundle.js', function() {
		$(frappe.render_template('warehouse_capacity_summary_header')).appendTo(page.main);

		page.capacity_dashboard = new erpnext.stock.ItemDashboard({
			page_name: "warehouse-capacity-summary",
			page_length: 10,
			parent: page.main,
			sort_by: 'stock_capacity',
			sort_order: 'desc',
			method: 'erpnext.stock.dashboard.warehouse_capacity_dashboard.get_data',
			template: 'warehouse_capacity_summary'
		});

		page.capacity_dashboard.before_refresh = function() {
			this.item_code = page.item_field.get_value();
			this.warehouse = page.warehouse_field.get_value();
			this.parent_warehouse = page.parent_warehouse_field.get_value();
			this.company = page.company_field.get_value();
		};

		page.capacity_dashboard.refresh();

		let setup_click = function(doctype) {
			page.main.on('click', 'a[data-type="'+ doctype.toLowerCase() +'"]', function() {
				var name = $(this).attr('data-name');
				var field = page[doctype.toLowerCase() + '_field'];
				if (field.get_value()===name) {
					frappe.set_route('Form', doctype, name);
				} else {
					field.set_input(name);
					page.capacity_dashboard.refresh();
				}
			});
		};

		setup_click('Item');
		setup_click('Warehouse');
	});
};
