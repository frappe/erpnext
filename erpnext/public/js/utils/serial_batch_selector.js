frappe.provide("erpnext.stock");

/**
	* Shows a Serial No and Batch selection Dialog Box.
	* @param  {Object} frm Current Form.
	* @param  {Object} item Line Item Row Doc Object.
	* @param  {String} [opts.warehouse_field="warehouse"] Warehouse field for Item Doc
	* @param  {Function} opts.callback Callback to run after submitting selection
	* @param  {Function} opts.on_close Callback to run after closing dialog
	* @param  {Function} opts.on_make_dialog Callback to run after creating dialog
*/
erpnext.stock.SerialBatchSelector = Class.extend({
	init: function(frm, item, opts) {
		if (!frm || !item) {
			return
		}

		opts = opts || {};
		$.extend(this, opts);

		this.frm = frm;
		this.item = item;

		this.has_batch_no = cint(item.has_batch_no || opts.has_batch_no);
		this.has_serial_no = cint(item.has_serial_no || opts.has_serial_no);

		if (!this.warehouse_field) {
			this.warehouse_field = "warehouse";
		}

		if (this.has_batch_no || this.has_serial_no) {
			this.setup();
		}
	},

	setup: function() {
		this.doc = {
			item_code: this.item.item_code,
			item_name: this.item.item_name,
			qty: flt(this.item.qty),
			warehouse: this.item[this.warehouse_field],
			batches: [],
			serial_no: this.has_serial_no ? this.item.serial_no : null,
		}

		frappe.call({
			method: "erpnext.stock.doctype.batch.batch.get_sufficient_batch_or_fifo",
			args: {
				qty: this.doc.qty,
				item_code: this.doc.item_code,
				warehouse: this.doc.warehouse,
				conversion_factor: this.item.conversion_factor,
				sales_order_item: this.item.sales_order_item,
			},
			callback: (r) => {
				if (r.message) {
					this.set_batch_nos(r.message, true);
				}
			}
		});

		let total_qty = 0;
		for (let d of this.frm.doc.items || []) {
			if (d.item_code == this.doc.item_code) {
				total_qty += flt(d.qty);

				if (d.batch_no) {
					this.doc.batches.push({
						'batch_no': d.batch_no,
						'actual_qty': d.actual_qty,
						'selected_qty': d.qty,
						'available_qty': d.actual_batch_qty
					});
				}
			}
		}

		this.make_dialog();
		this.update_total_qty(total_qty);
	},

	make_dialog: function() {
		let dialog_title = "Serial Batch Selector";
		let fields = this.get_fields();

		if (this.has_batch_no && this.has_serial_no) {
			dialog_title = __("Select Serial Numbers and Batches");
		} else if (this.has_batch_no) {
			dialog_title = __("Select Batches");
		} else if (this.has_serial_no) {
			dialog_title = __("Select Serial Numers");
		}

		this.dialog = new frappe.ui.Dialog({
			title: dialog_title,
			fields: fields,
			size: "large",
			doc: this.doc,
		});

		this.dialog.set_primary_action(__('Select'), () => {
			this.values = this.dialog.get_values();
			if(this.validate()) {
				this.update_items();
				this.dialog.hide();
			}
		});

		this.dialog.set_secondary_action_label(__("Close"));
		this.dialog.set_secondary_action(() => {
			this.on_close && this.on_close(this, this.item);
		});

		if (this.on_make_dialog) {
			this.on_make_dialog(this, this.item);
		}

		this.dialog.show();
	},

	get_fields: function () {
		let fields = [
			{
				fieldname: "item_code",
				fieldtype: "Link",
				options: "Item",
				label: __("Item Code"),
				reqd: 1,
				read_only: 1,
			},
			{fieldtype:'Column Break'},
			{
				fieldname: "warehouse",
				fieldtype: "Link",
				options: "Warehouse",
				label: __("Warehouse"),
				reqd: 1,
				onchange: () => {
					frappe.call({
						method: "erpnext.stock.doctype.batch.batch.get_sufficient_batch_or_fifo",
						args: {
							qty: this.doc.qty,
							item_code: this.doc.item_code,
							warehouse: this.doc.warehouse,
							conversion_factor: this.item.conversion_factor,
							sales_order_item: this.item.sales_order_item,
						},
						callback: (r) => {
							if (r.message) {
								this.set_batch_nos(r.message, true);
							}
						}
					});
				},
				get_query: () => {
					return {
						query: "erpnext.controllers.queries.warehouse_query",
						filters: [
							["Bin", "item_code", "=", this.doc.item_code],
							["Warehouse", "is_group", "=", 0],
							["Warehouse", "company", "=", this.frm.doc.company]
						]
					}
				}
			},
			{fieldtype:'Column Break'},
			{
				fieldname: "qty",
				fieldtype: "Float",
				read_only: 0,
				label: __(this.has_batch_no ? "Total Qty" : "Qty"),
			},
			{
				fieldname: "auto_fetch_button",
				fieldtype: "Button",
				hidden: 0,
				label: __('Fetch Based On FIFO'),
				click: () => {
					let qty = flt(this.doc.qty);

					if (this.has_batch_no) {
						frappe.call({
							method: "erpnext.stock.doctype.batch.batch.get_sufficient_batch_or_fifo",
							args: {
								qty: qty,
								item_code: this.doc.item_code,
								warehouse: this.doc.warehouse,
								conversion_factor: this.item.conversion_factor,
								sales_order_item: this.item.sales_order_item,
							},
							callback: (r) => {
								if (r.message) {
									this.set_batch_nos(r.message, true);
								}
							}
						});
					} else {
						frappe.call({
							method: "erpnext.stock.doctype.serial_no.serial_no.auto_fetch_serial_number",
							args: {
								qty: qty,
								item_code: this.doc.item_code,
								warehouse: this.doc.warehouse,
								batch_no: this.item.batch_no,
								sales_order_item: this.item.sales_order_item
							},
							callback: (r) => {
								if (!r.exc) {
									let serial_nos = r.message || [];
									let serial_no_count = serial_nos.length;
									if (serial_no_count < qty) {
										frappe.msgprint(__("Fetched only {0} serial numbers.", [serial_no_count]));
									}

									this.doc.serial_no = serial_nos.join('\n');
									this.dialog.fields_dict.serial_no.refresh();
								}
							}
						});
					}
				}
			}
		];

		if (this.has_serial_no) {
			fields = fields.concat(this.get_serial_no_fields());
		} else if (this.has_batch_no) {
			fields = fields.concat(this.get_batch_fields());
		}

		return fields;
	},

	get_batch_fields: function() {
		let me = this;

		return [
			{fieldtype:'Section Break', label: __('Batches')},
			{fieldname: 'batches', fieldtype: 'Table', label: __('Batch Nos'),
				fields: [
					{
						fieldname: "batch_no",
						fieldtype: "Link",
						options: "Batch",
						label: __("Select Batch"),
						reqd: 1,
						in_list_view: 1,
						get_query: () => {
							return {
								filters: {
									item_code: this.doc.item_code,
									warehouse: this.doc.warehouse,
								},
								query: "erpnext.controllers.queries.get_batch_no",
							};
						},
						change: function() {
							let control = this;
							let row = control.doc;

							if (!row.batch_no) {
								row.available_qty = 0;
								me.dialog.fields_dict.batches.refresh();
								return;
							}

							let already_selected_batches = me.doc.batches.filter(d => d != row).map(d => d.batch_no);
							if (already_selected_batches.includes(row.batch_no)) {
								control.set_value(null);
								frappe.throw(__("Batch No {0} already selected.", [row.batch_no]));
								return;
							}

							if (me.doc[me.warehouse_field]) {
								frappe.call({
									method: 'erpnext.stock.doctype.batch.batch.get_batch_qty',
									args: {
										batch_no: row.batch_no,
										warehouse: me.doc[me.warehouse_field],
										item_code: me.doc.item_code,
									},
									callback: (r) => {
										row.available_qty = flt(r.message) / (flt(me.item.conversion_factor) || 1);
										me.dialog.fields_dict.batches.refresh();
									}
								});
							} else {
								control.set_value(null);
								frappe.throw(__(`Please select Warehouse first to get available quantities`));
							}
						}
					},
					{
						fieldname: "available_qty",
						fieldtype: "Float",
						label: __('Available Qty'),
						read_only: 1,
						in_list_view: 1,
						default: 0
					},
					{
						fieldname: 'selected_qty',
						fieldtype: 'Float',
						label: __('Selected Qty'),
						in_list_view: 1,
						reqd: 1,
						default: 0,
						change: function() {
							let control = this;
							let row = control.doc;

							if (!row.batch_no && flt(row.selected_qty) != 0) {
								control.set_value(0);
								frappe.throw(__("Please select a Batch first"));
							}

							if (flt(row.selected_qty) > flt(row.available_qty)) {
								control.set_value(0);
								frappe.throw(__(`Selected Qty cannot be greater than Available Qty`));
							}

							me.update_total_qty();
						}
					},
				],
				in_place_edit: true,
				data: this.doc.batches,
				get_data: () => {
					return this.doc.batches;
				},
			}
		];
	},

	get_serial_no_fields: function() {
		let me = this;
		this.serial_list = [];

		return [
			{fieldtype: 'Section Break', label: __('Serial Numbers')},
			{
				fieldname: 'serial_no_select',
				fieldtype: 'Link',
				options: 'Serial No',
				label: __('Select to add Serial Number.'),
				get_query: () => {
					let serial_no_filters = {
						item_code: this.doc.item_code,
						delivery_document_no: ""
					}
					if (this.item.batch_no) {
						serial_no_filters["batch_no"] = this.item.batch_no;
					}
					if (this.doc.warehouse) {
						serial_no_filters['warehouse'] = this.doc.warehouse;
					}

					return {
						filters: serial_no_filters
					};
				},
				onchange: function() {
					let control = this;

					let new_line = '\n';
					if(!me.doc.serial_no) {
						new_line = '';
					} else {
						me.serial_list = me.doc.serial_no.replace(/\n/g, ' ').match(/\S+/g) || [];
					}

					if(!me.serial_list.includes(me.doc.serial_no_select)) {
						control.set_new_description('');

						me.doc.serial_no = me.serial_list.join('\n') + new_line + me.doc.serial_no_select;
						me.serial_list = me.doc.serial_no.replace(/\n/g, ' ').match(/\S+/g) || [];
					} else {
						control.set_new_description(me.doc.serial_no_select + ' is already selected.');
					}

					me.update_total_qty(me.serial_list.length);

					me.doc.serial_no_select = null;
					me.dialog.refresh();
				}
			},
			{fieldtype: 'Column Break'},
			{
				fieldname: 'serial_no',
				fieldtype: 'Long Text',
				label: __('Selected Serial Numbers'),
				onchange: function() {
					me.serial_list = me.doc.replace(/\n/g, ' ').match(/\S+/g) || [];
					me.update_total_qty(me.serial_list.length);
					me.dialog.refresh();
				}
			}
		];
	},

	validate: function() {
		if (!this.values.warehouse) {
			frappe.throw(__("Please select a warehouse"));
		}

		if (this.has_serial_no) {
			let serial_nos = this.values.serial_no || "";
			if (!serial_nos || !serial_nos.replace(/\s/g, '').length) {
				frappe.throw(__("Please enter Serial Numbers for Item {0}", [this.values.item_code]));
			}
			return true;
		} else if (this.has_batch_no) {
			if (!this.values.batches || this.values.batches.length === 0) {
				frappe.throw(__("Please select Batches for Item {0}", [this.values.item_code]));
			}

			for (let d of this.values.batches || []) {
				if (flt(d.available_qty) && flt(d.selected_qty) > flt(d.available_qty)) {
					frappe.throw(__("Selected Qty cannot be greater than Available Qty for Batch {0}", [d.batch_no]));
				}
			}
			return true;
		}
	},

	set_batch_nos: function(batches, update_qty) {
		batches = batches || [];

		this.doc.batches = batches;
		this.dialog.fields_dict.batches.grid.df.data = batches;

		$.each(this.doc.batches || [], function (i, row) {
			row.name = "row " + (i + 1);
			row.idx = i + 1;
		});

		if (update_qty) {
			this.update_total_qty();
		}
		this.dialog.refresh();
	},

	update_items: function() {
		if (this.has_serial_no) {
			this.map_row_values(this.item, this.values, 'serial_no', 'qty');
		} else if (this.has_batch_no) {
			let selected_batches = this.values.batches.filter(d => d.batch_no && d.selected_qty > 0);
			let selected_batch_nos = selected_batches.map(d => d.batch_no);

			let new_idx = this.item.idx + 1;

			$.each(selected_batches, (i, batch) => {
				let batch_no = batch.batch_no;
				let row = this.frm.doc.items.find(d => d.batch_no === batch_no);

				if (!row && !this.item.batch_no) {
					row = this.item;
					row.batch_no = batch_no;
				}

				if (!row) {
					row = frappe.model.copy_doc(this.item, true, this.frm.doc, 'items');
					row.batch_no = batch_no;

					this.frm.doc.items.pop();
					this.frm.doc.items.splice(new_idx-1, 0, row);

					$.each(this.frm.doc.items, function (i, d) {
						d.idx = i + 1;
					});
					new_idx += 1;
				}

				this.map_row_values(row, batch, 'batch_no', 'selected_qty', this.values.warehouse);
				row.actual_batch_qty = batch.available_qty;
			});

			refresh_field("items");
			for (let row of this.frm.doc.items) {
				if (row.item_code == this.doc.item_code && (!selected_batch_nos.includes(row.batch_no))) {
					this.frm.fields_dict.items.grid.grid_rows_by_docname[row.name]?.remove();
				}
			}
		}

		refresh_field("items");
		this.callback && this.callback(this.item);
	},

	map_row_values: function(row, values, serial_batch_field, qty_field, warehouse) {
		row.qty = values[qty_field];
		row.transfer_qty = flt(values[qty_field]) * flt(row.conversion_factor);
		row.stock_qty = flt(values[qty_field]) * flt(row.conversion_factor);
		row[serial_batch_field] = values[serial_batch_field];
		row[this.warehouse_field] = values.warehouse || warehouse;
	},

	update_total_qty: function(qty) {
		if (qty) {
			this.doc.qty = flt(qty);
		} else {
			let total_qty = 0;
			this.doc.batches.forEach(d => {
				total_qty += flt(d.selected_qty);
			});

			this.doc.qty = total_qty;
		}
		this.dialog.fields_dict.qty.refresh();
	},
});
