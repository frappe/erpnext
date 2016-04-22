{% include 'erpnext/stock/doctype/item/item_dashboard.html' %}

frappe.pages['stock-balance'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Stock Balance',
		single_column: true
	});

	page.warehouse_field = page.add_field({
		fieldname: 'wareshouse',
		label: __('Warehouse'),
		fieldtype:'Link',
		options:'Warehouse',
		change: function() {
			page.start = 0;
			refresh()
		}
	});

	page.item_field = page.add_field({
		fieldname: 'item_code',
		label: __('Item'),
		fieldtype:'Link',
		options:'Item',
		change: function() {
			page.start = 0;
			refresh()
		}
	});

	page.start = 0;
	page.sort_by = 'projected_qty';
	page.sort_order = 'asc';

	page.content = $(frappe.render_template('stock_balance')).appendTo(page.main);
	page.result = page.content.find('.result');

	// more
	page.content.find('.btn-more').on('click', function() {
			page.start += 20;
			refresh();
		});

	// move
	page.content.on('click', '.btn-move', function() {
		erpnext.inventory.move_item($(this).attr('data-item'), $(this).attr('data-warehouse'),
			null, $(this).attr('data-actual_qty'), function() { refresh(); });
	});

	page.content.on('click', '.btn-add', function() {
		erpnext.inventory.move_item($(this).attr('data-item'), null, $(this).attr('data-warehouse'),
			$(this).attr('data-actual_qty'), function() { refresh(); });
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
				{fieldname: 'actual_qty', label: __('Acutal qty in stock')},
			]
		},
		change: function(sort_by, sort_order) {
			page.sort_by = sort_by;
			page.sort_order = sort_order;
			page.start = 0;
			refresh();
		}
	});

	page.sort_selector.wrapper.css({'margin-right': '15px', 'margin-top': '4px'});

	var refresh = function() {
		var item_code = page.item_field.get_value();
		var warehouse = page.warehouse_field.get_value();
		frappe.call({
			method: 'erpnext.stock.page.stock_balance.stock_balance.get_data',
			args: {
				item_code: item_code,
				warehouse: warehouse,
				start: page.start,
				sort_by: page.sort_by,
				sort_order: page.sort_order,
			},
			callback: function(r) {
				render(r.message);
			}
		});
	}

	var render = function(data) {
		if(page.start===0) {
			page.max_count = 0;
			page.result.empty();
		}

		var context = erpnext.get_item_dashboard_data(data, page.max_count, true);
		page.max_count = context.max_count;

		// show more button
		if(data.length===21) {
			page.content.find('.more').removeClass('hidden');

			// remove the last element
			data.splice(-1);
		} else {
			page.content.find('.more').addClass('hidden');
		}

		$(frappe.render_template('item_dashboard', context)).appendTo(page.result);

	}

	refresh();

	// item click
	var setup_click = function(doctype) {
		page.result.on('click', 'a[data-type="'+ doctype.toLowerCase() +'"]', function() {
			var name = $(this).attr('data-name');
			var field = page[doctype.toLowerCase() + '_field'];
			if(field.get_value()===name) {
				frappe.set_route('Form', doctype, name)
			} else {
				field.set_input(name);
				refresh();
			}
		});
	}

	setup_click('Item');
	setup_click('Warehouse');

}