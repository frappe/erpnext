const ISLAND = "erpnext.page.plant-builder";

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
		const design = {
			...this.frm.doc,
			items: [],
			operations: this.get_rows("operations"),
			materials: this.get_rows("materials"),
		};
		return {
			design: JSON.parse(JSON.stringify(design)),
			readOnly: !this.view.is_editable(),
			onChange: (rows) => this.set_rows(rows),
			onUpdate: (values) => this.frm.set_value(values),
		};
	}

	get_rows(table) {
		return (this.frm.doc[table] || []).filter(
			(row) => !cint(row.bom_node_id) && !(table === "materials" && row.from_operation_id)
		);
	}

	set_rows(rows) {
		for (const table of ["operations", "materials"]) {
			const managed = this.get_rows(table);
			const by_name = Object.fromEntries(managed.map((row) => [row.name, row]));
			const others = (this.frm.doc[table] || []).filter((row) => !managed.includes(row));
			const ordered = rows[table].map((values) => {
				const row = by_name[values.name] || this.frm.add_child(table);
				return Object.assign(row, { ...values, name: row.name });
			});
			this.frm.doc[table] = [...others, ...ordered];
			this.frm.doc[table].forEach((row, index) => (row.idx = index + 1));
		}
		this.frm.dirty();
		this.view.render_summary(true);
	}
}
