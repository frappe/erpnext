const ROW =
	"display:flex;align-items:center;gap:8px;min-height:36px;padding:0 12px;border-top:1px solid var(--border-color);";
const INPUT = "height:28px;background-color:var(--fg-color);border:1px solid var(--border-color);";
const CARD = "border:1px solid var(--border-color);border-radius:var(--border-radius-md);overflow:hidden;";

export function render_bom_bar(editor, $bar) {
	const node_ids = [...new Set([...editor.view.get_bom_node_ids(), ...editor.view.state.extra_bom_nodes])];
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
		const options = (editor.frm.doc.items || [])
			.filter((part) => part.is_expandable && !node_ids.includes(part.node_id))
			.map(
				(part) =>
					`<option value="${part.node_id}">${escape(
						editor.view.get_node_label(part.node_id)
					)}</option>`
			);
		$bar.append(`<select class="form-control input-sm" data-field="new-bom" style="${INPUT}width:220px;">
			<option value="">${__("Choose a sub-assembly")}</option>${options.join("")}</select>`);
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
				style="${INPUT}width:160px;"><option value="">${__("Add to")}</option>${options.join("")}</select>`
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

function escape(value) {
	return frappe.utils.escape_html(value);
}

function badge(label, theme) {
	return frappe.ui.badge.html({ label, theme, size: "sm" });
}
