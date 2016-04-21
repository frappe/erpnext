{% include 'erpnext/stock/doctype/item/item_dashboard.html' %}

frappe.pages['stock-balance'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Stock Balance',
		single_column: true
	});

	var warehouse_field = page.add_field({
		fieldname: 'wareshouse',
		label: __('Warehouse'),
		fieldtype:'Link',
		options:'Warehouse',
		change: function() {
			page.start = 0;
			refresh()
		}
	});

	var item_field = page.add_field({
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
	page.sort_by = 'actual_qty';
	page.sort_order = 'desc';

	page.content = $(frappe.render_template('stock_balance')).appendTo(page.main);
	page.result = page.content.find('.result');

	// more
	page.content.find('.btn-more').on('click', function() {
			page.start += 20;
			refresh();
		});

	// order
	page.content.find('.btn-order').on('click', function() {
		var btn = $(this);
		var order = $(this).attr('data-value')==='desc' ? 'asc' : 'desc';

		btn.attr('data-value', order);
		page.sort_order = order;
		btn.find('.octicon')
			.removeClass('octicon-triangle-' + (order==='asc' ? 'down' : 'up'))
			.addClass('octicon-triangle-' + (order==='desc' ? 'down' : 'up'));
		page.start = 0;
		refresh();
	});

	// select field
	page.content.find('.dropdown a.option').on('click', function() {
		page.sort_by = $(this).attr('data-value');
		page.content.find('.dropdown .dropdown-toggle').html($(this).html());
		refresh();
	});

	var refresh = function() {
		var item_code = item_field.get_value();
		var warehouse = warehouse_field.get_value();
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

		var context = erpnext.get_item_dashboard_data(data, page.max_count);
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

}