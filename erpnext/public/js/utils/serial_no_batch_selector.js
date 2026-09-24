erpnext.SerialBatchPackageSelector = class SerialNoBatchBundleUpdate {
	constructor(frm, item, callback) {
		this.frm = frm;
		this.item = item;
		this.qty = item.qty;
		this.callback = callback;
		this.serial_field = this.item.is_rejected ? "rejected_serial_no" : "serial_no";
		this.bundle = this.item?.is_rejected
			? this.item.rejected_serial_and_batch_bundle
			: this.item.serial_and_batch_bundle;

		this.init();
	}

	async init() {
		try {
			this.based_on = await erpnext.stock.get_pick_serial_batch_based_on();
		} catch (e) {
			this.based_on = "FIFO";
		}

		await this.make();
		this.render_data();
	}

	async make() {
		let label = this.item?.has_serial_no ? __("Serial Nos") : __("Batch Nos");
		let primary_label = this.bundle ? __("Update") : __("Add");

		if (this.item?.has_serial_no && this.item?.has_batch_no) {
			label = __("Serial Nos / Batch Nos");
		}

		primary_label += " " + label;

		this.dialog = new frappe.ui.Dialog({
			title: this.item?.title || primary_label,
			size: "large",
			fields: this.get_dialog_fields(),
			primary_action_label: primary_label,
			primary_action: () => this.update_bundle_entries(),
			secondary_action_label: __("Edit Full Form"),
			secondary_action: () => this.edit_full_form(),
		});

		let qty = this.item.stock_qty || this.item.transfer_qty || this.item.qty;

		if (this.item?.is_rejected) {
			qty = this.item.rejected_qty;
		}

		qty = Math.abs(qty);
		if (qty > 0) {
			await this.dialog.set_value("qty", qty);
		}
		await this.set_initial_entries(qty);

		this.dialog.show();
		this.$scan_btn = this.dialog.$wrapper.find(".link-btn");
		this.$scan_btn.css("display", "inline");
	}

	async set_initial_entries(qty) {
		if (this.bundle) return;

		const serial_nos = (this.item[this.serial_field] || "")
			.split(/[\n,]+/)
			.map((number) => number.trim())
			.filter(Boolean);
		const batch_no = this.item.batch_no;
		let batch_number;
		if (batch_no) {
			const numbers = await frappe.xcall(
				"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_serial_batch_numbers",
				{ item_code: this.item.item_code, doctype: "Batch", names: [batch_no] }
			);
			batch_number = numbers[batch_no];
			if (!batch_number) {
				frappe.throw(__("Please select a valid Batch No for this Item in the transaction row"));
			}
			frappe.utils.add_link_title("Batch", batch_no, batch_number);
		}

		if (serial_nos.length) {
			const table = this.dialog.fields_dict.entries;
			table.df.data = serial_nos.map((serial_no) => ({
				serial_number: serial_no,
				batch_no,
				qty: 1,
			}));
			table.grid.refresh();
			this.dialog.set_value("enter_manually", 0);
			this.dialog.refresh_dependency();
		} else if (batch_no) {
			this.set_data([{ batch_no, qty }]);
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
		let fields = [
			{
				fieldname: "item_code",
				read_only: 1,
				fieldtype: "Link",
				options: "Item",
				label: __("Item Code"),
				default: this.item.item_code,
			},
		];

		fields.push({
			fieldtype: "Link",
			fieldname: "warehouse",
			label: __("Warehouse"),
			options: "Warehouse",
			default: this.get_warehouse(),
			onchange: () => {
				if (this.item?.is_rejected) {
					this.item.rejected_warehouse = this.dialog.get_value("warehouse");
				} else {
					this.item.warehouse = this.dialog.get_value("warehouse");
				}

				this.get_auto_data();
			},
			get_query: () => {
				return {
					query: "erpnext.controllers.queries.warehouse_query",
					filters: [
						["Bin", "item_code", "=", this.item.item_code],
						["Warehouse", "is_group", "=", 0],
						["Warehouse", "company", "=", this.frm.doc.company],
					],
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
			fields = [...this.get_filter_fields(), ...fields, ...this.get_attach_field()];
		} else {
			fields = [...fields, ...this.get_attach_field()];
		}

		fields.push({
			fieldtype: "Section Break",
			depends_on: "eval:doc.enter_manually !== 1 || doc.entries?.length > 0",
		});

		fields.push({
			fieldname: "entries",
			fieldtype: "Table",
			allow_bulk_edit: true,
			depends_on: "eval:doc.enter_manually !== 1 || doc.entries?.length > 0",
			data: [],
			fields: this.get_dialog_table_fields(),
		});

		return fields;
	}

	get_attach_field() {
		let me = this;
		let label = this.item?.has_serial_no ? __("Serial Nos") : __("Batch Nos");
		let primary_label = this.bundle ? __("Update") : __("Add");

		if (this.item?.has_serial_no && this.item?.has_batch_no) {
			label = __("Serial Nos / Batch Nos");
		}

		let fields = [];
		if (this.item.has_serial_no && this.item?.type_of_transaction !== "Outward") {
			fields.push({
				fieldtype: "Check",
				label: __("Enter Manually"),
				fieldname: "enter_manually",
				default: 1,
				depends_on: "eval:doc.import_using_csv_file !== 1",
				change() {
					if (me.dialog.get_value("enter_manually")) {
						me.dialog.set_value("import_using_csv_file", 0);
					}
				},
			});
		}

		fields = [
			...fields,
			{
				fieldtype: "Check",
				label: __("Import Using CSV file"),
				fieldname: "import_using_csv_file",
				depends_on: "eval:doc.enter_manually !== 1",
				default: !this.item.has_serial_no || this.item?.type_of_transaction === "Outward" ? 1 : 0,
				hidden: this.item?.type_of_transaction === "Outward",
				change() {
					if (me.dialog.get_value("import_using_csv_file")) {
						me.dialog.set_value("enter_manually", 0);
					}
				},
			},
			{
				fieldtype: "Section Break",
				depends_on: "eval:doc.import_using_csv_file === 1",
				label: __("{0} {1} via CSV File", [primary_label, label]),
			},
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

		if (this.item?.has_serial_no && this.item?.type_of_transaction !== "Outward") {
			fields = [
				...fields,
				{
					fieldtype: "Section Break",
					label: __("{0} {1} Manually", [primary_label, label]),
					depends_on: "eval:doc.enter_manually === 1",
				},
				{
					fieldtype: "Data",
					label: __("Serial No Range"),
					fieldname: "serial_no_range",
					depends_on: "eval:doc.enter_manually === 1 && !doc.serial_no_series",
					description: __('"SN-01::10" for "SN-01" to "SN-10"'),
					onchange: () => {
						this.set_serial_nos_from_range();
					},
				},
			];
		}

		if (this.item?.has_serial_no && this.item?.type_of_transaction !== "Outward") {
			fields = [
				...fields,
				{
					fieldtype: "Column Break",
					depends_on: "eval:doc.enter_manually === 1",
				},
				{
					fieldtype: "Small Text",
					label: __("Enter Serial Nos"),
					fieldname: "upload_serial_nos",
					depends_on: "eval:doc.enter_manually === 1",
					description: __("Enter each serial no in a new line"),
				},
			];
		}

		return fields;
	}

	set_serial_nos_from_range() {
		const serial_no_range = this.dialog.get_value("serial_no_range");

		if (!serial_no_range) {
			return;
		}

		const serial_nos = erpnext.stock.utils.get_serial_range(serial_no_range, "::");

		if (serial_nos) {
			this.dialog.set_value("upload_serial_nos", serial_nos.join("\n"));
		}
	}

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

	async upload_csv_file() {
		const file_path = this.dialog.get_value("attach_serial_batch_csv");
		const [serials, batches] = file_path
			? await frappe.xcall(
					"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.read_serial_batch_csv",
					{ file_path }
			  )
			: [[], []];
		if (file_path !== this.dialog.get_value("attach_serial_batch_csv")) return;

		const table = this.dialog.fields_dict.entries;
		const rows = serials.length ? serials : batches;
		table.df.data = [
			...table.df.data.filter((row) => !row.from_csv),
			...rows.map((row) => ({
				serial_number: row.serial_no,
				batch_number: row.batch_no,
				qty: Math.abs(flt(row.qty)),
				from_csv: true,
			})),
		];
		table.grid.refresh();
		this.dialog.refresh_dependency();
	}

	get_filter_fields() {
		return [
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
				default: this.based_on,
				fieldname: "based_on",
				label: __("Fetch Based On"),
				onchange: () => this.get_auto_data(),
			},
			{
				fieldtype: "Section Break",
			},
		];
	}

	get_batch_qty(batch_no, callback) {
		let warehouse = this.item.s_warehouse || this.item.t_warehouse || this.item.warehouse;
		frappe.call({
			method: "erpnext.stock.doctype.batch.batch.get_batch_qty",
			args: {
				batch_no: batch_no,
				warehouse: warehouse,
				item_code: this.item.item_code,
				posting_date: this.frm.doc.posting_date,
				posting_time: this.frm.doc.posting_time,
			},
			callback: (r) => {
				if (r.message) {
					callback(flt(r.message));
				}
			},
		});
	}

	get_dialog_table_fields() {
		let fields = [];
		let me = this;

		if (this.item.has_serial_no) {
			fields.push({
				fieldtype: "Link",
				options: "Serial No",
				fieldname: "serial_no",
				label: __("Serial No"),
				in_list_view: 1,
				formatter: (value, df, options, doc) =>
					this.format_number(value, df, options, doc, "serial_number"),
				change() {
					if (this.doc.serial_no) delete this.doc.serial_number;
				},
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
					formatter: (value, df, options, doc) =>
						this.format_number(value, df, options, doc, "batch_number"),
					get_route_options_for_new_doc: () => {
						return {
							item: this.item.item_code,
						};
					},
					change() {
						let doc = this.doc;
						if (doc.batch_no) delete doc.batch_number;
						if (!doc.qty && me.item.type_of_transaction === "Outward") {
							me.get_batch_qty(doc.batch_no, (qty) => {
								doc.qty = qty;
								this.grid.set_value("qty", qty, doc);
							});
						}
					},
					get_query: () => {
						let is_inward = false;
						if (
							(["Purchase Receipt", "Purchase Invoice"].includes(this.frm.doc.doctype) &&
								!this.frm.doc.is_return) ||
							(this.frm.doc.doctype === "Stock Entry" &&
								(this.frm.doc.purpose === "Material Receipt" ||
									(this.frm.doc.purpose === "Manufacture" && this.item.is_finished_item)))
						) {
							is_inward = true;
						}

						let include_expired_batches = me.include_expired_batches();

						return {
							query: "erpnext.controllers.queries.get_batch_no",
							filters: {
								item_code: this.item.item_code,
								warehouse:
									this.item.s_warehouse || this.item.t_warehouse || this.item.warehouse,
								is_inward: is_inward,
								posting_date: this.frm.doc.posting_date,
								posting_time: this.frm.doc.posting_time,
								include_expired_batches: include_expired_batches,
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

	format_number(value, df, options, doc, number_field) {
		return value
			? frappe.form.formatters.Link(value, df, options, doc)
			: frappe.utils.escape_html(doc?.[number_field] || "");
	}

	include_expired_batches() {
		return (
			this.frm.doc.doctype === "Stock Reconciliation" ||
			(this.frm.doc.doctype === "Stock Entry" &&
				["Material Receipt", "Material Transfer", "Material Issue"].includes(this.frm.doc.purpose))
		);
	}

	get_auto_data() {
		let { qty, based_on } = this.dialog.get_values();

		if (this.item.serial_and_batch_bundle || this.item.rejected_serial_and_batch_bundle) {
			if (this.qty && qty === Math.abs(this.qty)) {
				return;
			}
		}

		if (this.item[this.serial_field] || this.item.batch_no) {
			return;
		}

		if (!based_on) {
			based_on = this.based_on;
		}

		let warehouse = this.item.warehouse || this.item.s_warehouse;
		if (this.item?.is_rejected) {
			warehouse = this.item.rejected_warehouse;
		}

		if (qty) {
			frappe.call({
				method: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_auto_data",
				args: {
					item_code: this.item.item_code,
					warehouse: warehouse,
					has_serial_no: this.item.has_serial_no,
					has_batch_no: this.item.has_batch_no,
					qty: qty,
					based_on: based_on,
					posting_date: this.frm.doc.posting_date,
					posting_time: this.frm.doc.posting_time,
					scio_detail: this.item.scio_detail,
				},
				callback: (r) => {
					if (r.message) {
						const table = this.dialog.fields_dict.entries;
						table.df.data = [
							...r.message,
							...table.df.data.filter(
								(row) => row.serial_number || row.batch_number || row.from_csv
							),
						];
						table.grid.refresh();
					}
				},
			});
		}
	}

	async scan_barcode_data() {
		const doctype = this.item.has_serial_no ? "Serial No" : "Batch";
		const scan_field = this.item.has_serial_no ? "scan_serial_no" : "scan_batch_no";
		const number = this.dialog.get_value(scan_field)?.trim();
		if (!number) return;

		this.dialog.set_value(scan_field, "");
		this.dialog.set_value("enter_manually", 0);
		this.pending_scans = (this.pending_scans || 0) + 1;
		this.dialog.get_primary_btn().prop("disabled", true);
		try {
			const record = await frappe.xcall(
				"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_serial_batch_scan",
				{ item_code: this.item.item_code, number, doctype }
			);
			if (!record.name && this.item.type_of_transaction === "Outward") {
				frappe.throw(
					__("{0} {1} does not exist for Item {2}", [
						__(doctype),
						frappe.utils.escape_html(number),
						frappe.utils.escape_html(this.item.item_code),
					])
				);
			}
			if (record.name) {
				frappe.utils.add_link_title(doctype, record.name, record.serial_no || record.batch_id);
			}
			if (record.batch_no && !frappe.utils.get_link_title("Batch", record.batch_no)) {
				await frappe.utils.fetch_link_title("Batch", record.batch_no);
			}
			this.update_serial_batch_no(number, record);
		} finally {
			this.pending_scans -= 1;
			this.dialog.get_primary_btn().prop("disabled", this.pending_scans > 0);
		}
	}

	update_serial_batch_no(number, record) {
		const fieldname = this.item.has_serial_no ? "serial_no" : "batch_no";
		const number_field = this.item.has_serial_no ? "serial_number" : "batch_number";
		const entries = this.dialog.fields_dict.entries;
		const known_numbers = [number, record.serial_no, record.batch_id]
			.filter(Boolean)
			.map((value) => value.toLowerCase());
		const existing_row = entries.df.data.find(
			(row) =>
				(record.name && row[fieldname] === record.name) ||
				known_numbers.includes(row[number_field]?.trim().toLowerCase())
		);

		if (existing_row) {
			if (!this.item.has_serial_no) existing_row.qty = flt(existing_row.qty) + 1;
		} else if (record.name) {
			entries.df.data.push({ batch_no: record.batch_no, [fieldname]: record.name, qty: 1 });
		} else {
			entries.df.data.push({ [number_field]: number, qty: 1 });
		}

		entries.grid.refresh();
		this.dialog.refresh_dependency();
	}

	update_bundle_entries() {
		if (this.pending_scans) {
			frappe.throw(__("Please wait for barcode scanning to finish"));
		}
		const rows = this.dialog.get_values().entries || [];
		const entries = rows.filter((row) => !row.serial_number && !row.batch_number);
		let csv_entries = rows
			.filter((row) => row.serial_number || row.batch_number)
			.map((row) => ({
				serial_no_id: row.serial_no,
				batch_no_id: row.batch_no,
				serial_no: row.serial_number,
				batch_no: row.batch_number,
				qty: row.qty,
			}));
		let warehouse = this.dialog.get_value("warehouse");
		let upload_serial_nos = this.dialog.get_value("upload_serial_nos");

		if (!entries.length && !csv_entries.length && upload_serial_nos) {
			csv_entries = upload_serial_nos
				.split(/[\n,]+/)
				.map((number) => number.trim())
				.filter(Boolean)
				.map((serial_no) => ({ serial_no, qty: 1 }));
		}

		if (!entries.length && !csv_entries.length) {
			frappe.throw(__("Please add at least one Serial No / Batch No"));
		}

		if (!warehouse) {
			frappe.throw(__("Please select a Warehouse"));
		}

		if (this.item?.is_rejected && this.item.rejected_warehouse === this.item.warehouse) {
			frappe.throw(__("Rejected Warehouse and Accepted Warehouse cannot be the same."));
		}

		let qty_to_fetch = flt(this.dialog.get_value("qty"));
		let total_qty = [...entries, ...csv_entries].reduce((total, row) => total + (flt(row.qty) || 1.0), 0);

		if (flt(total_qty, 6) !== flt(qty_to_fetch, 6)) {
			const confirm_dialog = frappe.confirm(
				__(
					"<strong>Total qty</strong> of the rows (<strong>{0}</strong>) does not match the <strong>Qty to Fetch</strong> (<strong>{1}</strong>). Qty of the item will be changed to <strong>{0}</strong>. Are you sure want to proceed?",
					[format_number(total_qty), format_number(qty_to_fetch)]
				),
				() => this.create_bundle_entries(entries, warehouse, csv_entries)
			);
			confirm_dialog.indicator = "blue";
			confirm_dialog.set_indicator();

			return;
		}

		this.create_bundle_entries(entries, warehouse, csv_entries);
	}

	create_bundle_entries(entries, warehouse, csv_entries = []) {
		frappe
			.call({
				method: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.add_serial_batch_ledgers",
				args: {
					entries: entries,
					csv_entries: csv_entries,
					child_row: this.item,
					doc: this.frm.doc,
					warehouse: warehouse,
				},
			})
			.then((r) => {
				frappe.run_serially([
					() => this.clear_transaction_fields(),
					() => {
						this.callback && this.callback(r.message);
					},
					() => this.frm.save(),
					() => this.dialog.hide(),
				]);
			});
	}

	clear_transaction_fields() {
		const values = {};
		if (this.item[this.serial_field]) values[this.serial_field] = "";
		const other_serial_field = this.item.is_rejected ? "serial_no" : "rejected_serial_no";
		if (this.item.batch_no && !this.item[other_serial_field]) values.batch_no = "";
		return frappe.model.set_value(this.item.doctype, this.item.name, values);
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
		if (this.item?.is_rejected) {
			return this.item.rejected_warehouse;
		}

		return this.item?.type_of_transaction === "Outward"
			? this.item.warehouse || this.item.s_warehouse
			: this.item.warehouse || this.item.t_warehouse;
	}

	render_data() {
		if (!this.bundle && (this.item[this.serial_field] || this.item.batch_no)) return;

		if (this.bundle || (this.frm.doc.is_return && this.frm.doc.return_against)) {
			frappe
				.call({
					method: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_serial_batch_ledgers",
					args: {
						item_code: this.item.item_code,
						name: this.bundle,
						voucher_no: !this.frm.is_new() ? this.item.parent : "",
						child_row: this.frm.doc.is_return ? this.item : "",
					},
				})
				.then((r) => {
					if (r.message) {
						this.set_data(r.message);
					}
				});
		}
	}

	set_data(data) {
		data.forEach((d) => {
			d.qty = Math.abs(d.qty);
			d.name = d.child_row || d.name;
			this.dialog.fields_dict.entries.df.data.push(d);
		});

		this.dialog.fields_dict.entries.grid.refresh();
		if (this.dialog.fields_dict.entries.df.data?.length) {
			this.dialog.set_value("enter_manually", 0);
		}
	}
};
