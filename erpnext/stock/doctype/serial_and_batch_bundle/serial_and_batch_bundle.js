// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Serial and Batch Bundle", {
	setup(frm) {
		frm.trigger("set_queries");
	},

	before_submit(frm) {
		frappe.throw(__("The user cannot submit the Serial and Batch Bundle manually"));
	},

	refresh(frm) {
		frm.trigger("toggle_fields");
		frm.trigger("prepare_serial_batch_prompt");
	},

	item_code(frm) {
		frm.clear_custom_buttons();
		frm.trigger("prepare_serial_batch_prompt");
	},

	type_of_transaction(frm) {
		frm.clear_custom_buttons();
		frm.trigger("prepare_serial_batch_prompt");
	},

	warehouse(frm) {
		if (frm.doc.warehouse) {
			frm.call({
				method: "set_warehouse",
				doc: frm.doc,
				callback(r) {
					refresh_field("entries");
				},
			});
		}
	},

	has_serial_no(frm) {
		frm.trigger("toggle_fields");
	},

	has_batch_no(frm) {
		frm.trigger("toggle_fields");
	},

	prepare_serial_batch_prompt(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.item_code && frm.doc.type_of_transaction === "Inward") {
			let label = frm.doc?.has_serial_no === 1 ? __("Serial Nos") : __("Batch Nos");

			if (frm.doc?.has_serial_no === 1 && frm.doc?.has_batch_no === 1) {
				label = __("Serial and Batch Nos");
			}

			let fields = frm.events.get_prompt_fields(frm);

			frm.add_custom_button(__("Make " + label), () => {
				frappe.prompt(
					fields,
					(data) => {
						frm.events.add_serial_batch(frm, data);
					},
					"Add " + label,
					"Make " + label
				);
			});
		}
	},

	get_prompt_fields(frm) {
		let attach_field = {
			label: __("Attach CSV File"),
			fieldname: "csv_file",
			fieldtype: "Attach",
		};

		if (!frm.doc.has_batch_no) {
			attach_field.depends_on = "eval:doc.using_csv_file === 1";
		}

		let fields = [
			{
				label: __("Import Using CSV file"),
				fieldname: "using_csv_file",
				default: 1,
				fieldtype: "Check",
			},
			attach_field,
			{
				fieldtype: "Section Break",
			},
		];

		if (frm.doc.has_serial_no) {
			fields.push({
				label: "Serial Nos",
				fieldname: "serial_nos",
				fieldtype: "Small Text",
				depends_on: "eval:doc.using_csv_file === 0",
			});
		}

		if (frm.doc.has_batch_no) {
			fields = attach_field;
		}

		return fields;
	},

	add_serial_batch(frm, prompt_data) {
		frm.events.validate_prompt_data(frm, prompt_data);

		frm.call({
			method: "add_serial_batch",
			doc: frm.doc,
			args: {
				data: prompt_data,
			},
			callback(r) {
				refresh_field("entries");
			},
		});
	},

	validate_prompt_data(frm, prompt_data) {
		if (prompt_data.using_csv_file && !prompt_data.csv_file) {
			frappe.throw(__("Please attach CSV file"));
		}

		if (frm.doc.has_serial_no && !prompt_data.csv_file && !prompt_data.serial_nos) {
			frappe.throw(__("Please enter serial nos"));
		}
	},

	toggle_fields(frm) {
		let show_naming_series_field =
			frappe.user_defaults.set_serial_and_batch_bundle_naming_based_on_naming_series;
		frm.toggle_display("naming_series", cint(show_naming_series_field));
		frm.toggle_reqd("naming_series", cint(show_naming_series_field));

		frm.toggle_display("naming_series", frm.doc.__islocal ? true : false);

		if (frm.doc.has_serial_no) {
			frm.doc.entries.forEach((row) => {
				if (Math.abs(row.qty) !== 1) {
					frappe.model.set_value(row.doctype, row.name, "qty", 1);
				}
			});
		}

		frm.fields_dict.entries.grid.update_docfield_property(
			"serial_no",
			"read_only",
			!frm.doc.has_serial_no
		);

		frm.fields_dict.entries.grid.update_docfield_property("batch_no", "read_only", !frm.doc.has_batch_no);

		frm.fields_dict.entries.grid.update_docfield_property("qty", "read_only", frm.doc.has_serial_no);
	},

	set_queries(frm) {
		frm.set_query("item_code", () => {
			return {
				query: "erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.item_query",
			};
		});

		frm.set_query("voucher_type", () => {
			return {
				filters: {
					istable: 0,
					issingle: 0,
					is_submittable: 1,
					name: [
						"in",
						[
							"Asset Capitalization",
							"Asset Repair",
							"Delivery Note",
							"Installation Note",
							"Job Card",
							"Maintenance Schedule",
							"POS Invoice",
							"Pick List",
							"Purchase Invoice",
							"Purchase Receipt",
							"Quotation",
							"Sales Invoice",
							"Stock Entry",
							"Stock Reconciliation",
							"Subcontracting Receipt",
						],
					],
				},
			};
		});

		frm.set_query("voucher_no", () => {
			return {
				filters: {
					docstatus: ["!=", 2],
				},
			};
		});

		frm.set_query("warehouse", () => {
			return {
				filters: {
					is_group: 0,
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("serial_no", "entries", () => {
			return {
				filters: {
					item_code: frm.doc.item_code,
				},
			};
		});

		frm.set_query("batch_no", "entries", (doc) => {
			if (doc.type_of_transaction === "Outward") {
				return {
					query: "erpnext.controllers.queries.get_batch_no",
					filters: {
						item_code: doc.item_code,
						warehouse: doc.warehouse,
					},
				};
			} else {
				return {
					filters: {
						item: doc.item_code,
						disabled: 0,
					},
				};
			}
		});

		frm.set_query("warehouse", "entries", () => {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
		});
	},
});

frappe.ui.form.on("Serial and Batch Entry", {
	entries_add(frm, cdt, cdn) {
		if (frm.doc.warehouse) {
			frappe.model.set_value(cdt, cdn, "warehouse", frm.doc.warehouse);
		}
	},
});
