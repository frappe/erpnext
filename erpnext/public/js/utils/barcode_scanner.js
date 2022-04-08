erpnext.utils.BarcodeScanner = class BarcodeScanner {
	constructor(opts) {
		this.frm = opts.frm;

		// field from which to capture input of scanned data
		this.scan_field_name = opts.scan_field_name || "scan_barcode";
		this.scan_barcode_field = this.frm.fields_dict[this.scan_field_name];

		this.barcode_field = opts.barcode_field || "barcode";
		this.serial_no_field = opts.serial_no_field || "serial_no";
		this.batch_no_field = opts.batch_no_field || "batch_no";
		this.qty_field = opts.qty_field || "qty";

		this.items_table_name = opts.items_table_name || "items";
		this.items_table = this.frm.doc[this.items_table_name];

		// any API that takes `search_value` as input and returns dictionary as follows
		// {
		//     item_code: "HORSESHOE", // present if any item was found
		//     bar_code: "123456", // present if barcode was scanned
		//     batch_no: "LOT12", // present if batch was scanned
		//     serial_no: "987XYZ", // present if serial no was scanned
		// }
		this.scan_api = opts.scan_api || "erpnext.stock.utils.scan_barcode";
	}

	process_scan() {
		let me = this;

		const input = this.scan_barcode_field.value;
		if (!input) {
			return;
		}

		frappe
			.call({
				method: this.scan_api,
				args: {
					search_value: input,
				},
			})
			.then((r) => {
				const data = r && r.message;
				if (!data || Object.keys(data).length === 0) {
					frappe.show_alert({
						message: __("Cannot find Item with this Barcode"),
						indicator: "red",
					});
					this.clean_up();
					return;
				}

				me.update_table(data);
			});
	}

	update_table(data) {
		let cur_grid = this.frm.fields_dict[this.items_table_name].grid;
		let row = null;

		const {item_code, barcode, batch_no, serial_no} = data;

		// Check if batch is scanned and table has batch no field
		let batch_no_scan =
			Boolean(batch_no) && frappe.meta.has_field(cur_grid.doctype, this.batch_no_field);

		if (batch_no_scan) {
			row = this.get_batch_row_to_modify(batch_no);
		} else {
			// serial or barcode scan
			row = this.get_row_to_modify_on_scan(item_code);
		}

		if (!row) {
			// add new row if new item/batch is scanned
			row = frappe.model.add_child(this.frm.doc, cur_grid.doctype, this.items_table_name);
			// trigger any row add triggers defined on child table.
			this.frm.script_manager.trigger(`${this.items_table_name}_add`, row.doctype, row.name);
		}

		if (this.is_duplicate_serial_no(row, serial_no)) {
			this.clean_up();
			return;
		}

		this.show_scan_message(row.idx, row.item_code);
		this.set_selector_trigger_flag(row, data);
		this.set_item(row, item_code);
		this.set_serial_no(row, serial_no);
		this.set_batch_no(row, batch_no);
		this.set_barcode(row, barcode);
		this.clean_up();
	}

	// batch and serial selector is reduandant when all info can be added by scan
	// this flag on item row is used by transaction.js to avoid triggering selector
	set_selector_trigger_flag(row, data) {
		const {batch_no, serial_no, has_batch_no, has_serial_no} = data;

		const require_selecting_batch = has_batch_no && !batch_no;
		const require_selecting_serial = has_serial_no && !serial_no;

		if (!(require_selecting_batch || require_selecting_serial)) {
			row.__disable_batch_serial_selector = true;
		}
	}

	set_item(row, item_code) {
		const item_data = { item_code: item_code };
		item_data[this.qty_field] = (row[this.qty_field] || 0) + 1;
		frappe.model.set_value(row.doctype, row.name, item_data);
	}

	set_serial_no(row, serial_no) {
		if (serial_no && frappe.meta.has_field(row.doctype, this.serial_no_field)) {
			const existing_serial_nos = row[this.serial_no_field];
			let new_serial_nos = "";

			if (!!existing_serial_nos) {
				new_serial_nos = existing_serial_nos + "\n" + serial_no;
			} else {
				new_serial_nos = serial_no;
			}
			frappe.model.set_value(row.doctype, row.name, this.serial_no_field, new_serial_nos);
		}
	}

	set_batch_no(row, batch_no) {
		if (batch_no && frappe.meta.has_field(row.doctype, this.batch_no_field)) {
			frappe.model.set_value(row.doctype, row.name, this.batch_no_field, batch_no);
		}
	}

	set_barcode(row, barcode) {
		if (barcode && frappe.meta.has_field(row.doctype, this.barcode_field)) {
			frappe.model.set_value(row.doctype, row.name, this.barcode_field, barcode);
		}
	}

	show_scan_message(idx, exist = null) {
		// show new row or qty increase toast
		if (exist) {
			frappe.show_alert(
				{
					message: __("Row #{0}: Qty increased by 1", [idx]),
					indicator: "green",
				},
				5
			);
		} else {
			frappe.show_alert(
				{
					message: __("Row #{0}: Item added", [idx]),
					indicator: "green",
				},
				5
			);
		}
	}

	is_duplicate_serial_no(row, serial_no) {
		const is_duplicate = !!serial_no && !!row[this.serial_no_field]
			&& row[this.serial_no_field].includes(serial_no);

		if (is_duplicate) {
			frappe.show_alert(
				{
					message: __("Serial No {0} is already added", [serial_no]),
					indicator: "orange",
				},
				5
			);
		}
		return is_duplicate;
	}

	get_batch_row_to_modify(batch_no) {
		// get row if batch already exists in table
		const existing_batch_row = this.items_table.find((d) => d.batch_no === batch_no);
		return existing_batch_row || this.get_existing_blank_row();
	}

	get_row_to_modify_on_scan(item_code) {
		// get an existing item row to increment or blank row to modify
		const existing_item_row = this.items_table.find((d) => d.item_code === item_code);
		return existing_item_row || this.get_existing_blank_row();
	}

	get_existing_blank_row() {
		return this.items_table.find((d) => !d.item_code);
	}

	clean_up() {
		this.scan_barcode_field.set_value("");
		refresh_field(this.items_table_name);
	}
};
