const ISLAND = "erpnext.page.plant-builder";
const OPERATION_FIELDS = [
	"operation_id",
	"operation",
	"workstation",
	"workstation_type",
	"time_in_mins",
	"output_item",
	"yield_percentage",
	"sequence_id",
];
const MATERIAL_FIELDS = ["operation_id", "item_code", "qty", "is_balance_item", "storage"];
const HEADER_FIELDS = ["name", "item_code", "qty", "company", "raw_material_warehouse", "formula_tolerance"];

const pick = (row, fields) => Object.fromEntries(fields.map((field) => [field, row[field] ?? null]));

export class ProcessView {
	constructor(view) {
		this.view = view;
	}

	get frm() {
		return this.view.frm;
	}

	render(container) {
		if (this.target?.isConnected) {
			this.island.update(this.get_props());
			return;
		}

		this.unmount();
		this.target = $(`<div class="design-process"></div>`).appendTo(container.empty()).get(0);
		this.island = frappe.ui.mount_island(ISLAND, this.target, this.get_props());
	}

	unmount() {
		this.island?.unmount();
		this.island = null;
		this.target = null;
	}

	get_props() {
		const doc = this.frm.doc;
		return {
			design: {
				...pick(doc, HEADER_FIELDS),
				operations: this.get_rows("operations").map((row) => pick(row, OPERATION_FIELDS)),
				materials: this.get_rows("materials").map((row) => pick(row, MATERIAL_FIELDS)),
			},
			readOnly: !this.view.is_editable(),
			onChange: (rows) => this.set_rows(rows),
		};
	}

	get_rows(table) {
		return (this.frm.doc[table] || []).filter(
			(row) => !cint(row.bom_node_id) && !(table === "materials" && row.from_operation_id)
		);
	}

	set_rows({ operations, materials }) {
		for (const [table, rows] of [
			["operations", operations],
			["materials", materials],
		]) {
			const kept = (this.frm.doc[table] || []).filter((row) => cint(row.bom_node_id));
			this.frm.doc[table] = kept;
			rows.forEach((values) => this.frm.add_child(table, values));
		}
		this.frm.dirty();
	}
}
