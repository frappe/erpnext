// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;

frappe.ui.form.on("Quality Inspection", {
	onload(frm) {
		frm.trigger("set_default_company");

		// the blank option exists only so the server can tell "not chosen yet"
		// from an inspector's choice; the form never offers it
		frm.set_df_property("inspection_basis", "options", ["Sample", "Each Quantity"]);
		if (frm.is_new() && !frm.doc.inspection_basis) {
			frm.set_value("inspection_basis", "Sample");
		}
	},

	set_default_company(frm) {
		if (frm.doc.docstatus === 0 && !frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_default("company"));
		}
	},

	setup: function (frm) {
		frm.set_query("reference_name", function (doc) {
			let filters = { docstatus: ["!=", 2] };

			if (doc.company) {
				filters["company"] = doc.company;
			}

			return {
				filters: filters,
			};
		});

		frm.set_query("batch_no", function () {
			return {
				filters: {
					item: frm.doc.item_code,
				},
			};
		});

		// a both-tracked item's units can only be the mirrored batch's serials
		frm.set_query("serial_no", "unit_readings", function (doc) {
			const filters = { item_code: doc.item_code };
			if (doc.batch_no) {
				filters.batch_no = doc.batch_no;
			}
			return { filters: filters };
		});

		// item code based on GRN/DN
		frm.set_query("item_code", function (doc) {
			if (doc.reference_type && doc.reference_name) {
				return {
					query: "erpnext.stock.doctype.quality_inspection.quality_inspection.item_query",
					filters: {
						reference_doctype: doc.reference_type,
						reference_name: doc.reference_name,
						inspection_type: doc.inspection_type,
					},
				};
			}
		});
	},

	refresh: function (frm) {
		// Ignore cancellation of reference doctype on cancel all.
		frm.ignore_doctypes_on_cancel_all = [frm.doc.reference_type, "Serial and Batch Bundle"];
		frm.trigger("toggle_batch_and_serial_fields");
		frm.trigger("toggle_populate_units_button");
		frm.trigger("toggle_unit_quantity");
	},

	inspection_basis(frm) {
		frm.trigger("toggle_batch_and_serial_fields");
		frm.trigger("toggle_populate_units_button");
		frm.trigger("prefill_decided_quantity_from_lot");
		frm.trigger("toggle_unit_quantity");
	},

	reference_type(frm) {
		frm.trigger("toggle_unit_quantity");
	},

	toggle_unit_quantity(frm) {
		// a tranche is only choosable where undecided units can wait (a lot or
		// custody row); every other reference is decided whole, so the count
		// is a fact of the row, not an input
		const tranche_capable = ["Quality Control Lot", "Goods Inward Note"].includes(frm.doc.reference_type);
		frm.set_df_property("unit_quantity", "read_only", tranche_capable ? 0 : 1);
		if (
			tranche_capable ||
			frm.doc.docstatus !== 0 ||
			frm.doc.inspection_basis !== "Each Quantity" ||
			!frm.doc.reference_name ||
			!frm.doc.item_code
		) {
			return;
		}
		frm.call("get_qty_under_inspection").then((r) => {
			const qty = flt(r.message);
			// fractional quantities stay blank; the server points those at Sample
			if (qty && qty === cint(qty) && cint(frm.doc.unit_quantity) !== qty) {
				frm.set_value("unit_quantity", qty);
			}
		});
	},

	quality_inspection_template(frm) {
		frm.trigger("toggle_populate_units_button");
		if (frm.doc.quality_inspection_template && frm.doc.inspection_basis !== "Each Quantity") {
			return frm.call({
				method: "get_item_specification_details",
				doc: frm.doc,
				callback: function () {
					refresh_field("readings");
				},
			});
		}
	},

	toggle_populate_units_button(frm) {
		frm.remove_custom_button(__("Populate Units"));
		if (
			frm.doc.docstatus === 0 &&
			frm.doc.inspection_basis === "Each Quantity" &&
			!frm.doc.manual_inspection &&
			frm.doc.quality_inspection_template
		) {
			frm.add_custom_button(__("Populate Units"), () => {
				frm.call("populate_units").then(() => {
					frm.refresh_field("unit_readings");
					frm.dirty();
				});
			});
		}
	},

	toggle_batch_and_serial_fields(frm) {
		// identity flows by reference: a lot mirrors its batch, custody may
		// record the supplier's serials (no batch exists yet), and a
		// transaction-referenced (Block / Warn) inspection names the identity
		// it vouches for — the document reconciles coverage at its submission
		if (!frm.doc.item_code) {
			frm.toggle_display(["batch_no", "serial_no"], false);
			frm.trigger("toggle_unit_serial_column");
			return;
		}

		frappe.db.get_value("Item", frm.doc.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
			frm.__item_is_serialized = cint(r.message?.has_serial_no);
			frm.trigger("toggle_unit_serial_column");
			// serialization decides whether the decided quantity is lockable
			frm.trigger("prefill_decided_quantity_from_lot");

			const bundle_decided = frm.doc.inspection_basis === "Each Quantity";
			const is_lot = frm.doc.reference_type === "Quality Control Lot";
			const is_custody = frm.doc.reference_type === "Goods Inward Note";

			// on a lot, Each Quantity identity lives per unit in the readings
			// below — but a both-tracked item keeps the batch on show: it
			// narrows the units' serial picker
			frm.toggle_display(
				"batch_no",
				cint(r.message?.has_batch_no) &&
					!is_custody &&
					(!is_lot || !bundle_decided || frm.__item_is_serialized)
			);
			frm.set_df_property("batch_no", "read_only", is_lot ? 1 : 0);
			frm.set_df_property("batch_no", "reqd", 0);

			frm.toggle_display("serial_no", frm.__item_is_serialized && !bundle_decided);
			frm.set_df_property("serial_no", "reqd", 0);
			frm.trigger("toggle_sample_size_lock");

			// a transaction row still without identity gets it at submission —
			// there is nothing for the inspection to name yet
			if (!is_lot && !is_custody && frm.doc.reference_name) {
				frm.call("get_reference_row_identity").then((r) => {
					if (!r.message) {
						return;
					}
					if (!r.message.has_batch) {
						frm.toggle_display("batch_no", false);
					}
					if (!r.message.has_serials) {
						frm.toggle_display("serial_no", false);
					}
				});
			}
		});
	},

	toggle_unit_serial_column(frm) {
		// unit readings only name serials when the item has them to name
		const serialized = cint(frm.__item_is_serialized);
		const grid = frm.fields_dict.unit_readings?.grid;
		grid?.update_docfield_property("serial_no", "hidden", serialized ? 0 : 1);
		grid?.update_docfield_property("serial_no", "read_only", serialized ? 0 : 1);
	},

	toggle_sample_size_lock(frm) {
		// recorded serials are the sample: they set its size and lock it;
		// without them the size is the inspector's to type
		const count = (frm.doc.serial_no || "")
			.split("\n")
			.map((serial) => serial.trim())
			.filter(Boolean).length;
		if (count && frm.doc.inspection_basis !== "Each Quantity") {
			frm.set_value("sample_size", count);
		}
		frm.set_df_property("sample_size", "read_only", count ? 1 : 0);
	},

	serial_no: function (frm) {
		frm.trigger("toggle_sample_size_lock");
	},

	reference_name: function (frm) {
		// the lot dictates how it is inspected; the server re-derives on save
		if (frm.doc.reference_type === "Quality Control Lot" && frm.doc.reference_name) {
			frappe.db
				.get_value("Quality Control Lot", frm.doc.reference_name, [
					"inspection_basis",
					"item_code",
					"batch_no",
					"received_qty",
					"decided_qty",
				])
				.then((r) => {
					// a lot quarantines exactly one item: fill it in, nothing to pick
					if (r.message?.item_code && !frm.doc.item_code) {
						frm.set_value("item_code", r.message.item_code);
					}
					// the lot's batch is a fact, not a choice — mirror it
					frm.set_value("batch_no", r.message?.batch_no || "");
					frm.set_value("inspection_basis", r.message?.inspection_basis || "Sample");
					frm.trigger("prefill_decided_quantity_from_lot");
				});
		} else {
			frm.set_value("inspection_basis", "Sample");
		}
		frm.trigger("toggle_unit_quantity");
	},

	manual_inspection(frm) {
		frm.trigger("prefill_decided_quantity_from_lot");
	},

	prefill_decided_quantity_from_lot(frm) {
		// the verdict decides everything still undecided unless the inspector
		// narrows it to a tranche — but a serialized lot verdict without
		// per-unit readings cannot narrow (it could not say which units), so
		// the full quantity is locked in
		const locked =
			cint(frm.__item_is_serialized) &&
			frm.doc.reference_type === "Quality Control Lot" &&
			!(frm.doc.inspection_basis === "Each Quantity" && !frm.doc.manual_inspection);
		frm.set_df_property("decided_quantity", "read_only", locked ? 1 : 0);
		if (
			frm.doc.docstatus !== 0 ||
			!["Quality Control Lot", "Goods Inward Note"].includes(frm.doc.reference_type) ||
			!frm.doc.reference_name ||
			(frm.doc.inspection_basis === "Each Quantity" && !frm.doc.manual_inspection) ||
			(flt(frm.doc.decided_quantity) && !locked)
		) {
			return;
		}
		if (frm.doc.reference_type === "Goods Inward Note") {
			frm.call("get_qty_under_inspection").then((r) => {
				if (r.message != null) {
					frm.set_value("decided_quantity", flt(r.message));
				}
			});
			return;
		}
		frappe.db
			.get_value("Quality Control Lot", frm.doc.reference_name, ["received_qty", "decided_qty"])
			.then((r) => {
				if (r.message) {
					frm.set_value(
						"decided_quantity",
						flt(r.message.received_qty) - flt(r.message.decided_qty)
					);
				}
			});
	},

	item_code: function (frm) {
		frm.trigger("toggle_batch_and_serial_fields");
		// a custody row resolves its quantity through the item's row
		frm.trigger("prefill_decided_quantity_from_lot");
		frm.trigger("toggle_unit_quantity");
	},
});
