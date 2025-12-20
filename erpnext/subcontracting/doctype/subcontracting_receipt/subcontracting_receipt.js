// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.buying");

erpnext.landed_cost_taxes_and_charges.setup_triggers("Subcontracting Receipt");

frappe.ui.form.on("Subcontracting Receipt", {
	setup: (frm) => {
		frm.ignore_doctypes_on_cancel_all = ["Serial and Batch Bundle"];
		frm.get_field("supplied_items").grid.cannot_add_rows = true;
		frm.get_field("supplied_items").grid.only_sortable();
		frm.trigger("set_queries");

		frm.custom_make_buttons = {
			"Purchase Receipt": "Purchase Receipt",
		};
	},

	on_submit(frm) {
		frm.events.refresh_serial_batch_bundle_field(frm);
	},

	refresh_serial_batch_bundle_field(frm) {
		frappe.route_hooks.after_submit = (frm_obj) => {
			frm_obj.reload_doc();
		};
	},

	refresh: (frm) => {
		frappe.dynamic_link = { doc: frm.doc, fieldname: "supplier", doctype: "Supplier" };

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Stock Ledger"),
				() => {
					frappe.route_options = {
						voucher_no: frm.doc.name,
						from_date: frm.doc.posting_date,
						to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
						company: frm.doc.company,
						show_cancelled_entries: frm.doc.docstatus === 2,
					};
					frappe.set_route("query-report", "Stock Ledger");
				},
				__("View")
			);

			frm.add_custom_button(
				__("Accounting Ledger"),
				() => {
					frappe.route_options = {
						voucher_no: frm.doc.name,
						from_date: frm.doc.posting_date,
						to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
						company: frm.doc.company,
						categorize_by: "Categorize by Voucher (Consolidated)",
						show_cancelled_entries: frm.doc.docstatus === 2,
					};
					frappe.set_route("query-report", "General Ledger");
				},
				__("View")
			);

			if (frm.doc.is_return === 0) {
				frm.add_custom_button(
					__("Purchase Receipt"),
					() => {
						frappe.model.open_mapped_doc({
							method: "erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt.make_purchase_receipt",
							frm: frm,
							freeze: true,
							freeze_message: __("Creating Purchase Receipt ..."),
						});
					},
					__("Create")
				);
			}
		}

		if (!frm.doc.is_return && frm.doc.docstatus === 1 && frm.doc.per_returned < 100) {
			frm.add_custom_button(
				__("Subcontract Return"),
				() => {
					const make_standard_return = () => {
						frappe.model.open_mapped_doc({
							method: "erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt.make_subcontract_return",
							frm: frm,
						});
					};

					let has_rejected_items = frm.doc.items.filter((item) => {
						if (item.rejected_qty > 0) {
							return true;
						}
					});

					if (has_rejected_items && has_rejected_items.length > 0) {
						frappe.prompt(
							[
								{
									label: __("Return Qty from Rejected Warehouse"),
									fieldtype: "Check",
									fieldname: "return_for_rejected_warehouse",
									default: 1,
								},
							],
							function (values) {
								if (values.return_for_rejected_warehouse) {
									frappe.call({
										method: "erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt.make_subcontract_return_against_rejected_warehouse",
										args: {
											source_name: frm.doc.name,
										},
										callback: function (r) {
											if (r.message) {
												frappe.model.sync(r.message);
												frappe.set_route("Form", r.message.doctype, r.message.name);
											}
										},
									});
								} else {
									make_standard_return();
								}
							},
							__("Return Qty"),
							__("Make Return Entry")
						);
					} else {
						make_standard_return();
					}
				},
				__("Create")
			);
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(
				__("Subcontracting Order"),
				() => {
					if (!frm.doc.supplier) {
						frappe.throw({
							title: __("Mandatory"),
							message: __("Please Select a Supplier"),
						});
					}

					erpnext.utils.map_current_doc({
						method: "erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt",
						source_doctype: "Subcontracting Order",
						target: frm,
						setters: {
							supplier: frm.doc.supplier,
						},
						get_query_filters: {
							docstatus: 1,
							per_received: ["<", 100],
							company: frm.doc.company,
							status: ["!=", "Closed"],
						},
					});
				},
				__("Get Items From")
			);

			frm.fields_dict.supplied_items.grid.update_docfield_property(
				"consumed_qty",
				"read_only",
				frm.doc.__onload && frm.doc.__onload.backflush_based_on === "BOM"
			);
		}

		frm.trigger("setup_quality_inspection");
		frm.trigger("set_route_options_for_new_doc");
	},

	set_warehouse: (frm) => {
		set_warehouse_in_children(frm.doc.items, "warehouse", frm.doc.set_warehouse);
	},

	rejected_warehouse: (frm) => {
		set_warehouse_in_children(frm.doc.items, "rejected_warehouse", frm.doc.rejected_warehouse);
	},

	get_scrap_items: (frm) => {
		frappe.call({
			doc: frm.doc,
			method: "get_scrap_items",
			args: {
				recalculate_rate: true,
			},
			freeze: true,
			freeze_message: __("Getting Scrap Items"),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh();
				}
			},
		});
	},

	set_queries: (frm) => {
		frm.set_query("set_warehouse", () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});

		frm.set_query("contact_person", erpnext.queries.contact_query);
		frm.set_query("supplier_address", erpnext.queries.address_query);

		frm.set_query("billing_address", erpnext.queries.company_address_query);

		frm.set_query("shipping_address", () => {
			return erpnext.queries.company_address_query(frm.doc);
		});

		frm.set_query("rejected_warehouse", () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});

		frm.set_query("cost_center", (doc) => {
			return {
				filters: {
					company: doc.company,
				},
			};
		});

		frm.set_query("cost_center", "items", (doc) => {
			return {
				filters: {
					company: doc.company,
				},
			};
		});

		frm.set_query("supplier_warehouse", () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});

		frm.set_query("warehouse", "items", () => ({
			filters: {
				company: frm.doc.company,
				is_group: 0,
			},
		}));

		frm.set_query("rejected_warehouse", "items", () => ({
			filters: {
				company: frm.doc.company,
				is_group: 0,
			},
		}));

		frm.set_query("expense_account", "items", () => {
			return {
				query: "erpnext.controllers.queries.get_expense_account",
				filters: { company: frm.doc.company },
			};
		});

		frm.set_query("batch_no", "items", (doc, cdt, cdn) => {
			var row = locals[cdt][cdn];
			return {
				filters: {
					item: row.item_code,
				},
			};
		});

		frm.set_query("serial_and_batch_bundle", "items", (doc, cdt, cdn) => {
			return frm.events.get_serial_and_batch_bundle_filters(doc, cdt, cdn);
		});

		frm.set_query("rejected_serial_and_batch_bundle", "items", (doc, cdt, cdn) => {
			return frm.events.get_serial_and_batch_bundle_filters(doc, cdt, cdn);
		});

		frm.set_query("batch_no", "supplied_items", (doc, cdt, cdn) => {
			let row = locals[cdt][cdn];
			let filters = {
				item_code: row.rm_item_code,
				warehouse: doc.supplier_warehouse,
			};

			return {
				query: "erpnext.controllers.queries.get_batch_no",
				filters: filters,
			};
		});

		frm.set_query("serial_and_batch_bundle", "supplied_items", (doc, cdt, cdn) => {
			let row = locals[cdt][cdn];
			return {
				filters: {
					item_code: row.rm_item_code,
					voucher_type: doc.doctype,
					voucher_no: ["in", [doc.name, ""]],
					is_cancelled: 0,
				},
			};
		});
	},

	get_serial_and_batch_bundle_filters: (doc, cdt, cdn) => {
		let row = locals[cdt][cdn];
		return {
			filters: {
				item_code: row.item_code,
				voucher_type: doc.doctype,
				voucher_no: ["in", [doc.name, ""]],
				is_cancelled: 0,
			},
		};
	},

	setup_quality_inspection: (frm) => {
		if (!frm.is_new() && frm.doc.docstatus === 0 && !frm.doc.is_return) {
			let transaction_controller = new erpnext.TransactionController({ frm: frm });
			transaction_controller.setup_quality_inspection();
		}
	},

	set_route_options_for_new_doc: (frm) => {
		let batch_no_field = frm.get_docfield("items", "batch_no");
		if (batch_no_field) {
			batch_no_field.get_route_options_for_new_doc = (row) => {
				return {
					item: row.doc.item_code,
				};
			};
		}

		let item_sbb_field = frm.get_docfield("items", "serial_and_batch_bundle");
		if (item_sbb_field) {
			item_sbb_field.get_route_options_for_new_doc = (row) => {
				return {
					item_code: row.doc.item_code,
					voucher_type: frm.doc.doctype,
				};
			};
		}

		let rejected_item_sbb_field = frm.get_docfield("items", "rejected_serial_and_batch_bundle");
		if (rejected_item_sbb_field) {
			rejected_item_sbb_field.get_route_options_for_new_doc = (row) => {
				return {
					item_code: row.doc.item_code,
					voucher_type: frm.doc.doctype,
				};
			};
		}

		let rm_sbb_field = frm.get_docfield("supplied_items", "serial_and_batch_bundle");
		if (rm_sbb_field) {
			rm_sbb_field.get_route_options_for_new_doc = (row) => {
				return {
					item_code: row.doc.rm_item_code,
					voucher_type: frm.doc.doctype,
				};
			};
		}
	},

	reset_raw_materials_table: (frm) => {
		frm.clear_table("supplied_items");
		frm.doc.__unsaved = true;
		if (!frm.doc.set_posting_time) {
			frm.set_value("posting_time", frappe.datetime.now_time());
		}

		frm.call({
			method: "reset_raw_materials",
			doc: frm.doc,
			freeze: true,
			callback: (r) => {
				if (!r.exc) {
					frm.save();
				}
			},
		});
	},
});

