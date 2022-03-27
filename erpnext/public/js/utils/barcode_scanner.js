erpnext.stock.BarcodeScanner = class BarcodeScanner {
	constructor(opts) {
		$.extend(this, opts);
	}

	process_scan() {
		let me = this;

		if(this.frm.doc.scan_barcode) {
			frappe.call({
				method: "erpnext.selling.page.point_of_sale.point_of_sale.search_for_serial_or_batch_or_barcode_number",
				args: {
					search_value: this.frm.doc.scan_barcode
				}
			}).then(r => {
				const data = r && r.message;
				if (!data || Object.keys(data).length === 0) {
					frappe.show_alert({
						message: __('Cannot find Item with this Barcode'),
						indicator: 'red'
					});
					return;
				}

				me.modify_table_after_scan(data);
			});
		}
	}


	modify_table_after_scan(data) {
		let scan_barcode_field = this.frm.fields_dict["scan_barcode"];
		let cur_grid = this.frm.fields_dict.items.grid;
		let row_to_modify = null;

		// Check if batch is scanned and table has batch no field
		let batch_no_scan = Boolean(data.batch_no) && frappe.meta.has_field(cur_grid.doctype, "batch_no");

		if (batch_no_scan) {
			row_to_modify = this.get_batch_row_to_modify(data.batch_no);
		} else {
			// serial or barcode scan
			row_to_modify = this.get_row_to_modify_on_scan(row_to_modify, data);
		}

		if (!row_to_modify) {
			// add new row if new item/batch is scanned
			row_to_modify = frappe.model.add_child(this.frm.doc, cur_grid.doctype, 'items');
			this.frm.script_manager.trigger("items_add", row_to_modify.doctype, row_to_modify.name);
		}

		if (this.is_duplicate_serial_no(row_to_modify, data.serial_no)) {
			scan_barcode_field.set_value("");
			return;
		};

		this.show_scan_message(row_to_modify.idx, row_to_modify.item_code);
		this.set_scanned_values(row_to_modify, data, scan_barcode_field);
	}

	set_scanned_values(row_to_modify, data, scan_barcode_field) {
		// increase qty and set scanned value and item in row
		this.frm.from_barcode = this.frm.from_barcode ? this.frm.from_barcode + 1 : 1;
		frappe.model.set_value(row_to_modify.doctype, row_to_modify.name, {
			item_code: data.item_code,
			qty: (row_to_modify.qty || 0) + 1
		});

		['serial_no', 'batch_no', 'barcode'].forEach(field => {
			if (data[field] && frappe.meta.has_field(row_to_modify.doctype, field)) {
				let is_serial_no = row_to_modify[field] && field === "serial_no";
				let value = data[field];

				if (is_serial_no) {
					value = row_to_modify[field] + '\n' + data[field];
				}

				frappe.model.set_value(row_to_modify.doctype, row_to_modify.name, field, value);
			}
		});

		scan_barcode_field.set_value('');
		refresh_field("items");
	}

	show_scan_message (idx, exist = null) {
		// show new row or qty increase toast
		if (exist) {
			frappe.show_alert({
				message: __('Row #{0}: Qty increased by 1', [idx]),
				indicator: 'green'
			}, 5);
		} else {
			frappe.show_alert({
				message: __('Row #{0}: Item added', [idx]),
				indicator: 'green'
			}, 5);
		}
	}

	is_duplicate_serial_no(row, serial_no) {
		const is_duplicate = !!serial_no && !!row.serial_no && row.serial_no.includes(serial_no);

		if (is_duplicate) {
			frappe.show_alert({
				message: __('Serial No {0} is already added', [serial_no]),
				indicator: 'orange'
			}, 5);
		}
		return is_duplicate;
	}


	get_batch_row_to_modify(batch_no) {
		// get row if batch already exists in table
		const existing_batch_row = this.frm.doc.items.find(d => d.batch_no === batch_no);
		return existing_batch_row || null;
	}

	get_row_to_modify_on_scan(row_to_modify, data) {
		// get an existing item row to increment or blank row to modify
		const existing_item_row = this.frm.doc.items.find(d => d.item_code === data.item_code);
		const blank_item_row = this.frm.doc.items.find(d => !d.item_code);

		if (existing_item_row) {
			row_to_modify = existing_item_row;
		} else if (blank_item_row) {
			row_to_modify = blank_item_row;
		}

		return row_to_modify;
	}
};
