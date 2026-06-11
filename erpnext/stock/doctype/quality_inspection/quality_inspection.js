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
	},

	inspection_basis(frm) {
		frm.trigger("toggle_batch_and_serial_fields");
		frm.trigger("toggle_populate_units_button");
		frm.trigger("prefill_decided_quantity_from_lot");
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
		// only show batch / serial for items that are actually tracked that way
		if (!frm.doc.item_code) {
			frm.toggle_display(["batch_no", "serial_no"], false);
			frm.set_df_property("batch_no", "reqd", 0);
			frm.set_df_property("serial_no", "reqd", 0);
			return;
		}

		frappe.db.get_value("Item", frm.doc.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
			frm.__item_is_serialized = cint(r.message?.has_serial_no);
			const has_batch = cint(r.message?.has_batch_no);
			const bundle_decided = frm.doc.inspection_basis === "Each Quantity";
			const show_serial = frm.__item_is_serialized && !bundle_decided;
			// a lot-referenced Each Quantity inspection draws its identity from
			// the lot: serials per unit below, the batch on the lot itself
			const batch_exempt = bundle_decided && frm.doc.reference_type === "Quality Control Lot";

			frm.toggle_display("batch_no", has_batch && !batch_exempt);
			// Each Quantity inspections record serials per unit below
			frm.toggle_display("serial_no", show_serial);
			// the recorded serials drive the sample size for serialized items
			frm.set_df_property("sample_size", "read_only", show_serial ? 1 : 0);

			// mirror the server's identity gates as mandatory marks
			frm.set_df_property("serial_no", "reqd", show_serial ? 1 : 0);

			if (!has_batch || batch_exempt) {
				frm.set_df_property("batch_no", "reqd", 0);
			} else if (frm.doc.child_row_reference && frm.doc.reference_type !== "Quality Control Lot") {
				// an auto-created batch does not exist before the inbound document
				// submits — the field cannot be filled, so it cannot be mandatory
				const child_doctype =
					frm.doc.reference_type === "Stock Entry"
						? "Stock Entry Detail"
						: frm.doc.reference_type + " Item";
				frappe.db
					.get_value(child_doctype, frm.doc.child_row_reference, [
						"batch_no",
						"serial_and_batch_bundle",
					])
					.then((row) => {
						const row_has_batch = row.message?.batch_no || row.message?.serial_and_batch_bundle;
						frm.set_df_property("batch_no", "reqd", row_has_batch ? 1 : 0);
					});
			} else {
				frm.set_df_property("batch_no", "reqd", 1);
			}
		});
	},

	serial_no: function (frm) {
		if (!frm.__item_is_serialized || frm.doc.inspection_basis === "Each Quantity") {
			return;
		}
		const count = (frm.doc.serial_no || "")
			.split("\n")
			.map((serial) => serial.trim())
			.filter(Boolean).length;
		if (count) {
			frm.set_value("sample_size", count);
		}
	},

	reference_name: function (frm) {
		// the lot dictates how it is inspected; the server re-derives on save
		if (frm.doc.reference_type === "Quality Control Lot" && frm.doc.reference_name) {
			frappe.db
				.get_value("Quality Control Lot", frm.doc.reference_name, [
					"inspection_basis",
					"received_qty",
					"decided_qty",
				])
				.then((r) => {
					frm.set_value("inspection_basis", r.message?.inspection_basis || "Sample");
					frm.trigger("prefill_decided_quantity_from_lot");
				});
		} else {
			frm.set_value("inspection_basis", "Sample");
		}
	},

	manual_inspection(frm) {
		frm.trigger("prefill_decided_quantity_from_lot");
	},

	prefill_decided_quantity_from_lot(frm) {
		// the verdict decides everything still undecided unless the inspector
		// narrows it to a tranche
		if (
			frm.doc.docstatus !== 0 ||
			frm.doc.reference_type !== "Quality Control Lot" ||
			!frm.doc.reference_name ||
			(frm.doc.inspection_basis === "Each Quantity" && !frm.doc.manual_inspection) ||
			flt(frm.doc.decided_quantity)
		) {
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
		if (frm.doc.item_code && !frm.doc.quality_inspection_template) {
			return frm.call({
				method: "get_quality_inspection_template",
				doc: frm.doc,
				callback: function () {
					refresh_field(["quality_inspection_template", "readings"]);
				},
			});
		}
	},

});
