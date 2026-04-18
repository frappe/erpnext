// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;

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

		// Serial No based on item_code
		frm.set_query("item_serial_no", function () {
			let filters = {};
			if (frm.doc.item_code) {
				filters = {
					item_code: frm.doc.item_code,
				};
			}
			return { filters: filters };
		});

		// item code based on GRN/DN
		frm.set_query("item_code", function (doc) {
			let doctype = doc.reference_type;

			if (doc.reference_type !== "Job Card") {
				doctype =
					doc.reference_type == "Stock Entry" ? "Stock Entry Detail" : doc.reference_type + " Item";
			}

			if (doc.reference_type && doc.reference_name) {
				let filters = {
					from: doctype,
					inspection_type: doc.inspection_type,
				};

				if (doc.reference_type == doctype) filters["reference_name"] = doc.reference_name;
				else filters["parent"] = doc.reference_name;

				return {
					query: "erpnext.stock.doctype.quality_inspection.quality_inspection.item_query",
					filters: filters,
				};
			}
		});
	},

	refresh: function (frm) {
		// Ignore cancellation of reference doctype on cancel all.
		frm.ignore_doctypes_on_cancel_all = [frm.doc.reference_type, "Serial and Batch Bundle"];
		if (frm.doc.inspection_type) {
			frm.trigger("inspection_type");
		}
	},

	item_code: function (frm) {
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
	inspection_type: function (frm) {
		// Clear the reference_type when inspection_type changes
		frm.set_value("reference_type", "");
		frm.set_value("reference_name", "");

		if (frm.doc.inspection_type) {
			// Call the whitelisted Python function
			frappe.call({
				method: "erpnext.stock.doctype.quality_inspection.quality_inspection.get_reference_type_options",
				args: {
					inspection_type: frm.doc.inspection_type,
				},
				callback: function (r) {
					if (r.message) {
						// Set the dropdown options dynamically
						frm.set_df_property("reference_type", "options", ["", ...r.message].join("\n"));
						frm.refresh_field("reference_type");
					}
				},
			});
		}
	},
});
