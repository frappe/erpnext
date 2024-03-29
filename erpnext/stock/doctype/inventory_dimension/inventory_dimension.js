// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Inventory Dimension", {
	setup(frm) {
		frm.trigger("set_query_on_fields");
	},

	set_query_on_fields(frm) {
		frm.set_query("reference_document", () => {
			let invalid_doctypes = frappe.model.core_doctypes_list;
			invalid_doctypes.push(
				"Batch",
				"Serial No",
				"Warehouse",
				"Item",
				"Inventory Dimension",
				"Accounting Dimension",
				"Accounting Dimension Filter"
			);

			return {
				filters: {
					istable: 0,
					issingle: 0,
					name: ["not in", invalid_doctypes],
				},
			};
		});

		frm.set_query("document_type", () => {
			return {
				query: "erpnext.stock.doctype.inventory_dimension.inventory_dimension.get_inventory_documents",
			};
		});
	},

	onload(frm) {
		frm.trigger("render_traget_field");
		frm.trigger("set_parent_fields");
	},

	refresh(frm) {
		if (
			frm.doc.__onload &&
			frm.doc.__onload.has_stock_ledger &&
			frm.doc.__onload.has_stock_ledger.length
		) {
			let allow_to_edit_fields = [
				"disabled",
				"fetch_from_parent",
				"type_of_transaction",
				"condition",
				"mandatory_depends_on",
				"validate_negative_stock",
			];

			frm.fields.forEach((field) => {
				if (!in_list(allow_to_edit_fields, field.df.fieldname)) {
					frm.set_df_property(field.df.fieldname, "read_only", "1");
				}
			});
		}

		if (!frm.is_new()) {
			frm.add_custom_button(__("Delete Dimension"), () => {
				frm.trigger("delete_dimension");
			});
		}
	},

	document_type(frm) {
		frm.trigger("set_parent_fields");
	},

	set_parent_fields(frm) {
		if (frm.doc.apply_to_all_doctypes) {
			frm.set_df_property("fetch_from_parent", "options", frm.doc.reference_document);
		} else if (frm.doc.document_type && frm.doc.istable) {
			frappe.call({
				method: "erpnext.stock.doctype.inventory_dimension.inventory_dimension.get_parent_fields",
				args: {
					child_doctype: frm.doc.document_type,
					dimension_name: frm.doc.reference_document,
				},
				callback: (r) => {
					if (r.message && r.message.length) {
						frm.set_df_property("fetch_from_parent", "options", [""].concat(r.message));
					} else {
						frm.set_df_property("fetch_from_parent", "hidden", 1);
					}
				},
			});
		}
	},

	delete_dimension(frm) {
		let msg = `
			Custom fields related to this dimension will be deleted on deletion of dimension.
			<br> Do you want to delete {0} dimension?
		`;

		frappe.confirm(__(msg, [frm.doc.name.bold()]), () => {
			frappe.call({
				method: "erpnext.stock.doctype.inventory_dimension.inventory_dimension.delete_dimension",
				args: {
					dimension: frm.doc.name,
				},
				callback: function () {
					frappe.set_route("List", "Inventory Dimension");
				},
			});
		});
	},
});
