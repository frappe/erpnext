erpnext.utils.BarcodeScanner = class BarcodeScanner {
	constructor(opts) {
		this.frm = opts.frm;

		// field from which to capture input of scanned data
		this.scan_field_name = opts.scan_field_name || "scan_barcode";
		this.scan_barcode_field = this.frm.fields_dict[this.scan_field_name];

		this.barcode_field = opts.barcode_field || "barcode";
		this.serial_no_field = opts.serial_no_field || "serial_no";
		this.batch_no_field = opts.batch_no_field || "batch_no";
		this.uom_field = opts.uom_field || "uom";
		this.qty_field = opts.qty_field || "qty";
		// field name on row which defines max quantity to be scanned e.g. picklist
		this.max_qty_field = opts.max_qty_field;
		// scanner won't add a new row if this flag is set.
		this.dont_allow_new_row = opts.dont_allow_new_row;
		// scanner will ask user to type the quantity instead of incrementing by 1
		this.prompt_qty = opts.prompt_qty;

		this.items_table_name = opts.items_table_name || "items";
		this.items_table = this.frm.doc[this.items_table_name];

		// optional sound name to play when scan either fails or passes.
		// see https://frappeframework.com/docs/v14/user/en/python-api/hooks#sounds
		this.success_sound = opts.play_success_sound;
		this.fail_sound = opts.play_fail_sound;

		// any API that takes `search_value` as input and returns dictionary as follows
		// {
		//     item_code: "HORSESHOE", // present if any item was found
		//     bar_code: "123456", // present if barcode was scanned
		//     batch_no: "LOT12", // present if batch was scanned
		//     serial_no: "987XYZ", // present if serial no was scanned
		//     uom: "Kg", // present if barcode UOM is different from default
		// }
		this.scan_api = opts.scan_api || "erpnext.stock.utils.scan_barcode";
	}

	process_scan() {
		return new Promise((resolve, reject) => {
			let me = this;

			const input = this.scan_barcode_field.value;
			this.scan_barcode_field.set_value("");
			if (!input) {
				return;
			}

			this.scan_api_call(input, (r) => {
				const data = r && r.message;
				if (!data || Object.keys(data).length === 0) {
					this.show_alert(__("Cannot find Item with this Barcode"), "red");
					this.clean_up();
					this.play_fail_sound();
					reject();
					return;
				}

				me.update_table(data).then(row => {
					this.play_success_sound();
					resolve(row);
				}).catch(() => {
					this.play_fail_sound();
					reject();
				});
			});
		});
	}

	scan_api_call(input, callback) {
		frappe
			.call({
				method: this.scan_api,
				args: {
					search_value: input,
				},
			})
			.then((r) => {
				callback(r);
			});
	}

	update_table(data) {
		return new Promise(resolve => {
			let cur_grid = this.frm.fields_dict[this.items_table_name].grid;

			const {item_code, barcode, batch_no, serial_no, uom} = data;

			let row = this.get_row_to_modify_on_scan(item_code, batch_no, uom, barcode);

			this.is_new_row = false;
			if (!row) {
				if (this.dont_allow_new_row) {
					this.show_alert(__("Maximum quantity scanned for item {0}.", [item_code]), "red");
					this.clean_up();
					reject();
					return;
				}
				this.is_new_row = true;

				// add new row if new item/batch is scanned
				row = frappe.model.add_child(this.frm.doc, cur_grid.doctype, this.items_table_name);
				// trigger any row add triggers defined on child table.
				this.frm.script_manager.trigger(`${this.items_table_name}_add`, row.doctype, row.name);
				this.frm.has_items = false;
			}

			if (this.is_duplicate_serial_no(row, serial_no)) {
				this.clean_up();
				reject();
				return;
			}

			frappe.run_serially([
				() => this.set_selector_trigger_flag(data),
				() => this.set_item(row, item_code, barcode, batch_no, serial_no).then(qty => {
					this.show_scan_message(row.idx, row.item_code, qty);
				}),
				() => this.set_barcode_uom(row, uom),
				() => this.set_serial_no(row, serial_no),
				() => this.set_batch_no(row, batch_no),
				() => this.set_barcode(row, barcode),
				() => this.clean_up(),
				() => this.revert_selector_flag(),
				() => resolve(row)
			]);
		});
	}

	// batch and serial selector is reduandant when all info can be added by scan
	// this flag on item row is used by transaction.js to avoid triggering selector
	set_selector_trigger_flag(data) {
		const {batch_no, serial_no, has_batch_no, has_serial_no} = data;

		const require_selecting_batch = has_batch_no && !batch_no;
		const require_selecting_serial = has_serial_no && !serial_no;

		if (!(require_selecting_batch || require_selecting_serial)) {
			frappe.flags.hide_serial_batch_dialog = true;
		}
	}

	revert_selector_flag() {
		frappe.flags.hide_serial_batch_dialog = false;
	}

	set_item(row, item_code, barcode, batch_no, serial_no) {
		return new Promise(resolve => {
			const increment = async (value = 1) => {
				const item_data = {item_code: item_code};
				item_data[this.qty_field] = Number((row[this.qty_field] || 0)) + Number(value);
				await frappe.model.set_value(row.doctype, row.name, item_data);
				return value;
			};

			if (this.prompt_qty) {
				frappe.prompt(__("Please enter quantity for item {0}", [item_code]), ({value}) => {
					increment(value).then((value) => resolve(value));
				});
			} else if (this.frm.has_items) {
				this.prepare_item_for_scan(row, item_code, barcode, batch_no, serial_no);
			} else {
				increment().then((value) => resolve(value));
			}
		});
	}

	prepare_item_for_scan(row, item_code, barcode, batch_no, serial_no) {
		var me = this;
		this.dialog = new frappe.ui.Dialog({
			title: __("Scan barcode for item {0}", [item_code]),
			fields: me.get_fields_for_dialog(row, item_code, barcode, batch_no, serial_no),
		})

		this.dialog.set_primary_action(__("Update"), () => {
			const item_data = {item_code: item_code};
			item_data[this.qty_field] = this.dialog.get_value("scanned_qty");
			item_data["has_item_scanned"] = 1;

			this.remaining_qty = flt(this.dialog.get_value("qty")) - flt(this.dialog.get_value("scanned_qty"));
			frappe.model.set_value(row.doctype, row.name, item_data);

			frappe.run_serially([
				() => this.set_batch_no(row, this.dialog.get_value("batch_no")),
				() => this.set_barcode(row, this.dialog.get_value("barcode")),
				() => this.set_serial_no(row, this.dialog.get_value("serial_no")),
				() => this.add_child_for_remaining_qty(row),
				() => this.clean_up()
			]);

			this.dialog.hide();
		});

		this.dialog.show();

		this.$scan_btn = this.dialog.$wrapper.find(".link-btn");
		this.$scan_btn.css("display", "inline");
	}

	get_fields_for_dialog(row, item_code, barcode, batch_no, serial_no) {
		let fields = [
			{
				fieldtype: "Data",
				fieldname: "barcode_scanner",
				options: "Barcode",
				label: __("Scan Barcode"),
				onchange: (e) => {
					if (!e) {
						return;
					}

					if (e.target.value) {
						this.scan_api_call(e.target.value, (r) => {
							if (r.message) {
								this.update_dialog_values(item_code, r);
							}
						})
					}
				}
			},
			{
				fieldtype: "Section Break",
			},
			{
				fieldtype: "Float",
				fieldname: "qty",
				label: __("Quantity to Scan"),
				default: row[this.qty_field] || 1,
			},
			{
				fieldtype: "Column Break",
				fieldname: "column_break_1",
			},
			{
				fieldtype: "Float",
				read_only: 1,
				fieldname: "scanned_qty",
				label: __("Scanned Quantity"),
				default: 1,
			},
			{
				fieldtype: "Section Break",
			}
		]

		if (batch_no) {
			fields.push({
				fieldtype: "Link",
				fieldname: "batch_no",
				options: "Batch No",
				label: __("Batch No"),
				default: batch_no,
				read_only: 1,
				hidden: 1
			});
		}

		if (serial_no) {
			fields.push({
				fieldtype: "Small Text",
				fieldname: "serial_no",
				label: __("Serial Nos"),
				default: serial_no,
				read_only: 1,
			});
		}

		if (barcode) {
			fields.push({
				fieldtype: "Data",
				fieldname: "barcode",
				options: "Barcode",
				label: __("Barcode"),
				default: barcode,
				read_only: 1,
				hidden: 1
			});
		}

		return fields;
	}

	update_dialog_values(scanned_item, r) {
		const {item_code, barcode, batch_no, serial_no} = r.message;

		this.dialog.set_value("barcode_scanner", "");
		if (item_code === scanned_item &&
			(this.dialog.get_value("barcode") === barcode || batch_no || serial_no)) {

			if (batch_no) {
				this.dialog.set_value("batch_no", batch_no);
			}

			if (serial_no) {

				this.validate_duplicate_serial_no(serial_no);
				let serial_nos = this.dialog.get_value("serial_no") + "\n" + serial_no;
				this.dialog.set_value("serial_no", serial_nos);
			}

			let qty = flt(this.dialog.get_value("scanned_qty")) + 1.0;
			this.dialog.set_value("scanned_qty", qty);
		}
	}

	validate_duplicate_serial_no(serial_no) {
		let serial_nos = this.dialog.get_value("serial_no") ?
			this.dialog.get_value("serial_no").split("\n") : [];

		if (in_list(serial_nos, serial_no)) {
			frappe.throw(__("Serial No {0} already scanned", [serial_no]));
		}
	}

	add_child_for_remaining_qty(prev_row) {
		if (this.remaining_qty && this.remaining_qty >0) {
			let cur_grid = this.frm.fields_dict[this.items_table_name].grid;
			let row = frappe.model.add_child(this.frm.doc, cur_grid.doctype, this.items_table_name);

			let ignore_fields = ["name", "idx", "batch_no", "barcode",
				"received_qty", "serial_no", "has_item_scanned"];

			for (let key in prev_row) {
				if (in_list(ignore_fields, key)) {
					continue;
				}

				row[key] = prev_row[key];
			}

			row[this.qty_field] = this.remaining_qty;
			if (this.qty_field == "qty" && frappe.meta.has_field(row.doctype, "stock_qty")) {
				row["stock_qty"] = this.remaining_qty * row.conversion_factor;
			}

			this.frm.script_manager.trigger("item_code", row.doctype, row.name);
		}
	}

	async set_serial_no(row, serial_no) {
		if (serial_no && frappe.meta.has_field(row.doctype, this.serial_no_field)) {
			const existing_serial_nos = row[this.serial_no_field];
			let new_serial_nos = "";

			if (!!existing_serial_nos) {
				new_serial_nos = existing_serial_nos + "\n" + serial_no;
			} else {
				new_serial_nos = serial_no;
			}
			await frappe.model.set_value(row.doctype, row.name, this.serial_no_field, new_serial_nos);
		}
	}

	async set_barcode_uom(row, uom) {
		if (uom && frappe.meta.has_field(row.doctype, this.uom_field)) {
			await frappe.model.set_value(row.doctype, row.name, this.uom_field, uom);
		}
	}

	async set_batch_no(row, batch_no) {
		if (batch_no && frappe.meta.has_field(row.doctype, this.batch_no_field)) {
			await frappe.model.set_value(row.doctype, row.name, this.batch_no_field, batch_no);
		}
	}

	async set_barcode(row, barcode) {
		if (barcode && frappe.meta.has_field(row.doctype, this.barcode_field)) {
			await frappe.model.set_value(row.doctype, row.name, this.barcode_field, barcode);
		}
	}

	show_scan_message(idx, exist = null, qty = 1) {
		// show new row or qty increase toast
		if (exist) {
			this.show_alert(__("Row #{0}: Qty increased by {1}", [idx, qty]), "green");
		} else {
			this.show_alert(__("Row #{0}: Item added", [idx]), "green")
		}
	}

	is_duplicate_serial_no(row, serial_no) {
		const is_duplicate = row[this.serial_no_field]?.includes(serial_no);

		if (is_duplicate) {
			this.show_alert(__("Serial No {0} is already added", [serial_no]), "orange");
		}
		return is_duplicate;
	}

	get_row_to_modify_on_scan(item_code, batch_no, uom, barcode) {
		let cur_grid = this.frm.fields_dict[this.items_table_name].grid;

		// Check if batch is scanned and table has batch no field
		let is_batch_no_scan = batch_no && frappe.meta.has_field(cur_grid.doctype, this.batch_no_field);
		let check_max_qty = this.max_qty_field && frappe.meta.has_field(cur_grid.doctype, this.max_qty_field);

		const matching_row = (row) => {
			const item_match = row.item_code == item_code;
			const batch_match = (!row[this.batch_no_field] || row[this.batch_no_field] == batch_no);
			const uom_match = !uom || row[this.uom_field] == uom;
			const qty_in_limit = flt(row[this.qty_field]) < flt(row[this.max_qty_field]);
			const item_scanned = row.has_item_scanned;

			return item_match
				&& uom_match
				&& !item_scanned
				&& (!is_batch_no_scan || batch_match)
				&& (!check_max_qty || qty_in_limit)
		}

		return this.items_table.find(matching_row) || this.get_existing_blank_row();
	}

	get_existing_blank_row() {
		return this.items_table.find((d) => !d.item_code);
	}

	play_success_sound() {
		this.success_sound && frappe.utils.play_sound(this.success_sound);
	}

	play_fail_sound() {
		this.fail_sound && frappe.utils.play_sound(this.fail_sound);
	}

	clean_up() {
		this.scan_barcode_field.set_value("");
		refresh_field(this.items_table_name);
	}
	show_alert(msg, indicator, duration=3) {
		frappe.show_alert({message: msg, indicator: indicator}, duration);
	}
};