frappe.ui.form.on("Landed Cost Taxes and Charges", {
	amount: (frm, cdt, cdn) => {
		set_missing_values(frm);
		frm.events.set_base_amount(frm, cdt, cdn);
	},

	expense_account: (frm, cdt, cdn) => {
		frm.events.set_account_currency(frm, cdt, cdn);
	},

	additional_costs_remove: (frm) => {
		set_missing_values(frm);
	},
});

frappe.ui.form.on("Subcontracting Receipt Item", {
	item_code(frm) {
		set_missing_values(frm);
	},

	qty(frm) {
		set_missing_values(frm);
	},

	rate(frm) {
		set_missing_values(frm);
	},

	items_delete: (frm) => {
		set_missing_values(frm);
	},

	add_serial_batch_bundle(frm, cdt, cdn) {
		let item = locals[cdt][cdn];

		frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
			if (r.message && (r.message.has_batch_no || r.message.has_serial_no)) {
				item.has_serial_no = r.message.has_serial_no;
				item.has_batch_no = r.message.has_batch_no;
				item.type_of_transaction = item.qty > 0 ? "Inward" : "Outward";
				item.is_rejected = false;

				new erpnext.SerialBatchPackageSelector(frm, item, (r) => {
					if (r) {
						let qty = Math.abs(r.total_qty);
						if (frm.doc.is_return) {
							qty = qty * -1;
						}

						let update_values = {
							serial_and_batch_bundle: r.name,
							use_serial_batch_fields: 0,
							qty: qty / flt(item.conversion_factor || 1, precision("conversion_factor", item)),
						};

						if (r.warehouse) {
							update_values["warehouse"] = r.warehouse;
						}

						frappe.model.set_value(item.doctype, item.name, update_values);
					}
				});
			}
		});
	},

	add_serial_batch_for_rejected_qty(frm, cdt, cdn) {
		let item = locals[cdt][cdn];

		frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
			if (r.message && (r.message.has_batch_no || r.message.has_serial_no)) {
				item.has_serial_no = r.message.has_serial_no;
				item.has_batch_no = r.message.has_batch_no;
				item.type_of_transaction = item.rejected_qty > 0 ? "Inward" : "Outward";
				item.is_rejected = true;

				new erpnext.SerialBatchPackageSelector(frm, item, (r) => {
					if (r) {
						let qty = Math.abs(r.total_qty);
						if (frm.doc.is_return) {
							qty = qty * -1;
						}

						let update_values = {
							serial_and_batch_bundle: r.name,
							use_serial_batch_fields: 0,
							rejected_qty:
								qty / flt(item.conversion_factor || 1, precision("conversion_factor", item)),
						};

						if (r.warehouse) {
							update_values["rejected_warehouse"] = r.warehouse;
						}

						frappe.model.set_value(item.doctype, item.name, update_values);
					}
				});
			}
		});
	},
});

