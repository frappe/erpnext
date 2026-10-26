const ROW =
	"display:flex;align-items:center;gap:8px;min-height:36px;padding:0 12px;border-top:1px solid var(--border-color);";
const CARD = "border:1px solid var(--border-color);border-radius:var(--border-radius-md);overflow:hidden;";

export function render_bom_bar(editor, $bar) {
	const node_ids = editor.get_bom_node_ids();
	$bar.append(
		frappe.ui.tab_buttons({
			label: __("BOM"),
			options: node_ids.map((node_id) => ({
				label: editor.view.get_node_label(node_id),
				value: String(node_id),
				title: node_id ? __("Sub-Assembly BOM") : __("Finished Good BOM"),
			})),
			value: String(editor.bom_node_id),
			on_change: (value) => {
				editor.view.state.bom_node_id = cint(value);
				editor.view.render();
			},
		})
	);

	if (!editor.editable) return;
	if (editor.view.state.adding_bom) {
		$bar.append(
			`<span class="design-link-cell" data-link="sub_assembly" style="width:220px;display:flex;min-width:0;"></span>`
		);
	} else {
		$bar.append(
			frappe.ui.button.html({
				icon: "package-plus",
				variant: "ghost",
				tooltip: __("Add Sub-Assembly BOM"),
				attrs: { "data-action": "add-bom" },
			})
		);
	}
}

export function get_unused_tray(editor) {
	const parts = editor.view.get_unused_parts();
	if (!parts.length) return "";

	const operations = editor.get_operations();
	const options = operations.length
		? operations.map(
				(row, index) =>
					`<option value="${row.operation_id}">${__("Step {0}", [
						index + 1,
					])} · ${frappe.utils.escape_html(row.operation || "")}</option>`
		  )
		: [`<option value="0">${__("Raw Materials")}</option>`];
	const rows = parts.map((part) => {
		const assign = editor.editable
			? `<select class="form-control input-sm" data-field="assign" data-node-id="${part.node_id}"
				style="width:160px;"><option value="">${__("Add to")}</option>${options.join("")}</select>`
			: "";
		return `<div style="${ROW}">
			<span style="flex:1;min-width:0;display:flex;gap:8px;">
				<span class="ellipsis" title="${frappe.utils.escape_html(part.part_number)}">
				${frappe.utils.escape_html(part.part_name || part.part_number)}</span>
				</span>
			${assign}<span style="width:56px;text-align:right;">${flt(part.qty)}</span></div>`;
	});

	return `<div style="${CARD}margin-top:var(--margin-md);">
		<div style="${ROW}border-top:0;height:40px;background:var(--subtle-fg);font-weight:600;">
			${__("Parts Not Used in Any BOM")}
			${badge(String(parts.length), "red")}</div>${rows.join("")}</div>`;
}

function badge(label, theme) {
	return frappe.ui.badge.html({ label, theme, size: "sm" });
}
