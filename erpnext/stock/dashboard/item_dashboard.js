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

		// If not any stock in any warehouses provide a message to end user
		if (context.data.length > 0) {
			$(frappe.render_template('item_dashboard_list', context)).appendTo(this.result);
		} else {
			var message = __(" Currently no stock available in any warehouse")
			$("<span class='text-muted small'>"+message+"</span>").appendTo(this.result);
		}
	},
	get_item_dashboard_data: function(data, max_count, show_item) {
		if(!max_count) max_count = 0;
		if(!data) data = [];

		data.forEach(function(d) {
			d.actual_or_pending = d.projected_qty + d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract;
			d.pending_qty = 0;
			d.total_reserved = d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract;
			if(d.actual_or_pending > d.actual_qty) {
				d.pending_qty = d.actual_or_pending - d.actual_qty;
			}

			max_count = Math.max(d.actual_or_pending, d.actual_qty,
				d.total_reserved, max_count);
		});

		var can_write = 0;
		if(frappe.boot.user.can_write.indexOf("Stock Entry")>=0){
			can_write = 1;
		}

		return {
			data: data,
			max_count: max_count,
			can_write:can_write,
			show_item: show_item || false
		}
	}
})