<<<<<<< HEAD
=======
erpnext.SerialBatchPackageSelector = class SerialNoBatchBundleUpdate {
	constructor(frm, item, callback) {
		this.frm = frm;
		this.item = item;
		this.qty = item.qty;
		this.callback = callback;
		this.bundle = this.item?.is_rejected
			? this.item.rejected_serial_and_batch_bundle
			: this.item.serial_and_batch_bundle;
>>>>>>> ec74a5e566 (style: format js files)

erpnext.SerialNoBatchSelector = class SerialNoBatchSelector {
	constructor(opts, show_dialog) {
		$.extend(this, opts);
		this.show_dialog = show_dialog;
		// frm, item, warehouse_details, has_batch, oldest
		let d = this.item;
		this.has_batch = 0; this.has_serial_no = 0;

		if (d && d.has_batch_no && (!d.batch_no || this.show_dialog)) this.has_batch = 1;
		// !(this.show_dialog == false) ensures that show_dialog is implictly true, even when undefined
		if(d && d.has_serial_no && !(this.show_dialog == false)) this.has_serial_no = 1;

		this.setup();
	}

<<<<<<< HEAD
	setup() {
		this.item_code = this.item.item_code;
		this.qty = this.item.qty;
		this.make_dialog();
		this.on_close_dialog();
	}

	make_dialog() {
		var me = this;
=======
	make() {
		let label = this.item?.has_serial_no ? __("Serial Nos") : __("Batch Nos");
		let primary_label = this.bundle ? __("Update") : __("Add");

		if (this.item?.has_serial_no && this.item?.batch_no) {
			label = __("Serial Nos / Batch Nos");
		}

		primary_label += " " + label;

		this.dialog = new frappe.ui.Dialog({
			title: this.item?.title || primary_label,
			fields: this.get_dialog_fields(),
			primary_action_label: primary_label,
			primary_action: () => this.update_bundle_entries(),
			secondary_action_label: __("Edit Full Form"),
			secondary_action: () => this.edit_full_form(),
		});

		this.dialog.show();
		this.$scan_btn = this.dialog.$wrapper.find(".link-btn");
		this.$scan_btn.css("display", "inline");

		let qty = this.item.stock_qty || this.item.transfer_qty || this.item.qty;

		if (this.item?.is_rejected) {
			qty = this.item.rejected_qty;
		}

		qty = Math.abs(qty);
		if (qty > 0) {
			this.dialog.set_value("qty", qty).then(() => {
				if (this.item.serial_no && !this.item.serial_and_batch_bundle) {
					let serial_nos = this.item.serial_no.split("\n");
					if (serial_nos.length > 1) {
						serial_nos.forEach((serial_no) => {
							this.dialog.fields_dict.entries.df.data.push({
								serial_no: serial_no,
								batch_no: this.item.batch_no,
							});
						});
					} else {
						this.dialog.set_value("scan_serial_no", this.item.serial_no);
					}
					frappe.model.set_value(this.item.doctype, this.item.name, "serial_no", "");
				} else if (this.item.batch_no && !this.item.serial_and_batch_bundle) {
					this.dialog.set_value("scan_batch_no", this.item.batch_no);
					frappe.model.set_value(this.item.doctype, this.item.name, "batch_no", "");
				}

				this.dialog.fields_dict.entries.grid.refresh();
			});
		}
	}

	get_serial_no_filters() {
		let warehouse =
			this.item?.type_of_transaction === "Outward" ? this.item.warehouse || this.item.s_warehouse : "";

		if (this.frm.doc.doctype === "Stock Entry") {
			warehouse = this.item.s_warehouse || this.item.t_warehouse;
		}

		if (!warehouse && this.frm.doc.doctype === "Stock Reconciliation") {
			warehouse = this.get_warehouse();
		}

		return {
			item_code: this.item.item_code,
			warehouse: ["=", warehouse],
		};
	}

	get_dialog_fields() {
		let fields = [];

		fields.push({
			fieldtype: "Link",
			fieldname: "warehouse",
			label: __("Warehouse"),
			options: "Warehouse",
			default: this.get_warehouse(),
			onchange: () => {
				this.item.warehouse = this.dialog.get_value("warehouse");
				this.get_auto_data();
			},
			get_query: () => {
				return {
					filters: {
						is_group: 0,
						company: this.frm.doc.company,
					},
				};
			},
		});

		if (this.frm.doc.doctype === "Stock Entry" && this.frm.doc.purpose === "Manufacture") {
			fields.push({
				fieldtype: "Column Break",
			});

			fields.push({
				fieldtype: "Link",
				fieldname: "work_order",
				label: __("For Work Order"),
				options: "Work Order",
				read_only: 1,
				default: this.frm.doc.work_order,
			});

			fields.push({
				fieldtype: "Section Break",
			});
		}

		fields.push({
			fieldtype: "Column Break",
		});

		if (this.item.has_serial_no) {
			fields.push({
				fieldtype: "Data",
				options: "Barcode",
				fieldname: "scan_serial_no",
				label: __("Scan Serial No"),
				get_query: () => {
					return {
						filters: this.get_serial_no_filters(),
					};
				},
				onchange: () => this.scan_barcode_data(),
			});
		}

		if (this.item.has_batch_no && !this.item.has_serial_no) {
			fields.push({
				fieldtype: "Data",
				options: "Barcode",
				fieldname: "scan_batch_no",
				label: __("Scan Batch No"),
				onchange: () => this.scan_barcode_data(),
			});
		}

		if (this.item?.type_of_transaction === "Outward") {
			fields = [...this.get_filter_fields(), ...fields];
		} else {
			fields = [...fields, ...this.get_attach_field()];
		}

		fields.push({
			fieldtype: "Section Break",
		});

		fields.push({
			fieldname: "entries",
			fieldtype: "Table",
			allow_bulk_edit: true,
			data: [],
			fields: this.get_dialog_table_fields(),
		});

		return fields;
	}

	get_attach_field() {
		let label = this.item?.has_serial_no ? __("Serial Nos") : __("Batch Nos");
		let primary_label = this.bundle ? __("Update") : __("Add");

		if (this.item?.has_serial_no && this.item?.has_batch_no) {
			label = __("Serial Nos / Batch Nos");
		}
>>>>>>> ec74a5e566 (style: format js files)

		this.data = this.oldest ? this.oldest : [];
		let title = "";
		let fields = [
			{
<<<<<<< HEAD
				fieldname: 'item_code',
				read_only: 1,
				fieldtype:'Link',
				options: 'Item',
				label: __('Item Code'),
				default: me.item_code
			},
			{
				fieldname: 'warehouse',
				fieldtype:'Link',
				options: 'Warehouse',
				reqd: me.has_batch && !me.has_serial_no ? 0 : 1,
				label: __(me.warehouse_details.type),
				default: typeof me.warehouse_details.name == "string" ? me.warehouse_details.name : '',
				onchange: function(e) {
					me.warehouse_details.name = this.get_value();

					if(me.has_batch && !me.has_serial_no) {
						fields = fields.concat(me.get_batch_fields());
					} else {
						fields = fields.concat(me.get_serial_no_fields());
					}

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
				read_only: me.has_batch && !me.has_serial_no,
				label: __(me.has_batch && !me.has_serial_no ? 'Selected Qty' : 'Qty'),
				default: flt(me.item.stock_qty) || flt(me.item.transfer_qty),
			},
			...get_pending_qty_fields(me),
			{
				fieldname: 'uom',
				read_only: 1,
				fieldtype: 'Link',
				options: 'UOM',
				label: __('UOM'),
				default: me.item.uom
			},
			{
				fieldname: 'auto_fetch_button',
				fieldtype:'Button',
				hidden: me.has_batch && !me.has_serial_no,
				label: __('Auto Fetch'),
				description: __('Fetch Serial Numbers based on FIFO'),
				click: () => {
					let qty = this.dialog.fields_dict.qty.get_value();
					let already_selected_serial_nos = get_selected_serial_nos(me);
					let numbers = frappe.call({
						method: "erpnext.stock.doctype.serial_no.serial_no.auto_fetch_serial_number",
						args: {
							qty: qty,
							item_code: me.item_code,
							warehouse: typeof me.warehouse_details.name == "string" ? me.warehouse_details.name : '',
							batch_nos: me.item.batch_no || null,
							posting_date: me.frm.doc.posting_date || me.frm.doc.transaction_date,
							exclude_sr_nos: already_selected_serial_nos
						}
					});

					numbers.then((data) => {
						let auto_fetched_serial_numbers = data.message;
						let records_length = auto_fetched_serial_numbers.length;
						if (!records_length) {
							const warehouse = me.dialog.fields_dict.warehouse.get_value().bold();
							frappe.msgprint(
								__('Serial numbers unavailable for Item {0} under warehouse {1}. Please try changing warehouse.', [me.item.item_code.bold(), warehouse])
							);
						}
						if (records_length < qty) {
							frappe.msgprint(__('Fetched only {0} available serial numbers.', [records_length]));
						}
						let serial_no_list_field = this.dialog.fields_dict.serial_no;
						numbers = auto_fetched_serial_numbers.join('\n');
						serial_no_list_field.set_value(numbers);
					});
				}
			}
		];

		if (this.has_batch && !this.has_serial_no) {
			title = __("Select Batch Numbers");
			fields = fields.concat(this.get_batch_fields());
		} else {
			// if only serial no OR
			// if both batch_no & serial_no then only select serial_no and auto set batches nos
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
				frappe.run_serially([
					() => me.update_batch_items(),
					() => me.update_serial_no_item(),
					() => me.update_batch_serial_no_items(),
					() => {
						refresh_field("items");
						refresh_field("packed_items");
						if (me.callback) {
							return me.callback(me.item);
						}
					},
					() => me.dialog.hide()
				])
			}
=======
				fieldtype: "Section Break",
				label: __("{0} {1} via CSV File", [primary_label, label]),
			},
		];

		if (this.item?.has_serial_no) {
			fields = [
				...fields,
				{
					fieldtype: "Check",
					label: __("Import Using CSV file"),
					fieldname: "import_using_csv_file",
					default: 0,
				},
				{
					fieldtype: "Section Break",
					label: __("{0} {1} Manually", [primary_label, label]),
					depends_on: "eval:doc.import_using_csv_file === 0",
				},
				{
					fieldtype: "Small Text",
					label: __("Enter Serial Nos"),
					fieldname: "upload_serial_nos",
					depends_on: "eval:doc.import_using_csv_file === 0",
					description: __("Enter each serial no in a new line"),
				},
				{
					fieldtype: "Column Break",
					depends_on: "eval:doc.import_using_csv_file === 0",
				},
				{
					fieldtype: "Button",
					fieldname: "make_serial_nos",
					label: __("Create Serial Nos"),
					depends_on: "eval:doc.import_using_csv_file === 0",
					click: () => {
						this.create_serial_nos();
					},
				},
				{
					fieldtype: "Section Break",
					depends_on: "eval:doc.import_using_csv_file === 1",
				},
			];
		}

		fields = [
			...fields,
			{
				fieldtype: "Button",
				fieldname: "download_csv",
				label: __("Download CSV Template"),
				click: () => this.download_csv_file(),
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Attach",
				fieldname: "attach_serial_batch_csv",
				label: __("Attach CSV File"),
				onchange: () => this.upload_csv_file(),
			},
		];

		return fields;
	}

	create_serial_nos() {
		let { upload_serial_nos } = this.dialog.get_values();

		if (!upload_serial_nos) {
			frappe.throw(__("Please enter Serial Nos"));
		}

		frappe.call({
			method: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.create_serial_nos",
			args: {
				item_code: this.item.item_code,
				serial_nos: upload_serial_nos,
			},
			callback: (r) => {
				if (r.message) {
					this.dialog.fields_dict.entries.df.data = [];
					this.set_data(r.message);
					this.update_bundle_entries();
				}
			},
>>>>>>> ec74a5e566 (style: format js files)
		});

		if(this.show_dialog) {
			let d = this.item;
			if (this.item.serial_no) {
				this.dialog.fields_dict.serial_no.set_value(this.item.serial_no);
			}

			if (this.has_batch && !this.has_serial_no && d.batch_no) {
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

		if (this.has_batch && !this.has_serial_no) {
			this.update_total_qty();
			this.update_pending_qtys();
		}

		this.dialog.show();
	}

	on_close_dialog() {
		this.dialog.get_close_btn().on('click', () => {
			this.on_close && this.on_close(this.item);
		});
	}

<<<<<<< HEAD
	validate() {
		let values = this.values;
		if(!values.warehouse) {
			frappe.throw(__("Please select a warehouse"));
			return false;
		}
		if(this.has_batch && !this.has_serial_no) {
			if(values.batches.length === 0 || !values.batches) {
				frappe.throw(__("Please select batches for batched item {0}", [values.item_code]));
			}
			values.batches.map((batch, i) => {
				if(!batch.selected_qty || batch.selected_qty === 0 ) {
					if (!this.show_dialog) {
						frappe.throw(__("Please select quantity on row {0}", [i+1]));
					}
				}
			});
			return true;

		} else {
			let serial_nos = values.serial_no || '';
			if (!serial_nos || !serial_nos.replace(/\s/g, '').length) {
				frappe.throw(__("Please enter serial numbers for serialized item {0}", [values.item_code]));
			}
			return true;
		}
=======
	download_csv_file() {
		let csvFileData = ["Serial No"];

		if (this.item.has_serial_no && this.item.has_batch_no) {
			csvFileData = ["Serial No", "Batch No", "Quantity"];
		} else if (this.item.has_batch_no) {
			csvFileData = ["Batch No", "Quantity"];
		}

		const method = `/api/method/erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.download_blank_csv_template?content=${encodeURIComponent(
			JSON.stringify(csvFileData)
		)}`;
		const w = window.open(frappe.urllib.get_full_url(method));
		if (!w) {
			frappe.msgprint(__("Please enable pop-ups"));
		}
	}

	upload_csv_file() {
		const file_path = this.dialog.get_value("attach_serial_batch_csv");

		frappe.call({
			method: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.upload_csv_file",
			args: {
				item_code: this.item.item_code,
				file_path: file_path,
			},
			callback: (r) => {
				if (r.message.serial_nos && r.message.serial_nos.length) {
					this.set_data(r.message.serial_nos);
				} else if (r.message.batch_nos && r.message.batch_nos.length) {
					this.set_data(r.message.batch_nos);
				}
			},
		});
>>>>>>> ec74a5e566 (style: format js files)
	}

	update_batch_items() {
		// clones an items if muliple batches are selected.
		if(this.has_batch && !this.has_serial_no) {
			this.values.batches.map((batch, i) => {
				let batch_no = batch.batch_no;
				let row = '';

				if (i !== 0 && !this.batch_exists(batch_no)) {
					row = this.frm.add_child("items", { ...this.item });
				} else {
					row = this.frm.doc.items.find(i => i.batch_no === batch_no);
				}

				if (!row) {
					row = this.item;
				}
				// this ensures that qty & batch no is set
				this.map_row_values(row, batch, 'batch_no',
					'selected_qty', this.values.warehouse);
			});
		}
	}

	update_serial_no_item() {
		// just updates serial no for the item
		if(this.has_serial_no && !this.has_batch) {
			this.map_row_values(this.item, this.values, 'serial_no', 'qty');
		}
	}

	update_batch_serial_no_items() {
		// if serial no selected is from different batches, adds new rows for each batch.
		if(this.has_batch && this.has_serial_no) {
			const selected_serial_nos = this.values.serial_no.split(/\n/g).filter(s => s);

			return frappe.db.get_list("Serial No", {
				filters: { 'name': ["in", selected_serial_nos]},
				fields: ["batch_no", "name"]
			}).then((data) => {
				// data = [{batch_no: 'batch-1', name: "SR-001"},
				// 	{batch_no: 'batch-2', name: "SR-003"}, {batch_no: 'batch-2', name: "SR-004"}]
				const batch_serial_map = data.reduce((acc, d) => {
					if (!acc[d['batch_no']]) acc[d['batch_no']] = [];
					acc[d['batch_no']].push(d['name'])
					return acc
				}, {})
				// batch_serial_map = { "batch-1": ['SR-001'], "batch-2": ["SR-003", "SR-004"]}
				Object.keys(batch_serial_map).map((batch_no, i) => {
					let row = '';
					const serial_no = batch_serial_map[batch_no];
					if (i == 0) {
						row = this.item;
						this.map_row_values(row, {qty: serial_no.length, batch_no: batch_no}, 'batch_no',
							'qty', this.values.warehouse);
					} else if (!this.batch_exists(batch_no)) {
						row = this.frm.add_child("items", { ...this.item });
						row.batch_no = batch_no;
					} else {
						row = this.frm.doc.items.find(i => i.batch_no === batch_no);
					}
					const values = {
						'qty': serial_no.length,
						'serial_no': serial_no.join('\n')
					}
					this.map_row_values(row, values, 'serial_no',
						'qty', this.values.warehouse);
				});
			})
		}
	}

	batch_exists(batch) {
		const batches = this.frm.doc.items.map(data => data.batch_no);
		return (batches && in_list(batches, batch)) ? true : false;
	}

	map_row_values(row, values, number, qty_field, warehouse) {
		row.qty = values[qty_field];
		row.transfer_qty = flt(values[qty_field]) * flt(row.conversion_factor);
		row[number] = values[number];
		if(this.warehouse_details.type === 'Source Warehouse') {
			row.s_warehouse = values.warehouse || warehouse;
		} else if(this.warehouse_details.type === 'Target Warehouse') {
			row.t_warehouse = values.warehouse || warehouse;
		} else {
			row.warehouse = values.warehouse || warehouse;
		}

		this.frm.dirty();
	}

	update_total_qty() {
		let qty_field = this.dialog.fields_dict.qty;
		let total_qty = 0;

		this.dialog.fields_dict.batches.df.data.forEach(data => {
			total_qty += flt(data.selected_qty);
		});

		qty_field.set_input(total_qty);
	}

	update_pending_qtys() {
		const pending_qty_field = this.dialog.fields_dict.pending_qty;
		const total_selected_qty_field = this.dialog.fields_dict.total_selected_qty;

		if (!pending_qty_field || !total_selected_qty_field) return;

		const me = this;
		const required_qty = this.dialog.fields_dict.required_qty.value;
		const selected_qty = this.dialog.fields_dict.qty.value;
		const total_selected_qty = selected_qty + calc_total_selected_qty(me);
		const pending_qty = required_qty - total_selected_qty;

		pending_qty_field.set_input(pending_qty);
		total_selected_qty_field.set_input(total_selected_qty);
	}

	get_batch_fields() {
		var me = this;

		return [
<<<<<<< HEAD
			{fieldtype:'Section Break', label: __('Batches')},
			{fieldname: 'batches', fieldtype: 'Table', label: __('Batch Entries'),
				fields: [
					{
						'fieldtype': 'Link',
						'read_only': 0,
						'fieldname': 'batch_no',
						'options': 'Batch',
						'label': __('Select Batch'),
						'in_list_view': 1,
						get_query: function () {
							return {
								filters: {
									item_code: me.item_code,
									warehouse: me.warehouse || typeof me.warehouse_details.name == "string" ? me.warehouse_details.name : ''
								},
								query: 'erpnext.controllers.queries.get_batch_no'
							};
						},
						change: function () {
							const batch_no = this.get_value();
							if (!batch_no) {
								this.grid_row.on_grid_fields_dict
									.available_qty.set_value(0);
								return;
							}
							let selected_batches = this.grid.grid_rows.map((row) => {
								if (row === this.grid_row) {
									return "";
								}

								if (row.on_grid_fields_dict.batch_no) {
									return row.on_grid_fields_dict.batch_no.get_value();
								}
=======
			{
				fieldtype: "Section Break",
				label: __("Auto Fetch"),
			},
			{
				fieldtype: "Float",
				fieldname: "qty",
				label: __("Qty to Fetch"),
				onchange: () => this.get_auto_data(),
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Select",
				options: ["FIFO", "LIFO", "Expiry"],
				default: "FIFO",
				fieldname: "based_on",
				label: __("Fetch Based On"),
				onchange: () => this.get_auto_data(),
			},
			{
				fieldtype: "Section Break",
			},
		];
	}

	get_dialog_table_fields() {
		let fields = [];

		if (this.item.has_serial_no) {
			fields.push({
				fieldtype: "Link",
				options: "Serial No",
				fieldname: "serial_no",
				label: __("Serial No"),
				in_list_view: 1,
				get_query: () => {
					return {
						filters: this.get_serial_no_filters(),
					};
				},
			});
		}

		let batch_fields = [];
		if (this.item.has_batch_no) {
			batch_fields = [
				{
					fieldtype: "Link",
					options: "Batch",
					fieldname: "batch_no",
					label: __("Batch No"),
					in_list_view: 1,
					get_query: () => {
						let is_inward = false;
						if (
							(["Purchase Receipt", "Purchase Invoice"].includes(this.frm.doc.doctype) &&
								!this.frm.doc.is_return) ||
							(this.frm.doc.doctype === "Stock Entry" &&
								this.frm.doc.purpose === "Material Receipt")
						) {
							is_inward = true;
						}

						return {
							query: "erpnext.controllers.queries.get_batch_no",
							filters: {
								item_code: this.item.item_code,
								warehouse:
									this.item.s_warehouse || this.item.t_warehouse || this.item.warehouse,
								is_inward: is_inward,
							},
						};
					},
				},
			];

			if (!this.item.has_serial_no) {
				batch_fields.push({
					fieldtype: "Float",
					fieldname: "qty",
					label: __("Quantity"),
					in_list_view: 1,
				});
			}
		}

		fields = [...fields, ...batch_fields];

		fields.push({
			fieldtype: "Data",
			fieldname: "name",
			label: __("Name"),
			hidden: 1,
		});

		return fields;
	}

	get_auto_data() {
		let { qty, based_on } = this.dialog.get_values();

		if (this.item.serial_and_batch_bundle || this.item.rejected_serial_and_batch_bundle) {
			if (qty === this.qty) {
				return;
			}
		}

		if (this.item.serial_no || this.item.batch_no) {
			return;
		}

		if (!based_on) {
			based_on = "FIFO";
		}

		if (qty) {
			frappe.call({
				method: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_auto_data",
				args: {
					item_code: this.item.item_code,
					warehouse: this.item.warehouse || this.item.s_warehouse,
					has_serial_no: this.item.has_serial_no,
					has_batch_no: this.item.has_batch_no,
					qty: qty,
					based_on: based_on,
				},
				callback: (r) => {
					if (r.message) {
						this.dialog.fields_dict.entries.df.data = r.message;
						this.dialog.fields_dict.entries.grid.refresh();
					}
				},
			});
		}
	}

	scan_barcode_data() {
		const { scan_serial_no, scan_batch_no } = this.dialog.get_values();

		if (scan_serial_no || scan_batch_no) {
			frappe.call({
				method: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.is_serial_batch_no_exists",
				args: {
					item_code: this.item.item_code,
					type_of_transaction: this.item.type_of_transaction,
					serial_no: scan_serial_no,
					batch_no: scan_batch_no,
				},
				callback: (r) => {
					this.update_serial_batch_no();
				},
			});
		}
	}

	update_serial_batch_no() {
		const { scan_serial_no, scan_batch_no } = this.dialog.get_values();

		if (scan_serial_no) {
			let existing_row = this.dialog.fields_dict.entries.df.data.filter((d) => {
				if (d.serial_no === scan_serial_no) {
					return d;
				}
			});

			if (existing_row?.length) {
				frappe.throw(__("Serial No {0} already exists", [scan_serial_no]));
			}

			if (!this.item.has_batch_no) {
				this.dialog.fields_dict.entries.df.data.push({
					serial_no: scan_serial_no,
				});

				this.dialog.fields_dict.scan_serial_no.set_value("");
			} else {
				frappe.call({
					method: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_batch_no_from_serial_no",
					args: {
						serial_no: scan_serial_no,
					},
					callback: (r) => {
						if (r.message) {
							this.dialog.fields_dict.entries.df.data.push({
								serial_no: scan_serial_no,
								batch_no: r.message,
>>>>>>> ec74a5e566 (style: format js files)
							});
							if (selected_batches.includes(batch_no)) {
								this.set_value("");
								frappe.throw(__('Batch {0} already selected.', [batch_no]));
							}

<<<<<<< HEAD
							if (me.warehouse_details.name) {
								frappe.call({
									method: 'erpnext.stock.doctype.batch.batch.get_batch_qty',
									args: {
										batch_no,
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
								frappe.throw(__('Please select a warehouse to get available quantities'));
							}
							// e.stopImmediatePropagation();
						}
					},
					{
						'fieldtype': 'Float',
						'read_only': 1,
						'fieldname': 'available_qty',
						'label': __('Available'),
						'in_list_view': 1,
						'default': 0,
						change: function () {
							this.grid_row.on_grid_fields_dict.selected_qty.set_value('0');
						}
					},
					{
						'fieldtype': 'Float',
						'read_only': 0,
						'fieldname': 'selected_qty',
						'label': __('Qty'),
						'in_list_view': 1,
						'default': 0,
						change: function () {
							var batch_no = this.grid_row.on_grid_fields_dict.batch_no.get_value();
							var available_qty = this.grid_row.on_grid_fields_dict.available_qty.get_value();
							var selected_qty = this.grid_row.on_grid_fields_dict.selected_qty.get_value();

							if (batch_no.length === 0 && parseInt(selected_qty) !== 0) {
								frappe.throw(__("Please select a batch"));
							}
							if (me.warehouse_details.type === 'Source Warehouse' &&
								parseFloat(available_qty) < parseFloat(selected_qty)) {

								this.set_value('0');
								frappe.throw(__('For transfer from source, selected quantity cannot be greater than available quantity'));
							} else {
								this.grid.refresh();
							}

							me.update_total_qty();
							me.update_pending_qtys();
						}
					},
				],
				in_place_edit: true,
				data: this.data,
				get_data: function () {
					return this.data;
				},
			}
		];
	}

	get_serial_no_fields() {
		var me = this;
		this.serial_list = [];

		let serial_no_filters = {
			item_code: me.item_code,
			delivery_document_no: ""
		}

		if (this.item.batch_no) {
			serial_no_filters["batch_no"] = this.item.batch_no;
		}

		if (me.warehouse_details.name) {
			serial_no_filters['warehouse'] = me.warehouse_details.name;
		}

		if (me.frm.doc.doctype === 'POS Invoice' && !this.showing_reserved_serial_nos_error) {
			frappe.call({
				method: "erpnext.stock.doctype.serial_no.serial_no.get_pos_reserved_serial_nos",
				args: {
					filters: {
						item_code: me.item_code,
						warehouse: typeof me.warehouse_details.name == "string" ? me.warehouse_details.name : '',
					}
				}
			}).then((data) => {
				serial_no_filters['name'] = ["not in", data.message[0]]
			})
=======
							this.dialog.fields_dict.scan_serial_no.set_value("");
						}
					},
				});
			}
		} else if (scan_batch_no) {
			let existing_row = this.dialog.fields_dict.entries.df.data.filter((d) => {
				if (d.batch_no === scan_batch_no) {
					return d;
				}
			});

			if (existing_row?.length) {
				existing_row[0].qty += 1;
			} else {
				this.dialog.fields_dict.entries.df.data.push({
					batch_no: scan_batch_no,
					qty: 1,
				});
			}

			this.dialog.fields_dict.scan_batch_no.set_value("");
		}

		this.dialog.fields_dict.entries.grid.refresh();
	}

	update_bundle_entries() {
		let entries = this.dialog.get_values().entries;
		let warehouse = this.dialog.get_value("warehouse");

		if ((entries && !entries.length) || !entries) {
			frappe.throw(__("Please add atleast one Serial No / Batch No"));
		}

		frappe
			.call({
				method: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.add_serial_batch_ledgers",
				args: {
					entries: entries,
					child_row: this.item,
					doc: this.frm.doc,
					warehouse: warehouse,
				},
			})
			.then((r) => {
				this.callback && this.callback(r.message);
				this.frm.save();
				this.dialog.hide();
			});
	}

	edit_full_form() {
		let bundle_id = this.item.serial_and_batch_bundle;
		if (!bundle_id) {
			let _new = frappe.model.get_new_doc("Serial and Batch Bundle", null, null, true);

			_new.item_code = this.item.item_code;
			_new.warehouse = this.get_warehouse();
			_new.has_serial_no = this.item.has_serial_no;
			_new.has_batch_no = this.item.has_batch_no;
			_new.type_of_transaction = this.item.type_of_transaction;
			_new.company = this.frm.doc.company;
			_new.voucher_type = this.frm.doc.doctype;
			bundle_id = _new.name;
		}

		frappe.set_route("Form", "Serial and Batch Bundle", bundle_id);
		this.dialog.hide();
	}

	get_warehouse() {
		return this.item?.type_of_transaction === "Outward"
			? this.item.warehouse || this.item.s_warehouse
			: this.item.warehouse || this.item.t_warehouse;
	}

	render_data() {
		if (this.bundle) {
			frappe
				.call({
					method: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_serial_batch_ledgers",
					args: {
						item_code: this.item.item_code,
						name: this.bundle,
						voucher_no: !this.frm.is_new() ? this.item.parent : "",
					},
				})
				.then((r) => {
					if (r.message) {
						this.set_data(r.message);
					}
				});
>>>>>>> ec74a5e566 (style: format js files)
		}

<<<<<<< HEAD
		return [
			{fieldtype: 'Section Break', label: __('Serial Numbers')},
			{
				fieldtype: 'Link', fieldname: 'serial_no_select', options: 'Serial No',
				label: __('Select to add Serial Number.'),
				get_query: function() {
					return {
						filters: serial_no_filters
					};
				},
				onchange: function(e) {
					if(this.in_local_change) return;
					this.in_local_change = 1;
=======
	set_data(data) {
		data.forEach((d) => {
			d.qty = Math.abs(d.qty);
			this.dialog.fields_dict.entries.df.data.push(d);
		});
>>>>>>> ec74a5e566 (style: format js files)

					let serial_no_list_field = this.layout.fields_dict.serial_no;
					let qty_field = this.layout.fields_dict.qty;

					let new_number = this.get_value();
					let list_value = serial_no_list_field.get_value();
					let new_line = '\n';
					if(!list_value) {
						new_line = '';
					} else {
						me.serial_list = list_value.split(/\n/g) || [];
					}

					if(!me.serial_list.includes(new_number)) {
						this.set_new_description('');
						serial_no_list_field.set_value(me.serial_list.join('\n') + new_line + new_number);
						me.serial_list = serial_no_list_field.get_value().split(/\n/g) || [];
					} else {
						this.set_new_description(new_number + ' is already selected.');
					}

					me.serial_list = me.serial_list.filter(serial => {
						if (serial) {
							return true;
						}
					});

					qty_field.set_input(me.serial_list.length);
					this.$input.val("");
					this.in_local_change = 0;
				}
			},
			{fieldtype: 'Section Break'},
			{
				fieldname: 'serial_no',
				fieldtype: 'Text',
				label: __(me.has_batch && !me.has_serial_no ? 'Selected Batch Numbers' : 'Selected Serial Numbers'),
				onchange: function() {
					me.serial_list = this.get_value().split(/\n/g);
					me.serial_list = me.serial_list.filter(serial => {
						if (serial) {
							return true;
						}
					});

					this.layout.fields_dict.qty.set_input(me.serial_list.length);
				}
			}
		];
	}
};
<<<<<<< HEAD

function get_pending_qty_fields(me) {
	if (!check_can_calculate_pending_qty(me)) return [];
	const { frm: { doc: { fg_completed_qty }}, item: { item_code, stock_qty }} = me;
	const { qty_consumed_per_unit } = erpnext.stock.bom.items[item_code];

	const total_selected_qty = calc_total_selected_qty(me);
	const required_qty = flt(fg_completed_qty) * flt(qty_consumed_per_unit);
	const pending_qty = required_qty - (flt(stock_qty) + total_selected_qty);

	const pending_qty_fields =  [
		{ fieldtype: 'Section Break', label: __('Pending Quantity') },
		{
			fieldname: 'required_qty',
			read_only: 1,
			fieldtype: 'Float',
			label: __('Required Qty'),
			default: required_qty
		},
		{ fieldtype: 'Column Break' },
		{
			fieldname: 'total_selected_qty',
			read_only: 1,
			fieldtype: 'Float',
			label: __('Total Selected Qty'),
			default: total_selected_qty
		},
		{ fieldtype: 'Column Break' },
		{
			fieldname: 'pending_qty',
			read_only: 1,
			fieldtype: 'Float',
			label: __('Pending Qty'),
			default: pending_qty
		},
	];
	return pending_qty_fields;
}

// get all items with same item code except row for which selector is open.
function get_rows_with_same_item_code(me) {
	const { frm: { doc: { items }}, item: { name, item_code }} = me;
	return items.filter(item => (item.name !== name) && (item.item_code === item_code))
}

function calc_total_selected_qty(me) {
	const totalSelectedQty = get_rows_with_same_item_code(me)
		.map(item => flt(item.qty))
		.reduce((i, j) => i + j, 0);
	return totalSelectedQty;
}

function get_selected_serial_nos(me) {
	const selected_serial_nos = get_rows_with_same_item_code(me)
		.map(item => item.serial_no)
		.filter(serial => serial)
		.map(sr_no_string => sr_no_string.split('\n'))
		.reduce((acc, arr) => acc.concat(arr), [])
		.filter(serial => serial);
	return selected_serial_nos;
};

function check_can_calculate_pending_qty(me) {
	const { frm: { doc }, item } = me;
	const docChecks = doc.bom_no
		&& doc.fg_completed_qty
		&& erpnext.stock.bom
		&& erpnext.stock.bom.name === doc.bom_no;
	const itemChecks = !!item
		&& !item.original_item
		&& erpnext.stock.bom && erpnext.stock.bom.items
		&& (item.item_code in erpnext.stock.bom.items);
	return docChecks && itemChecks;
}

//# sourceURL=serial_no_batch_selector.js
=======
>>>>>>> ec74a5e566 (style: format js files)
