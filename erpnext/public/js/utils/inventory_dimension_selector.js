// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

/**
 * Inventory Dimension capture dialog (mirrors the Serial / Batch selector).
 *
 * Lets a stock row split its quantity across inventory-dimension combinations and stores the
 * result in an Inventory Dimension Bundle, linked back to the row via `inventory_dimension_bundle`
 * (or `rejected_inventory_dimension_bundle` for the rejected qty on purchase documents).
 *
 * Each applicable dimension renders one Link column (to its reference document); a `qty` column
 * captures the split, reconciled against the row quantity.
 */
erpnext.show_inventory_dimension_selector = function (frm, item_row, opts = {}) {
	const child_doctype = item_row.doctype;

	frappe.call({
		method: "erpnext.stock.doctype.inventory_dimension_bundle.inventory_dimension_bundle.get_dimensions_for_selector",
		args: { child_doctype: child_doctype },
		callback: function (r) {
			const dimensions = r.message || [];
			if (!dimensions.length) {
				frappe.msgprint(__("No inventory dimensions apply to {0}.", [child_doctype]));
				return;
			}
			new erpnext.InventoryDimensionSelector(frm, item_row, dimensions, opts);
		},
		error: function () {
			frappe.msgprint(__("Could not load inventory dimensions for {0}.", [child_doctype]));
		},
	});
};

erpnext.InventoryDimensionSelector = class InventoryDimensionSelector {
	constructor(frm, item_row, dimensions, opts = {}) {
		this.frm = frm;
		this.item_row = item_row;
		this.dimensions = dimensions;
		// `opts` lets the rejected-qty button reuse the same dialog: a different qty field,
		// warehouse field and target bundle link on the row.
		this.qty_field = opts.qty_field || "qty";
		this.warehouse_field = opts.warehouse_field || "warehouse";
		this.bundle_field = opts.bundle_field || "inventory_dimension_bundle";
		this.is_rejected = !!opts.is_rejected;
		this.make_dialog();
	}

	get_warehouse() {
		return (
			this.item_row[this.warehouse_field] ||
			this.item_row.warehouse ||
			this.item_row.t_warehouse ||
			this.item_row.s_warehouse
		);
	}

	build_entry_fields() {
		const fields = this.dimensions.map((dim) => ({
			fieldname: dim.fieldname,
			label: dim.dimension,
			fieldtype: "Link",
			options: dim.reference_document,
			in_list_view: 1,
			reqd: dim.reqd ? 1 : 0,
		}));

		fields.push({
			fieldname: "qty",
			label: __("Qty"),
			fieldtype: "Float",
			in_list_view: 1,
			reqd: 1,
		});

		return fields;
	}

	make_dialog() {
		const me = this;
		const title = this.is_rejected
			? __("Inventory Dimensions for {0} (Rejected Qty)", [this.item_row.item_code])
			: __("Inventory Dimensions for {0}", [this.item_row.item_code]);

		this.dialog = new frappe.ui.Dialog({
			title: title,
			size: "large",
			fields: [
				{
					fieldname: "entries",
					fieldtype: "Table",
					label: __("Dimensions"),
					cannot_add_rows: false,
					in_place_edit: true,
					data: [],
					fields: this.build_entry_fields(),
				},
			],
			primary_action_label: __("Save"),
			primary_action: () => me.create_bundle(),
		});

		this.dialog.show();
		this.load_existing_entries();
	}

	load_existing_entries() {
		const me = this;
		const bundle = this.item_row[this.bundle_field];
		if (!bundle) return;

		frappe.call({
			method: "erpnext.stock.doctype.inventory_dimension_bundle.inventory_dimension_bundle.get_inventory_dimension_bundle_entries",
			args: { bundle: bundle },
			callback: function (r) {
				if (r.message && r.message.length) {
					me.dialog.fields_dict.entries.df.data = r.message;
					me.dialog.fields_dict.entries.grid.refresh();
				}
			},
		});
	}

	create_bundle() {
		const me = this;
		const entries = this.dialog.get_value("entries") || [];

		// The captured dimension qty is authoritative: push the total back onto the row's qty field
		// (e.g. a PR item qty of 5 becomes 10 if the user split 10 across dimensions).
		const total = entries.reduce((sum, row) => sum + flt(row.qty), 0);

		frappe.call({
			method: "erpnext.stock.doctype.inventory_dimension_bundle.inventory_dimension_bundle.create_inventory_dimension_bundle",
			args: {
				company: this.frm.doc.company,
				item_code: this.item_row.item_code,
				warehouse: this.get_warehouse(),
				type_of_transaction: null,
				voucher_type: this.frm.doc.doctype,
				bundle: this.item_row[this.bundle_field],
				entries: entries,
			},
			callback: function (r) {
				if (r.message) {
					frappe.model.set_value(me.item_row.doctype, me.item_row.name, me.bundle_field, r.message);
					frappe.model
						.set_value(me.item_row.doctype, me.item_row.name, me.qty_field, total)
						.then(() => {
							me.dialog.hide();
							// Persist the link on the transaction so it survives a page refresh
							// without the user manually saving.
							me.frm.save();
						});
				}
			},
			error: function () {
				frappe.msgprint(
					__("Could not save the inventory dimensions. Please review the entries and try again.")
				);
			},
		});
	}
};

