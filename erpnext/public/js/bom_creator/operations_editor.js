import { open_link_field } from "./link_field";
import { get_unused_tray, render_bom_bar } from "./operation_panels";

const ROW =
	"display:flex;align-items:center;gap:8px;min-height:36px;padding:0 12px;border-top:1px solid var(--border-color);";
const CARD = "border:1px solid var(--border-color);border-radius:var(--border-radius-md);overflow:hidden;";

export class OperationsEditor {
	constructor(view) {
		this.view = view;
		view.wrapper.on("click", ".design-operations [data-action]", (event) =>
			this.handle_action($(event.currentTarget))
		);
		view.wrapper.on("change", ".design-operations [data-field]", (event) =>
			this.handle_change($(event.currentTarget))
		);
		view.wrapper.on("click", ".design-step", (event) => {
			if ($(event.target).closest("input, select, button, [data-action]").length) return;
			this.select_step(cint($(event.currentTarget).attr("data-operation-id")));
		});
	}

	get frm() {
		return this.view.frm;
	}

	get bom_node_id() {
		return this.view.state.bom_node_id;
	}

	get produces_items() {
		return Boolean(this.frm.doc.track_semi_finished_goods);
	}

	get bom_quantity() {
		return this.bom_node_id ? 1 : flt(this.frm.doc.qty) || 1;
	}

	get_bom_value(quantity) {
		return flt(flt(quantity) * this.bom_quantity, precision("qty", this.frm.doc));
	}

	get_operations() {
		return (this.frm.doc.operations || []).filter((row) => cint(row.bom_node_id) === this.bom_node_id);
	}

	get_materials(operation_id) {
		return (this.frm.doc.materials || []).filter(
			(row) => cint(row.bom_node_id) === this.bom_node_id && cint(row.operation_id) === operation_id
		);
	}

	render(container) {
		this.editable = this.view.is_editable();
		const operations = this.get_operations();
		const html = [
			`<div class="design-bom-bar" style="display:flex;flex-wrap:wrap;align-items:center;
			gap:var(--margin-sm);margin-bottom:var(--margin-sm);"></div>`,
		];
		const loose = this.get_materials(0);
		if (!operations.length || loose.length) html.push(this.get_card(null, loose, 0, operations.length));

		operations.forEach((operation, index) => {
			const materials = this.get_materials(cint(operation.operation_id));
			html.push(this.get_card(operation, materials, index, operations.length));
			if (index < operations.length - 1)
				html.push(this.get_connector(operation, operations[index + 1]));
		});

		if (this.editable) {
			const add = frappe.ui.button.html({
				label: __("Add Operation"),
				icon: "plus",
				attrs: { "data-action": "add-operation" },
			});
			html.push(`<div style="margin-top:var(--margin-sm);">${add}</div>`);
		}

		html.push(get_unused_tray(this));
		container.html(`<div class="design-operations">${html.join("")}</div>`);
		render_bom_bar(this, container.find(".design-bom-bar"));
		if (this.editable) this.mount_links(container);
	}

	get_card(operation, materials, index, count) {
		const operation_id = operation ? cint(operation.operation_id) : 0;
		const title = count ? __("Raw Materials Not Linked to an Operation") : __("Raw Materials");
		const header = operation
			? this.get_card_header(operation, index)
			: `<div style="${ROW}border-top:0;background:var(--subtle-fg);height:44px;"><span class="bold">${title}</span></div>`;
		const label = operation
			? `<div class="text-muted small" style="padding:8px 12px 4px;">${__("Raw Materials")}</div>`
			: "";
		const rows = materials.map((row) => this.get_material_row(row)).join("");
		const add = this.editable ? this.get_add_row(operation_id) : "";
		const is_last = operation ? index === count - 1 : !count;
		const output =
			is_last || (operation && this.produces_items) ? this.get_output_row(operation, is_last) : "";

		return `<div class="design-step" data-operation-id="${operation_id}" style="${CARD}">
			${header}${label}${rows}${add}${output}</div>`;
	}

