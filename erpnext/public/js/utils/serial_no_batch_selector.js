erpnext.SerialBatchPackageSelector = class SerialNoBatchBundleUpdate {
	constructor(frm, item, callback) {
		this.frm = frm;
		this.item = item;
		this.qty = item.qty;
		this.callback = callback;
		this.bundle = this.item?.is_rejected
			? this.item.rejected_serial_and_batch_bundle
			: this.item.serial_and_batch_bundle;

		this.make();
		this.render_data();
	}

	make() {
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
				if (this.item?.is_rejected) {
					this.item.rejected_warehouse = this.dialog.get_value("warehouse");
				} else {
					this.item.warehouse = this.dialog.get_value("warehouse");
				}

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
		if (this.item.has_serial_no) {
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
				default: !this.item.has_serial_no ? 1 : 0,
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

		if (this.item?.has_serial_no) {
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

		if (this.item?.has_serial_no) {
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
		});
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
					get_route_options_for_new_doc: () => {
						return {
							item: this.item.item_code,
						};
					},
					change() {
						let doc = this.doc;
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

		if (this.item.serial_no || this.item.batch_no) {
			return;
		}

		if (!based_on) {
			based_on = "FIFO";
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
						this.dialog.fields_dict.entries.df.data = r.message;
						this.dialog.fields_dict.entries.grid.refresh();
					}
				},
			});
		}
	}

	scan_barcode_data() {
		const { scan_serial_no, scan_batch_no } = this.dialog.get_values();

		this.dialog.set_value("enter_manually", 0);

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
						this.dialog.fields_dict.entries.df.data.push({
							serial_no: scan_serial_no,
							batch_no: r.message,
						});

						this.dialog.fields_dict.scan_serial_no.set_value("");
						this.dialog.fields_dict.entries.grid.refresh();
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
		let upload_serial_nos = this.dialog.get_value("upload_serial_nos");

		if (!entries?.length && upload_serial_nos) {
			this.create_serial_nos();
			return;
		}

		if ((entries && !entries.length) || !entries) {
			frappe.throw(__("Please add atleast one Serial No / Batch No"));
		}

		if (!warehouse) {
			frappe.throw(__("Please select a Warehouse"));
		}

		if (this.item?.is_rejected && this.item.rejected_warehouse === this.item.warehouse) {
			frappe.throw(__("Rejected Warehouse and Accepted Warehouse cannot be same."));
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
				frappe.run_serially([
					() => {
						this.callback && this.callback(r.message);
					},
					() => this.frm.save(),
					() => this.dialog.hide(),
				]);
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
		if (this.item?.is_rejected) {
			return this.item.rejected_warehouse;
		}

		return this.item?.type_of_transaction === "Outward"
			? this.item.warehouse || this.item.s_warehouse
			: this.item.warehouse || this.item.t_warehouse;
	}

	render_data() {
		if (this.bundle || this.frm.doc.is_return) {
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