frappe.ui.form.on("Subcontracting Receipt Supplied Item", {
	consumed_qty(frm) {
		set_missing_values(frm);
	},

	add_serial_batch_bundle(frm, cdt, cdn) {
		let item = locals[cdt][cdn];

		item.item_code = item.rm_item_code;
		item.qty = item.consumed_qty;
		item.warehouse = frm.doc.supplier_warehouse;
		frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
			if (r.message && (r.message.has_batch_no || r.message.has_serial_no)) {
				item.has_serial_no = r.message.has_serial_no;
				item.has_batch_no = r.message.has_batch_no;
				item.type_of_transaction = item.qty > 0 ? "Outward" : "Inward";
				item.is_rejected = false;

				new erpnext.SerialBatchPackageSelector(frm, item, (r) => {
					if (r) {
						let qty = Math.abs(r.total_qty);
						if (frm.doc.is_return) {
							qty = qty * -1;
						}

						let update_values = {
							serial_and_batch_bundle: r.name,
							use_serial_batch_fields: 0,
							consumed_qty:
								qty / flt(item.conversion_factor || 1, precision("conversion_factor", item)),
						};

						frappe.model.set_value(item.doctype, item.name, update_values);
					}
				});
			}
		});
	},
});

let set_warehouse_in_children = (child_table, warehouse_field, warehouse) => {
	let transaction_controller = new erpnext.TransactionController();
	transaction_controller.autofill_warehouse(child_table, warehouse_field, warehouse);
};

let set_missing_values = (frm) => {
	frappe.call({
		doc: frm.doc,
		method: "set_missing_values",
		callback: (r) => {
			if (!r.exc) frm.refresh();
		},
	});
};