	get_card_header(operation, index) {
		const field = (name, value, width) =>
			this.editable
				? `<span class="design-link-cell" data-link="${name}" data-operation="${operation.name}"
					style="${width}display:flex;min-width:0;"></span>`
				: `<span class="ellipsis" style="${width}">${frappe.utils.escape_html(value || "")}</span>`;
		const time = this.editable
			? `<input class="form-control input-sm" data-field="time_in_mins" data-operation="${
					operation.name
			  }"
				value="${flt(operation.time_in_mins) || ""}" style="width:52px;text-align:right;">`
			: `<span style="width:52px;text-align:right;">${flt(operation.time_in_mins)}</span>`;
		const remove = this.editable
			? remove_button("remove-operation", { "data-operation": operation.name }, __("Remove Operation"))
			: "";

		return `<div style="${ROW}border-top:0;background:var(--subtle-fg);height:44px;">
			<span style="flex:none;width:24px;height:24px;border-radius:12px;background:var(--gray-900);
				color:var(--white);display:flex;align-items:center;justify-content:center;font-size:12px;">${index + 1}</span>
			${field("operation", operation.operation, "width:170px;font-weight:600;")}
			${field("workstation_type", operation.workstation_type, "flex:1;")}
			${time}<span class="text-muted small">${__("min")}</span>${remove}</div>`;
	}

	get_material_row(row) {
		const value = this.get_bom_value(row.qty);
		const quantity = this.editable
			? `<input class="form-control input-sm" data-field="quantity" data-material="${row.name}"
				value="${value}" style="width:64px;text-align:right;margin-left:auto;">`
			: `<span style="display:block;text-align:right;">${value}</span>`;
		const remove = this.editable
			? remove_button("remove-material", { "data-material": row.name }, __("Remove"))
			: "";
		const item = this.get_material_item(row);
		const item_html = item
			? `<span class="ellipsis" title="${frappe.utils.escape_html(item)}">${frappe.utils.escape_html(
					item
			  )}</span>`
			: this.get_unmapped_html(row);

		return `<div style="${ROW}">
			<span style="flex:1;min-width:0;display:flex;align-items:center;gap:8px;">${this.get_material_label(
				row
			)}</span>
			<span style="width:120px;display:flex;min-width:0;">${item_html}</span>
			<span style="width:72px;">${quantity}</span>
			<span class="text-muted ellipsis" style="width:36px;">${escape(this.get_material_uom(row))}</span>
			<span style="width:28px;">${remove}</span></div>`;
	}

	get_unmapped_html(row) {
		if (this.frm.doc.docstatus === 1) {
			return badge(__("Not Mapped"), "red");
		}

		const part = row.part_node_id ? this.view.get_part(row.part_node_id) : null;
		return `<span class="text-muted ellipsis">${frappe.utils.escape_html(
			part?.part_number || ""
		)}</span>`;
	}

	get_material_label(row) {
		if (row.from_operation_id) {
			const source = this.get_operation(row.from_operation_id);
			return `${badge(__("Step {0} Output", [this.get_step_no(source)]), "green")}
				<span class="ellipsis">${frappe.utils.escape_html(this.get_output_label(source))}</span>`;
		}

		if (row.part_node_id) {
			const part = this.view.get_part(row.part_node_id) || {};
			return `<span class="ellipsis" title="${frappe.utils.escape_html(part.part_number || "")}">
				${frappe.utils.escape_html(part.part_name || part.part_number || "")}</span>`;
		}

		return `<span class="ellipsis">${frappe.utils.escape_html(row.item_code || "")}</span>`;
	}

	get_material_item(row) {
		if (row.from_operation_id) return this.get_output_item(this.get_operation(row.from_operation_id));
		if (row.part_node_id) return this.view.get_node_item(row.part_node_id);
		return row.item_code;
	}

	get_material_uom(row) {
		return row.uom || (row.part_node_id && this.view.get_part(row.part_node_id)?.uom) || "";
	}

	get_add_row(operation_id) {
		return `<div style="${ROW}">
			<span class="design-link-cell" data-link="material" data-operation-id="${operation_id}"
				style="flex:1;min-width:0;display:flex;"></span>
			${this.get_earlier_output_buttons(operation_id)}</div>`;
	}

