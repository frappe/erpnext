frappe.provide('erpnext.stock');

erpnext.stock.ItemDashboard = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
		this.make();
	},
	make: function() {
		var me = this;
		this.start = 0;
		if(!this.sort_by) {
			this.sort_by = 'projected_qty';
			this.sort_order = 'asc';
		}

		this.content = $(frappe.render_template('item_dashboard')).appendTo(this.parent);
		this.result = this.content.find('.result');

		// move
		this.content.on('click', '.btn-move', function() {
			erpnext.stock.move_item($(this).attr('data-item'), $(this).attr('data-warehouse'),
				null, $(this).attr('data-actual_qty'), null, function() { me.refresh(); });
		});

		this.content.on('click', '.btn-add', function() {
			erpnext.stock.move_item($(this).attr('data-item'), null, $(this).attr('data-warehouse'),
				$(this).attr('data-actual_qty'), $(this).attr('data-rate'),
				function() { me.refresh(); });
		});

		// more
		this.content.find('.btn-more').on('click', function() {
			me.start += 20;
			me.refresh();
		});

	},
	refresh: function() {
		if(this.before_refresh) {
			this.before_refresh();
		}

		var me = this;
		frappe.call({
			method: 'erpnext.stock.dashboard.item_dashboard.get_data',
			args: {
				item_code: this.item_code,
				warehouse: this.warehouse,
				item_group: this.item_group,
				start: this.start,
				sort_by: this.sort_by,
				sort_order: this.sort_order,
			},
			callback: function(r) {
				me.render(r.message);
			}
		});
	},
	render: function(data) {
		if(this.start===0) {
			this.max_count = 0;
			this.result.empty();
		}

		var context = this.get_item_dashboard_data(data, this.max_count, true);
		this.max_count = this.max_count;

		// show more button
		if(data && data.length===21) {
			this.content.find('.more').removeClass('hidden');

			// remove the last element
			data.splice(-1);
		} else {
			this.content.find('.more').addClass('hidden');
		}

		$(frappe.render_template('item_dashboard_list', context)).appendTo(this.result);

	},
	get_item_dashboard_data: function(data, max_count, show_item) {
		if(!max_count) max_count = 0;
		if(!data) data = [];
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
})

erpnext.stock.move_item = function(item, source, target, actual_qty, rate, callback) {
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
			{fieldname: 'rate', label: __('Rate'), fieldtype: 'Currency', hidden: 1 },
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

	if(rate) {
		dialog.get_field('rate').set_value(rate);
		dialog.get_field('rate').df.hidden = 0;
		dialog.get_field('rate').refresh();
	}

	if(target) {
		dialog.get_field('target').df.read_only = 1;
		dialog.get_field('target').value = target;
		dialog.get_field('target').refresh();
	}

	dialog.set_primary_action(__('Submit'), function() {
		var values = dialog.get_values();
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

	$('<p style="margin-left: 10px;"><a class="link-open text-muted small">'
		+ __("Add more items or open full form") + '</a></p>')
		.appendTo(dialog.body)
		.find('.link-open')
		.on('click', function() {
			frappe.model.with_doctype('Stock Entry', function() {
				var doc = frappe.model.get_new_doc('Stock Entry');
				doc.from_warehouse = dialog.get_value('source');
				doc.to_warehouse = dialog.get_value('target');
				row = frappe.model.add_child(doc, 'items');
				row.item_code = dialog.get_value('item_code');
				row.f_warehouse = dialog.get_value('target');
				row.t_warehouse = dialog.get_value('target');
				row.qty = dialog.get_value('qty');
				row.conversion_factor = 1;
				row.transfer_qty = dialog.get_value('qty');
				row.basic_rate = dialog.get_value('rate');
				frappe.set_route('Form', doc.doctype, doc.name);
			})
		});
}