// Wire the grid "Inventory Dimension" button (and the rejected-qty variant on purchase docs) for
// every child doctype that carries the bundle field. Mirrors the Serial / Batch grid button.
erpnext.inventory_dimension_child_doctypes = [
	"Purchase Receipt Item",
	"Purchase Invoice Item",
	"Sales Invoice Item",
	"POS Invoice Item",
	"Delivery Note Item",
	"Stock Entry Detail",
	"Stock Reconciliation Item",
	"Subcontracting Receipt Item",
	"Subcontracting Receipt Supplied Item",
	"Packed Item",
	"Pick List Item",
	"Maintenance Schedule Item",
	"Installation Note Item",
	"Asset Capitalization Stock Item",
	"Asset Repair Consumed Item",
];

erpnext.inventory_dimension_rejected_doctypes = [
	"Purchase Receipt Item",
	"Purchase Invoice Item",
	"Subcontracting Receipt Item",
];

erpnext.inventory_dimension_child_doctypes.forEach((child_doctype) => {
	frappe.ui.form.on(child_doctype, {
		add_inventory_dimension(frm, cdt, cdn) {
			erpnext.show_inventory_dimension_selector(frm, locals[cdt][cdn]);
		},
	});
});

erpnext.inventory_dimension_rejected_doctypes.forEach((child_doctype) => {
	frappe.ui.form.on(child_doctype, {
		add_inventory_dimension_for_rejected_qty(frm, cdt, cdn) {
			erpnext.show_inventory_dimension_selector(frm, locals[cdt][cdn], {
				is_rejected: true,
				qty_field: "rejected_qty",
				warehouse_field: "rejected_warehouse",
				bundle_field: "rejected_inventory_dimension_bundle",
			});
		},
	});
});

// Inventory Dimensions are gated behind a Stock Settings switch. When disabled, hide every
// dimension field/button on the child grids so the feature is invisible across all doctypes.
erpnext.inventory_dimension_grid_fields = [
	"inventory_dimension_section",
	"column_break_inv_dim",
	"add_inventory_dimension",
	"inventory_dimension_bundle",
	"add_inventory_dimension_for_rejected_qty",
	"rejected_inventory_dimension_bundle",
];

erpnext.is_inventory_dimension_enabled = function () {
	// Cache the lookup so we don't refetch on every form refresh. A whitelisted method is used
	// (instead of frappe.db.get_single_value) so users without read access to Stock Settings can
	// still resolve the flag.
	if (!erpnext._inventory_dimension_enabled) {
		erpnext._inventory_dimension_enabled = frappe
			.xcall(
				"erpnext.stock.doctype.inventory_dimension.inventory_dimension.inventory_dimension_enabled"
			)
			.then((enabled) => !!enabled);
	}
	return erpnext._inventory_dimension_enabled;
};

erpnext.toggle_inventory_dimension_fields = function (frm) {
	erpnext.is_inventory_dimension_enabled().then((enabled) => {
		const hidden = enabled ? 0 : 1;
		Object.values(frm.fields_dict || {}).forEach((field) => {
			const grid = field.grid;
			if (!grid || !erpnext.inventory_dimension_child_doctypes.includes(grid.doctype)) return;

			erpnext.inventory_dimension_grid_fields.forEach((fieldname) => {
				if (grid.fields_map && grid.fields_map[fieldname]) {
					grid.update_docfield_property(fieldname, "hidden", hidden);
				}
			});
		});
		frm.refresh_fields();
	});
};

// Parent doctypes that carry one of the inventory-dimension child tables.
erpnext.inventory_dimension_parent_doctypes = [
	"Purchase Receipt",
	"Purchase Invoice",
	"Sales Invoice",
	"POS Invoice",
	"Delivery Note",
	"Stock Entry",
	"Stock Reconciliation",
	"Subcontracting Receipt",
	"Pick List",
	"Maintenance Schedule",
	"Installation Note",
	"Asset Capitalization",
	"Asset Repair",
];

erpnext.inventory_dimension_parent_doctypes.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			erpnext.toggle_inventory_dimension_fields(frm);
		},
	});
});