	get_earlier_output_buttons(operation_id) {
		if (!this.produces_items || !operation_id) return "";

		const operations = this.get_operations();
		const position = operations.findIndex((row) => cint(row.operation_id) === operation_id);
		const used = new Set(this.get_materials(operation_id).map((row) => cint(row.from_operation_id)));
		return operations
			.slice(0, Math.max(position, 0))
			.map((row, index) => ({ row, step: index + 1 }))
			.filter(({ row }) => !used.has(cint(row.operation_id)))
			.map(({ row, step }) =>
				frappe.ui.button.html({
					label: __("Step {0} Output", [step]),
					icon: "plus",
					size: "xs",
					title: this.get_output_label(row),
					attrs: {
						"data-action": "add-output",
						"data-operation-id": operation_id,
						"data-from": row.operation_id,
					},
				})
			)
			.join("");
	}

	get_output_row(operation, is_last) {
		let label;
		if (is_last) {
			const kind = this.bom_node_id ? __("Sub-Assembly") : __("Finished Good");
			label = `<span class="bold ellipsis">${frappe.utils.escape_html(
				this.view.get_node_label(this.bom_node_id)
			)}</span>
				${badge(kind, "blue")}`;
		} else if (this.editable) {
			label = `<span class="design-link-cell" data-link="output" data-operation="${operation.name}"
				style="flex:1;max-width:280px;display:flex;min-width:0;"></span>
				${badge(__("Semi-Finished"), "violet")}`;
		} else {
			label = `<span class="ellipsis">${frappe.utils.escape_html(
				this.get_output_label(operation)
			)}</span>`;
		}

		const item = is_last ? this.view.get_node_item(this.bom_node_id) : this.get_output_item(operation);
		const node_id = is_last ? this.bom_node_id : cint(operation.output_node_id);
		const part = node_id ? this.view.get_part(node_id) : null;
		const uom = (part ? part.uom : is_last && this.frm.doc.uom) || "";
		const heading = __("Output Item");
		return `<div style="${ROW}background:var(--subtle-accent);min-height:42px;">
			<span class="bold" style="flex:none;width:92px;white-space:nowrap;color:var(--text-color);">${heading}</span>
			<span style="flex:1;min-width:0;display:flex;align-items:center;gap:8px;">${label}</span>
			<span class="ellipsis" style="width:120px;">${escape(item || "")}</span>
			<span style="width:72px;">${this.get_output_quantity(operation, is_last)}</span>
			<span class="text-muted ellipsis" style="width:36px;">${escape(uom)}</span>
			<span style="width:28px;"></span></div>`;
	}

	get_output_quantity(operation, is_last) {
		if (is_last) {
			const title = this.bom_node_id
				? __("A sub-assembly BOM is made for one unit.")
				: __("Change the Finished Good Quantity to make more.");
			return `<span title="${title}" style="display:block;text-align:right;">${this.bom_quantity}</span>`;
		}

		const quantity = this.get_bom_value(flt(operation.output_quantity) || 1);
		return this.editable
			? `<input class="form-control input-sm" data-field="output_quantity" data-operation="${operation.name}"
				value="${quantity}" style="width:64px;text-align:right;margin-left:auto;">`
			: `<span style="display:block;text-align:right;">${quantity}</span>`;
	}

	get_connector(operation, next) {
		const used = (this.frm.doc.materials || []).some(
			(row) => cint(row.from_operation_id) === cint(operation.operation_id)
		);
		const text =
			this.produces_items && used
				? __("{0} is used in a later step", [
						frappe.utils.escape_html(this.get_output_label(operation)),
				  ])
				: __("then");
		return `<div class="text-muted small" style="display:flex;align-items:center;gap:12px;height:28px;padding-left:22px;">
			<span style="width:2px;height:28px;background:var(--border-color);"></span>${text}</div>`;
	}

	get_operation(operation_id) {
		return this.get_operations().find((row) => cint(row.operation_id) === cint(operation_id));
	}

	get_step_no(operation) {
		return this.get_operations().indexOf(operation) + 1;
	}

	get_output_item(operation) {
		if (!operation) return "";
		const operations = this.get_operations();
		if (operation === operations[operations.length - 1]) return this.view.get_node_item(this.bom_node_id);
		return operation.output_node_id
			? this.view.get_node_item(operation.output_node_id)
			: operation.output_item;
	}

