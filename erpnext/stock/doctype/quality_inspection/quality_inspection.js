// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;

frappe.ui.form.on("Quality Inspection", {
	onload(frm) {
		frm.trigger("set_default_company");
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

		// bundles are born from their inspection: only this inspection's own
		// bundles are selectable
		frm.set_query("reading_bundle", function (doc) {
			return {
				filters: {
					item_code: doc.item_code,
					quality_inspection: doc.name,
					docstatus: ["!=", 2],
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
		// Ignore cancellation of reference doctype on cancel all. The reading
		// bundle is frozen evidence — released by the server on cancel, not cancelled.
		frm.ignore_doctypes_on_cancel_all = [
			frm.doc.reference_type,
			"Serial and Batch Bundle",
			"Quality Inspection Reading Bundle",
		];
		frm.trigger("toggle_batch_and_serial_fields");
		// this Frappe version's DocField schema drops only_select from the doctype
		// JSON, so set it client-side: bundles are born from the Create Reading
		// Bundle button (server-side), never from the link field
		frm.set_df_property("reading_bundle", "only_select", 1);

		if (
			frm.doc.docstatus === 0 &&
			!frm.is_new() &&
			frm.doc.inspection_basis === "Each Quantity" &&
			!frm.doc.reading_bundle
		) {
			frm.add_custom_button(__("Create Reading Bundle"), () => {
				frappe.call({
					method: "erpnext.stock.doctype.quality_inspection.quality_inspection.make_reading_bundle",
					args: { quality_inspection: frm.doc.name },
					freeze: true,
					callback: (r) => {
						const bundle = frappe.model.sync(r.message)[0];
						frappe.set_route("Form", bundle.doctype, bundle.name);
					},
				});
			});
		}
	},

	toggle_batch_and_serial_fields(frm) {
		// only show batch / serial for items that are actually tracked that way
		if (!frm.doc.item_code) {
			frm.toggle_display(["batch_no", "serial_no"], false);
			return;
		}

		frappe.db.get_value("Item", frm.doc.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
			frm.toggle_display("batch_no", cint(r.message?.has_batch_no));
			// Each Quantity inspections record serials per unit in the bundle
			frm.toggle_display(
				"serial_no",
				cint(r.message?.has_serial_no) && frm.doc.inspection_basis !== "Each Quantity"
			);
		});
	},

	reference_name: function (frm) {
		// the lot dictates how it is inspected; the server re-derives on save
		if (frm.doc.reference_type === "Quality Control Lot" && frm.doc.reference_name) {
			frappe.db
				.get_value("Quality Control Lot", frm.doc.reference_name, "inspection_basis")
				.then((r) => {
					frm.set_value("inspection_basis", r.message?.inspection_basis || "Sample");
				});
		} else {
			frm.set_value("inspection_basis", "Sample");
		}
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

	quality_inspection_template: function (frm) {
		if (frm.doc.quality_inspection_template) {
			return frm.call({
				method: "get_item_specification_details",
				doc: frm.doc,
				callback: function () {
					refresh_field("readings");
				},
			});
		}
	},
});
