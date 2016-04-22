erpnext.get_item_dashboard_data = function(data, max_count, show_item) {
	if(!max_count) max_count = 0;
	data.forEach(function(d) {
		d.actual_or_pending = d.projected_qty + d.reserved_qty + d.reserved_qty_for_production;
		d.pending_qty = 0;
		d.total_reserved = d.reserved_qty + d.reserved_qty_for_production;
		if(d.actual_or_pending > d.actual_qty) {
			d.pending_qty = d.actual_or_pending - d.actual_qty;
		}

		max_count = Math.max(d.actual_or_pending, d.actual_qty,
			d.total_reserved, max_count);
	});
	return {
		data: data,
		max_count: max_count,
		show_item: show_item || false
	}
}

frappe.provide('erpnext.inventory');

erpnext.inventory.move_item = function(item, source, target, actual_qty, callback) {
	var dialog = new frappe.ui.Dialog({
		title: target ? __('Add Item') : __('Move Item'),
		fields: [
			{fieldname: 'item_code', label: __('Item'),
				fieldtype: 'Link', options: 'Item', read_only: 1},
			{fieldname: 'source', label: __('Source Warehouse'),
				fieldtype: 'Link', options: 'Warehouse', read_only: 1},
			{fieldname: 'target', label: __('Target Warehouse'),
				fieldtype: 'Link', options: 'Warehouse', reqd: 1},
			{fieldname: 'qty', label: __('Quantity'), reqd: 1,
				fieldtype: 'Float', description: __('Available {0}', [actual_qty]) },
		],
	})
	dialog.show();
	dialog.get_field('item_code').set_input(item);

	if(source) {
		dialog.get_field('source').set_input(source);
	} else {
		dialog.get_field('source').df.hidden = 1;
		dialog.get_field('source').refresh();
	}

	if(target) {
		dialog.get_field('target').df.read_only = 1;
		dialog.get_field('target').value = target;
		dialog.get_field('target').refresh();
	}

	dialog.set_primary_action(__('Submit'), function() {
		values = dialog.get_values();
		if(!values) {
			return;
		}
		if(source && values.qty > actual_qty) {
			frappe.msgprint(__('Quantity must be less than or equal to {0}', [actual_qty]));
			return;
		}
		if(values.source === values.target) {
			frappe.msgprint(__('Source and target warehouse must be different'));
		}

		frappe.call({
			method: 'erpnext.stock.doctype.stock_entry.stock_entry_utils.make_stock_entry',
			args: values,
			callback: function(r) {
				frappe.show_alert(__('Stock Entry {0} created',
					['<a href="#Form/Stock Entry/'+r.message.name+'">' + r.message.name+ '</a>']));
				dialog.hide();
				callback(r);
			},
		});
	});
}