	get_output_label(operation) {
		if (!operation) return "";
		if (operation.output_node_id) return this.view.get_node_label(operation.output_node_id);
		return operation.output_item || "";
	}

	mount_links(container) {
		container
			.find(".design-link-cell")
			.each((_, cell) => open_link_field(cell, { ...this.get_link_options($(cell)), focus: false }));
	}

	get_link_options($cell) {
		const kind = $cell.attr("data-link");
		const operation = this.get_row($cell, "operation");
		const options = {
			operation: () => ({
				doctype: "Operation",
				value: operation.operation,
				placeholder: __("Operation"),
				on_change: (value) => this.set_operation(operation, value),
			}),
			workstation_type: () => ({
				doctype: "Workstation Type",
				value: operation.workstation_type,
				placeholder: __("Workstation Type"),
				on_change: (value) => this.update(operation, { workstation_type: value }),
			}),
			output: () => ({
				doctype: "Item",
				value: this.get_output_item(operation),
				placeholder: __("Item this step makes"),
				on_change: (value) => this.set_output(operation, value),
			}),
			material: () => ({
				doctype: "Item",
				placeholder: __("Add raw material"),
				on_change: (value) => this.add_item(cint($cell.attr("data-operation-id")), value),
			}),
			sub_assembly: () => ({
				doctype: "Item",
				placeholder: __("Sub-assembly item"),
				get_query: () => ({ filters: { name: ["not in", this.get_bom_items()] } }),
				on_change: (value) => this.add_sub_assembly(value),
			}),
		};
		return options[kind]();
	}

	get_row(element, kind) {
		const name = $(element).attr(`data-${kind}`);
		const table = kind === "operation" ? "operations" : "materials";
		return (this.frm.doc[table] || []).find((row) => row.name === name);
	}

	update(row, values) {
		Object.assign(row, values);
		this.frm.dirty();
		this.view.render();
	}

	async set_operation(row, operation) {
		const defaults = await frappe.db.get_value("Operation", operation, [
			"workstation",
			"total_operation_time",
		]);
		const { workstation, total_operation_time } = defaults.message || {};
		const workstation_type =
			row.workstation_type ||
			(workstation &&
				(await frappe.db.get_value("Workstation", workstation, "workstation_type")).message
					?.workstation_type);
		this.update(row, {
			operation,
			workstation_type: workstation_type || row.workstation_type,
			time_in_mins: flt(row.time_in_mins) || flt(total_operation_time),
		});
	}

	set_output(row, item_code) {
		const part = this.find_unused_part(item_code);
		this.update(row, {
			output_node_id: part ? part.node_id : 0,
			output_item: part ? "" : item_code,
		});
	}

	add_item(operation_id, item_code) {
		const part = this.find_unused_part(item_code);
		this.add_material(operation_id, part ? `part:${part.node_id}` : `item:${item_code}`);
	}

	find_unused_part(item_code) {
		const used = this.view.get_used_node_ids();
		return (this.frm.doc.items || []).find(
			(part) => part.item_code === item_code && !used.has(part.node_id)
		);
	}

	add_material(operation_id, value) {
		const [kind, key] = split_value(value);
		const row = frappe.model.add_child(this.frm.doc, "BOM Creator Material", "materials");
		Object.assign(row, {
			bom_node_id: this.bom_node_id,
			operation_id,
			part_node_id: kind === "part" ? cint(key) : 0,
			item_code: kind === "item" ? key : "",
			from_operation_id: kind === "step" ? cint(key) : 0,
			qty: this.get_default_quantity(kind, key),
		});
		this.frm.dirty();
		this.view.render();
		this.view.wrapper
			.find(`.design-link-cell[data-link="material"][data-operation-id="${operation_id}"] input`)
			.trigger("focus");
	}

	get_default_quantity(kind, key) {
		if (kind === "part") return this.view.get_default_quantity(cint(key), this.bom_node_id);
		if (kind === "step") return flt(this.get_operation(key)?.output_quantity) || 1;
		return 1;
	}

