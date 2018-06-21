
erpnext.SerialNoBatchSelector = Class.extend({
	init: function(opts, show_dialog) {
		$.extend(this, opts);
		this.show_dialog = show_dialog;
		// frm, item, warehouse_details, has_batch, oldest
		let d = this.item;

		// Don't show dialog if batch no or serial no already set
		if(d && d.has_batch_no && (!d.batch_no || this.show_dialog)) {
			this.has_batch = 1;
			this.setup();
		} else if(d && d.has_serial_no && (!d.serial_no || this.show_dialog)) {
			this.has_batch = 0;
			this.setup();
		}
	},

	setup: function() {
		this.item_code = this.item.item_code;
		this.qty = this.item.qty;
		this.make_dialog();
		this.on_close_dialog();
	},

	make_dialog: function() {
		var me = this;

		this.data = this.oldest ? this.oldest : [];
		let title = "";
		let fields = [
			{
				fieldname: 'item_code',
				read_only: 1,
				fieldtype:'Link',
				options: 'Item',
				label: __('Item Code'),
				default: me.item_code
			},
			{fieldtype:'Column Break'},
			{
				fieldname: 'warehouse',
				fieldtype:'Link',
				options: 'Warehouse',
				label: __(me.warehouse_details.type),
				default: me.warehouse_details.name,
				onchange: function(e) {
					me.warehouse_details.name = this.get_value();
					var batches = this.layout.fields_dict.batches;
					if(batches) {
						batches.grid.df.data = [];
						batches.grid.refresh();
						batches.grid.add_new_row(null, null, null);
					}
				},
				get_query: function() {
					return {
						query: "erpnext.controllers.queries.warehouse_query",
						filters: [
							["Bin", "item_code", "=", me.item_code],
							["Warehouse", "is_group", "=", 0],
							["Warehouse", "company", "=", me.frm.doc.company]
						]
					}
				}
			},
			{fieldtype:'Column Break'},
			{
				fieldname: 'qty',
				fieldtype:'Float',
				read_only: 1,
				label: __(me.has_batch ? 'Total Qty' : 'Qty'),
				default: 0
			},
		];

		if(this.has_batch) {
			title = __("Select Batch Numbers");
			fields = fields.concat(this.get_batch_fields());
		} else {
			title = __("Select Serial Numbers");
			fields = fields.concat(this.get_serial_no_fields());
		}

		this.dialog = new frappe.ui.Dialog({
			title: title,
			fields: fields
		});

		this.dialog.set_primary_action(__('Insert'), function() {
			me.values = me.dialog.get_values();
			if(me.validate()) {
				me.set_items();
				me.dialog.hide();
			}
		});

		if(this.show_dialog) {
			let d = this.item;
			if (d.has_serial_no && d.serial_no) {
				this.dialog.set_value('serial_no', d.serial_no);
			}

			if (d.batch_no) {
				this.frm.doc.items.forEach(data => {
					if(data.item_code == d.item_code) {
						this.dialog.fields_dict.batches.df.data.push({
							'batch_no': data.batch_no,
							'actual_qty': data.actual_qty,
							'selected_qty': data.qty,
							'available_qty': data.actual_batch_qty
						});
					}
				});
				this.dialog.fields_dict.batches.grid.refresh();
			}
		}

		if (this.has_batch) {
			this.update_total_qty();
		}

		this.dialog.show();
	},

	on_close_dialog: function() {
		this.dialog.get_close_btn().on('click', () => {
			this.on_close && this.on_close(this.item);
		});
	},

	validate: function() {
		let values = this.values;
		if(!values.warehouse) {
			frappe.throw(__("Please select a warehouse"));
			return false;
		}
		if(this.has_batch) {
			if(values.batches.length === 0 || !values.batches) {
				frappe.throw(__("Please select batches for batched item "
					+ values.item_code));
				return false;
			}
			values.batches.map((batch, i) => {
				if(!batch.selected_qty || batch.selected_qty === 0 ) {
					if (!this.show_dialog) {
						frappe.throw(__("Please select quantity on row " + (i+1)));
						return false;
					}
				}
			});
			return true;

		} else {
			let serial_nos = values.serial_no || '';
			if (!serial_nos || !serial_nos.replace(/\s/g, '').length) {
				if (!this.show_dialog) {
					frappe.throw(__("Please enter serial numbers for serialized item "
						+ values.item_code));
					return false;
				}
			}
			return true;
		}
	},

	set_items: function() {
		var me = this;
		if(this.has_batch) {
			this.values.batches.map((batch, i) => {
				let batch_no = batch.batch_no;
				let row = '';

				if (i !== 0 && !this.batch_exists(batch_no)) {
					row = this.frm.add_child("items", {
						'item_code': this.item.item_code,
						'item_name': this.item.item_name,
						'price_list_rate': this.item.price_list_rate,
						'rate': this.item.rate,
						'qty': batch.selected_qty,
						'batch_no': batch_no,
						'actual_qty': this.item.actual_qty,
						'discount_percentage': this.item.discount_percentage
					});
				} else {
					row = this.frm.doc.items.find(i => i.batch_no === batch_no);
				}

				if (!row) {
					row = this.item;
				}

				this.map_row_values(row, batch, 'batch_no',
					'selected_qty', this.values.warehouse);
			});
		} else {
			this.map_row_values(this.item, this.values, 'serial_no', 'qty');
		}

		refresh_field("items");
		this.callback && this.callback(this.item);
	},

	batch_exists: function(batch) {
		const batches = this.frm.doc.items.map(data => data.batch_no);
		return (batches && in_list(batches, batch)) ? true : false;
	},

	map_row_values: function(row, values, number, qty_field, warehouse) {
		row.qty = values[qty_field];
		row[number] = values[number];
		if(this.warehouse_details.type === 'Source Warehouse') {
			row.s_warehouse = values.warehouse || warehouse;
		} else if(this.warehouse_details.type === 'Target Warehouse') {
			row.t_warehouse = values.warehouse || warehouse;
		} else {
			row.warehouse = values.warehouse || warehouse;
		}
	},

	update_total_qty: function() {
		let qty_field = this.dialog.fields_dict.qty;
		let total_qty = 0;

		this.dialog.fields_dict.batches.df.data.forEach(data => {
			total_qty += flt(data.selected_qty);
		});

		qty_field.set_input(total_qty);
	},

	get_batch_fields: function() {
		var me = this;
		return [
			{fieldtype:'Section Break', label: __('Batches')},
			{fieldname: 'batches', fieldtype: 'Table',
				fields: [
					{
						fieldtype:'Link',
						fieldname:'batch_no',
						options: 'Batch',
						label: __('Select Batch'),
						in_list_view:1,
						get_query: function() {
							return {
							    filters: {item: me.item_code },
							    query: 'erpnext.controllers.queries.get_batch_numbers'
					        };
						},
						onchange: function(e) {
							let val = this.get_value();
							if(val.length === 0) {
								this.grid_row.on_grid_fields_dict
									.available_qty.set_value(0);
								return;
							}
							let selected_batches = this.grid.grid_rows.map((row) => {
								if(row === this.grid_row) {
									return "";
								}

								if (row.on_grid_fields_dict.batch_no) {
									return row.on_grid_fields_dict.batch_no.get_value();
								}
							});
							if(selected_batches.includes(val)) {
								this.set_value("");
								frappe.throw(__(`Batch ${val} already selected.`));
								return;
							}
							if(me.warehouse_details.name) {
								frappe.call({
									method: 'erpnext.stock.doctype.batch.batch.get_batch_qty',
									args: {
										batch_no: this.doc.batch_no,
										warehouse: me.warehouse_details.name,
										item_code: me.item_code
									},
									callback: (r) => {
										this.grid_row.on_grid_fields_dict
											.available_qty.set_value(r.message || 0);
									}
								});

							} else {
								this.set_value("");
								frappe.throw(__(`Please select a warehouse to get available
									quantities`));
							}
							// e.stopImmediatePropagation();
						}
					},
					{
						fieldtype:'Float',
						read_only:1,
						fieldname:'available_qty',
						label: __('Available'),
						in_list_view:1,
						default: 0,
						onchange: function() {
							this.grid_row.on_grid_fields_dict.selected_qty.set_value('0');
						}
					},
					{
						fieldtype:'Float',
						fieldname:'selected_qty',
						label: __('Qty'),
						in_list_view:1,
						'default': 0,
						onchange: function(e) {
							var batch_no = this.grid_row.on_grid_fields_dict.batch_no.get_value();
							var available_qty = this.grid_row.on_grid_fields_dict.available_qty.get_value();
							var selected_qty = this.grid_row.on_grid_fields_dict.selected_qty.get_value();

							if(batch_no.length === 0 && parseInt(selected_qty)!==0) {
								frappe.throw(__("Please select a batch"));
							}
							if(me.warehouse_details.type === 'Source Warehouse' &&
								parseFloat(available_qty) < parseFloat(selected_qty)) {

								this.set_value('0');
								frappe.throw(__(`For transfer from source, selected quantity cannot be
									greater than available quantity`));
							} else {
								this.grid.refresh();
							}

							me.update_total_qty();
						}
					},
				],
				in_place_edit: true,
				data: this.data,
				get_data: function() {
					return this.data;
				},
			}
		];
	},

	get_serial_no_fields: function() {
		var me = this;
		this.serial_list = [];
		return [
			{fieldtype: 'Section Break', label: __('Serial No')},
			{
				fieldtype: 'Link', fieldname: 'serial_no_select', options: 'Serial No',
				label: __('Select'),
				get_query: function() {
					return { filters: {item_code: me.item_code, warehouse: me.warehouse_details.name}};
				},
				onchange: function(e) {
					if(this.in_local_change) return;
					this.in_local_change = 1;

					let serial_no_list_field = this.layout.fields_dict.serial_no;
					let qty_field = this.layout.fields_dict.qty;

					let new_number = this.get_value();
					let list_value = serial_no_list_field.get_value();
					let new_line = '\n';
					if(!list_value) {
						new_line = '';
					} else {
						me.serial_list = list_value.replace(/\n/g, ' ').match(/\S+/g) || [];
					}

					if(!me.serial_list.includes(new_number)) {
						this.set_new_description('');
						serial_no_list_field.set_value(me.serial_list.join('\n') + new_line + new_number);
						me.serial_list = serial_no_list_field.get_value().replace(/\n/g, ' ').match(/\S+/g) || [];
					} else {
						this.set_new_description(new_number + ' is already selected.');
					}

					qty_field.set_input(me.serial_list.length);
					this.$input.val("");
					this.in_local_change = 0;
				}
			},
			{fieldtype: 'Column Break'},
			{
				fieldname: 'serial_no',
				fieldtype: 'Small Text',
				onchange: function() {
					me.serial_list = this.get_value()
						.replace(/\n/g, ' ').match(/\S+/g) || [];
					this.layout.fields_dict.qty.set_input(me.serial_list.length);
				}
			}
		];
	}
});
