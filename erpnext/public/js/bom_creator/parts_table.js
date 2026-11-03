import { get_item_link_html } from "./link_field";

const ROW =
	"display:flex;align-items:center;gap:8px;height:36px;padding:0 12px;border-top:1px solid var(--border-color);";
const CHANGE_COLORS = { Added: "green", "Quantity Changed": "orange" };

export class PartsTable {
	constructor(view) {
		this.view = view;
		view.wrapper.on("click", ".design-parts [data-node-id]", (event) => {
			if ($(event.target).closest("input").length) return;
			this.view.highlight_nodes([cint($(event.currentTarget).attr("data-node-id"))]);
		});
	}

	get frm() {
		return this.view.frm;
	}

	render(container) {
		this.editable = this.view.is_editable();
		this.index_usage();
		const header = `<div class="text-muted small" style="${ROW}border-top:0;height:32px;background:var(--subtle-fg);">
			<span style="flex:1;">${__("Part")}</span><span style="width:130px;">${__("Item")}</span>
			<span style="width:140px;">${__("Used In")}</span>
			<span style="width:48px;text-align:right;">${__("Quantity")}</span></div>`;
		const rows = [];
		this.add_rows(0, 0, rows);
		container.html(`<div class="design-parts" style="border:1px solid var(--border-color);
			border-radius:var(--radius-md);overflow:hidden;">${header}${rows.join("")}</div>`);

		this.mark_selected(this.view.selected_node_ids || new Set());
	}

	add_rows(parent_node_id, depth, rows) {
		for (const part of this.view.children[parent_node_id] || []) {
			rows.push(this.get_row_html(part, depth));
			this.add_rows(part.node_id, depth + 1, rows);
		}
	}

	get_row_html(part, depth) {
		const name = frappe.utils.escape_html(part.part_name || part.part_number);
		const color = CHANGE_COLORS[part.change_type];
		const change = color
			? `<span title="${__(part.change_type)}" style="flex:none;width:6px;height:6px;border-radius:50%;
				background:var(--${color}-500);"></span>`
			: "";

		return `<div data-node-id="${part.node_id}" style="${ROW}cursor:pointer;">
			<span style="flex:1;min-width:0;display:flex;align-items:center;gap:8px;padding-left:${depth * 18}px;">
				${change}<span class="ellipsis ${part.is_expandable ? "bold" : ""}" title="${frappe.utils.escape_html(
			part.part_number
		)}">${name}</span>
				</span>
			<span style="width:130px;display:flex;min-width:0;">${this.get_item_html(part)}</span>
			<span style="width:140px;display:flex;min-width:0;">${this.get_usage_html(part)}</span>
			<span style="width:48px;text-align:right;">${flt(part.qty)}</span></div>`;
	}

	get_item_html(part) {
		if (this.editable) return get_item_link_html(part.node_id, part.item_code);

		if (part.item_code) {
			return `<span class="ellipsis">${frappe.utils.escape_html(part.item_code)}</span>`;
		}

		return this.frm.doc.docstatus === 1
			? frappe.ui.badge.html({ label: __("Not Mapped"), theme: "red", size: "sm" })
			: "";
	}

	index_usage() {
		this.used = this.view.get_used_node_ids();
		this.bom_nodes = new Set(this.view.get_bom_node_ids());
		this.outputs = new Map();
		this.materials = new Map();
		for (const row of this.frm.doc.operations || []) {
			if (row.output_node_id) this.outputs.set(cint(row.output_node_id), row);
		}
		for (const row of this.frm.doc.materials || []) {
			if (row.part_node_id) this.materials.set(cint(row.part_node_id), row);
		}
	}

	get_usage_html(part) {
		const pill = (theme, text) =>
			frappe.ui.badge.html({ label: text, theme, size: "sm", title: text, css_class: "ellipsis" });
		const muted = (text) => `<span class="text-muted small ellipsis">${text}</span>`;

		if (this.bom_nodes.has(part.node_id)) return pill("blue", __("Own BOM"));
		if (this.outputs.has(part.node_id)) {
			return pill(
				"purple",
				__("Output of {0}", [this.outputs.get(part.node_id).operation || __("Operation")])
			);
		}
		if (this.materials.has(part.node_id))
			return pill("gray", this.get_material_usage(this.materials.get(part.node_id)));
		if (this.view.is_inside_used_part(part, this.used)) return muted(__("Inside a used assembly"));
		if (part.is_expandable) return muted(__("Parts used directly"));
		return pill("red", __("Not Used"));
	}

	get_material_usage(row) {
		const bom = this.view.get_node_label(cint(row.bom_node_id));
		const operation = (this.frm.doc.operations || []).find(
			(operation) => cint(operation.operation_id) === cint(row.operation_id)
		);
		if (!cint(row.bom_node_id)) return operation?.operation || __("Raw Material");
		return operation?.operation ? `${bom} · ${operation.operation}` : bom;
	}

	mark_selected(node_ids) {
		this.view.wrapper.find(".design-parts [data-node-id]").each((_, row) => {
			const selected = node_ids.has(cint($(row).attr("data-node-id")));
			$(row).css("background", selected ? "var(--subtle-accent)" : "");
		});
	}
}