	handle_change($input) {
		const field = $input.attr("data-field");
		const value = $input.val();
		if (field === "quantity") {
			this.update(this.get_row($input, "material"), { qty: flt(value) / this.bom_quantity });
		} else if (field === "time_in_mins") {
			this.update(this.get_row($input, "operation"), { time_in_mins: flt(value) });
		} else if (field === "output_quantity") {
			const output_quantity = flt(value) / this.bom_quantity || 1;
			this.update(this.get_row($input, "operation"), { output_quantity });
		} else if (field === "assign" && value !== "") {
			this.add_material(cint(value), `part:${$input.attr("data-node-id")}`);
		}
	}

	handle_action($button) {
		const action = $button.attr("data-action");
		if (action === "add-bom") {
			this.view.state.adding_bom = true;
		} else if (action === "add-operation") {
			this.add_operation();
		} else if (action === "remove-operation") {
			this.remove_operation(this.get_row($button, "operation"));
		} else if (action === "add-output") {
			this.add_material(cint($button.attr("data-operation-id")), `step:${$button.attr("data-from")}`);
		} else if (action === "remove-material") {
			this.remove_rows([this.get_row($button, "material")]);
		}
		this.view.render();
		if (action === "add-bom")
			this.view.wrapper.find(".design-bom-bar .design-link-cell input").trigger("focus");
	}

	get_bom_node_ids() {
		return [...new Set([...this.view.get_bom_node_ids(), ...this.view.state.extra_bom_nodes])];
	}

	get_bom_items() {
		return this.get_bom_node_ids()
			.map((node_id) => this.view.get_node_item(node_id))
			.filter(Boolean);
	}

	async add_sub_assembly(item_code) {
		const node_ids = this.get_bom_node_ids();
		let part = (this.frm.doc.items || []).find(
			(row) => row.item_code === item_code && !node_ids.includes(row.node_id)
		);
		if (!part) {
			part = await this.view.tree.add_part(0, item_code);
			this.frm.dirty();
		}
		this.view.state.extra_bom_nodes.push(part.node_id);
		Object.assign(this.view.state, { bom_node_id: part.node_id, adding_bom: false });
		this.view.render();
	}

	add_operation() {
		const last_id = Math.max(0, ...(this.frm.doc.operations || []).map((row) => cint(row.operation_id)));
		const row = frappe.model.add_child(this.frm.doc, "BOM Creator Operation", "operations");
		Object.assign(row, { operation_id: last_id + 1, bom_node_id: this.bom_node_id, output_quantity: 1 });
		this.frm.dirty();
	}

	remove_operation(operation) {
		const operation_id = cint(operation.operation_id);
		const materials = (this.frm.doc.materials || []).filter(
			(row) =>
				cint(row.bom_node_id) === this.bom_node_id &&
				(cint(row.operation_id) === operation_id || cint(row.from_operation_id) === operation_id)
		);
		this.remove_rows([...materials, operation]);
	}

	remove_rows(rows) {
		rows.forEach((row) => frappe.model.clear_doc(row.doctype, row.name));
		this.frm.dirty();
	}

	select_step(operation_id) {
		const node_ids = this.get_materials(operation_id)
			.map((row) => cint(row.part_node_id))
			.filter(Boolean);
		const operation = this.get_operation(operation_id);
		if (operation?.output_node_id) node_ids.push(cint(operation.output_node_id));
		this.view.highlight_nodes(node_ids);
		this.view.wrapper
			.find(".design-step")
			.css("box-shadow", "")
			.filter(`[data-operation-id="${operation_id}"]`)
			.css("box-shadow", "0 0 0 2px var(--blue-300)");
	}
}

function split_value(value) {
	const index = value.indexOf(":");
	return [value.slice(0, index), value.slice(index + 1)];
}

function escape(value) {
	return frappe.utils.escape_html(value);
}

function badge(label, theme) {
	return frappe.ui.badge.html({ label, theme, size: "sm" });
}

function remove_button(action, attrs, title) {
	return frappe.ui.button.html({
		icon: "x",
		variant: "ghost",
		size: "xs",
		title,
		attrs: { "data-action": action, ...attrs },
	});
}
