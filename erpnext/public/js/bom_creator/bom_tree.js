import { get_placements } from "./placement_panel";
import { get_item_link_html, open_item_link } from "./link_field";

const ROW =
	"display:flex;align-items:center;gap:8px;min-height:36px;padding:0 12px;border-top:1px solid var(--border-color);";
const INPUT = "height:28px;background-color:var(--fg-color);border:1px solid var(--border-color);";

export class BomTree {
	constructor(view) {
		this.view = view;
		this.collapsed = new Set();
		view.wrapper.on("click", ".design-tree [data-node-id]", (event) => {
			if ($(event.target).closest("input, button").length) return;
			this.view.highlight_nodes([cint($(event.currentTarget).attr("data-node-id"))]);
		});
		view.wrapper.on("click", ".design-tree [data-action]", (event) =>
			this.handle_action($(event.currentTarget))
		);
		view.wrapper.on("keydown", ".design-tree-add input", (event) => {
			if (event.key !== "Escape") return;
			this.adding_to = null;
			this.view.render();
		});
		view.wrapper.on("change", ".design-tree [data-field='quantity']", (event) => {
			const node_id = cint($(event.currentTarget).attr("data-part-node"));
			const quantity = flt(event.currentTarget.value);
			if (node_id) {
				this.update(this.view.get_part(node_id), { qty: quantity });
			} else {
				this.frm.set_value("qty", quantity || 1).then(() => this.view.render());
			}
		});
	}

	get frm() {
		return this.view.frm;
	}

	render(container) {
		this.editable = this.view.is_editable();
		this.show_items = true;
		const header = `<div class="text-muted small" style="${ROW}border-top:0;min-height:32px;background:var(--subtle-fg);">
			<span style="flex:1;">${__("Part")}</span>${
			this.show_items ? `<span style="width:130px;">${__("Item")}</span>` : ""
		}
			<span style="width:64px;text-align:right;">${__("Quantity")}</span>
			${this.show_items ? `<span style="width:36px;"></span>` : ""}
			<span style="width:96px;text-align:right;">${__("Amount")}</span>${this.get_actions_cell("")}</div>`;
		const rows = [this.get_finished_good_row()];
		if (!this.collapsed.has(0)) this.add_rows(0, 1, rows);

		container.html(`<div class="design-tree" style="border:1px solid var(--border-color);
			border-radius:var(--border-radius-md);overflow:hidden;">${header}${rows.join("")}</div>`);
		if (this.editable) this.open_add_link(container);
		this.mark_selected(this.view.selected_node_ids || new Set());
	}

	add_rows(parent_node_id, depth, rows) {
		for (const part of this.view.children[parent_node_id] || []) {
			rows.push(this.get_part_row(part, depth));
			const is_open = this.has_children(part) || this.adding_to === part.node_id;
			if (is_open && !part.exclude_from_bom && !this.collapsed.has(part.node_id))
				this.add_rows(part.node_id, depth + 1, rows);
		}
		if (this.editable && this.adding_to === parent_node_id)
			rows.push(this.get_add_row(parent_node_id, depth));
	}

	get_finished_good_row() {
		const doc = this.frm.doc;
		return `<div data-node-id="0" style="${ROW}background:var(--subtle-accent);">
			${this.get_caret(0, true)}${this.get_thumbnail(0, doc.item_code)}
			<span style="flex:1;min-width:0;display:flex;align-items:center;gap:8px;">
				<span class="bold ellipsis" title="${__("Finished Good")}">${escape(
			doc.design_name || __("Finished Good")
		)}</span></span>
			${this.get_item_cell(0, doc.item_code)}
			<span style="width:64px;">${this.get_finished_good_quantity()}</span>
			${this.show_items ? `<span style="width:36px;"></span>` : ""}
			${this.get_amount_cell(doc.raw_material_cost)}
			${this.get_actions_cell(this.get_add_button(0) + this.get_empty_slot() + this.get_menu_button(0))}</div>`;
	}

	get_finished_good_quantity() {
		const quantity = flt(this.frm.doc.qty) || 1;
		if (!this.editable) return `<span style="display:block;text-align:right;">${quantity}</span>`;

		return `<input class="form-control input-sm" data-field="quantity" data-part-node="0" value="${quantity}"
			title="${__("Quantity of the finished good the BOM is made for")}" style="${INPUT}text-align:right;">`;
	}

	get_add_button(node_id) {
		return this.get_icon_button("plus", __("Add Material"), "add", node_id);
	}

	get_icon_button(icon, title, action, node_id) {
		if (!this.editable) return "";
		return frappe.ui.button.html({
			icon,
			variant: "ghost",
			size: "xs",
			title,
			attrs: { "data-action": action, "data-part-node": node_id },
		});
	}

	get_part_row(part, depth) {
		const excluded = Boolean(part.exclude_from_bom);
		const label = `<span class="ellipsis ${this.has_children(part) ? "bold" : ""}" title="${escape(
			part.part_number
		)}"
			style="${excluded ? "text-decoration:line-through;" : ""}">${escape(
			part.part_name || part.part_number
		)}</span>`;
		const quantity = excluded
			? `<span class="text-muted" style="display:block;text-align:right;">${flt(part.qty)}</span>`
			: this.get_quantity_cell(part);
		const uom = this.show_items
			? `<span class="text-muted ellipsis" style="width:36px;">${escape(part.uom || "")}</span>`
			: "";

		return `<div data-node-id="${part.node_id}" style="${ROW}cursor:pointer;${
			excluded ? "opacity:0.55;" : ""
		}">
			<span style="width:${depth * 16}px;flex:none;"></span>
			${this.get_caret(part.node_id, this.has_children(part) && !excluded)}${this.get_thumbnail(
			part.node_id,
			part.item_code
		)}
			<span style="flex:1;min-width:0;display:flex;align-items:center;gap:8px;">${get_change_dot(
				part
			)}${label}</span>
			${
				excluded
					? this.show_items
						? `<span style="width:130px;"></span>`
						: ""
					: this.get_item_cell(part.node_id, part.item_code)
			}
			<span style="width:64px;">${quantity}</span>${uom}
			${excluded ? `<span style="width:96px;"></span>` : this.get_amount_cell(part.amount)}
			${this.get_actions_cell(this.get_row_actions(part))}</div>`;
	}

	get_row_actions(part) {
		if (part.exclude_from_bom) {
			return this.get_icon_button("undo-2", __("Add Back to BOM"), "restore", part.node_id);
		}

		const remove =
			part.source === "Manual"
				? this.get_icon_button("x", __("Remove"), "remove", part.node_id)
				: this.get_icon_button("x", __("Remove from BOM"), "exclude", part.node_id);
		return this.get_add_button(part.node_id) + remove + this.get_menu_button(part.node_id);
	}

	get_empty_slot() {
		return frappe.ui.button.html({
			icon: "ellipsis",
			variant: "ghost",
			size: "xs",
			attrs: {
				style: "visibility:hidden;",
				tabindex: "-1",
				"aria-hidden": "true",
				"aria-label": __("More"),
			},
		});
	}

	get_actions_cell(content) {
		if (!this.editable) return "";
		return `<span style="width:84px;flex:none;display:flex;justify-content:flex-end;">${content}</span>`;
	}

	get_amount_cell(amount) {
		return `<span class="ellipsis" style="width:96px;flex:none;text-align:right;">${format_currency(
			flt(amount),
			this.frm.doc.currency
		)}</span>`;
	}

	get_menu_button(node_id) {
		return this.get_menu_items(node_id).length
			? this.get_icon_button("ellipsis", __("More"), "menu", node_id)
			: this.get_empty_slot();
	}

	get_menu_items(node_id) {
		const part = this.view.get_part(node_id);
		const item_code = node_id ? part.item_code : this.frm.doc.item_code;
		const items = [];
		if (part?.item_code) items.push({ label: __("Edit"), action: () => this.edit_part(part) });
		if (item_code) {
			items.push({
				label: this.view.has_geometry(node_id)
					? __("Take Item Image from the 3D Model")
					: __("Upload Item Image"),
				action: () => this.set_image(node_id),
			});
		}
		if (part?.source === "Manual" && this.view.viewer) {
			items.push(
				part.model_file
					? {
							label: __("Place in Model ({0} of {1} placed)", [
								get_placements(part).length,
								flt(part.qty),
							]),
							action: () => this.view.placement_panel.start(part.node_id),
					  }
					: { label: __("Add 3D Model"), action: () => this.upload_model(part) }
			);
		}
		return items;
	}

	open_menu(button, node_id) {
		this.close_menu();
		const menu = $(`<div class="dropdown-menu show" style="position:fixed;z-index:1050;"></div>`);
		for (const item of this.get_menu_items(node_id)) {
			$(`<a class="dropdown-item" href="#"></a>`)
				.text(item.label)
				.on("click", (event) => {
					event.preventDefault();
					this.close_menu();
					item.action();
					this.view.render();
				})
				.appendTo(menu);
		}
		menu.appendTo(document.body);
		const bounds = button.getBoundingClientRect();
		const opens_up = window.innerHeight - bounds.bottom < menu.outerHeight() + 8;
		menu.css({
			left: bounds.right - menu.outerWidth(),
			top: opens_up ? bounds.top - menu.outerHeight() - 4 : bounds.bottom + 4,
		});
		this.menu = menu;
		setTimeout(() =>
			$(document).one("click.bom-tree-menu scroll.bom-tree-menu", () => this.close_menu())
		);
	}

	close_menu() {
		this.menu?.remove();
		this.menu = null;
		$(document).off(".bom-tree-menu");
	}

	edit_part(part) {
		const is_assembly = this.has_children(part);
		const dialog = new frappe.ui.Dialog({
			title: __("Edit {0}", [part.part_name || part.part_number]),
			fields: get_part_fields(part, is_assembly, this.frm.doc.routing),
			primary_action_label: __("Update"),
			primary_action: (values) => {
				if (values.uom !== part.uom) values.conversion_factor = 0;
				this.update(part, values);
				dialog.hide();
			},
		});
		dialog.set_values(part);
		dialog.show();
	}

	has_children(part) {
		return Boolean(this.view.children[part.node_id]?.length);
	}

	get_thumbnail(node_id, item_code) {
		const box = `flex:none;width:28px;height:28px;padding:0;display:flex;align-items:center;justify-content:center;
			overflow:hidden;border-radius:var(--border-radius-sm);`;
		if (!item_code) return `<span style="${box}"></span>`;

		const image = this.view.item_images[item_code];
		const from_model = this.view.has_geometry(node_id);
		const content = image
			? `<img src="${escape(image)}" alt="" style="width:100%;height:100%;object-fit:contain;">`
			: frappe.utils.icon(from_model ? "camera" : "image-plus", "sm");
		const title = from_model ? __("Take Item Image from the 3D Model") : __("Upload Item Image");
		return `<button class="btn btn-default" data-action="image" data-part-node="${node_id}" title="${title}"
			style="${box}background:var(--fg-color);border:1px solid var(--border-color);">${content}</button>`;
	}

	upload_model(part) {
		new frappe.ui.FileUploader({
			doctype: this.frm.is_new() ? null : this.frm.doctype,
			docname: this.frm.is_new() ? null : this.frm.docname,
			restrictions: { allowed_file_types: [".step", ".stp", ".stl", ".glb"] },
			on_success: (file) => this.update(part, { model_file: file.file_url }),
		});
	}

	async set_image(node_id) {
		const item_code = node_id ? this.view.get_part(node_id).item_code : this.frm.doc.item_code;
		if (this.view.has_geometry(node_id)) {
			await this.view.save_item_image(item_code, await this.view.capture_node_image(node_id));
			frappe.show_alert({ message: __("Item image updated"), indicator: "green" });
			return;
		}

		new frappe.ui.FileUploader({
			doctype: "Item",
			docname: item_code,
			fieldname: "image",
			restrictions: { allowed_file_types: ["image/*"] },
			on_success: (file) => this.view.set_item_image(item_code, file.file_url),
		});
	}

	get_caret(node_id, has_children) {
		if (!has_children) return `<span style="width:16px;flex:none;"></span>`;
		const icon = this.collapsed.has(node_id) ? "chevron-right" : "chevron-down";
		return `<span data-action="toggle" data-part-node="${node_id}" style="width:16px;flex:none;cursor:pointer;
			display:flex;align-items:center;">${frappe.utils.icon(icon, "sm")}</span>`;
	}

	get_item_cell(node_id, item_code) {
		if (!this.show_items) return "";
		if (this.editable) return get_item_link_html(node_id, item_code);

		const cell = item_code
			? `<span class="ellipsis">${escape(item_code)}</span>`
			: frappe.ui.badge.html({ label: __("Not Mapped"), theme: "red", size: "sm" });
		return `<span style="width:130px;display:flex;min-width:0;">${cell}</span>`;
	}

	get_quantity_cell(part) {
		const design_quantity = flt(part.design_quantity);
		const edited = part.source !== "Manual" && design_quantity && flt(part.qty) !== design_quantity;
		const title = edited ? __("Design file: {0}", [design_quantity]) : "";
		const dot = edited
			? `<span title="${title}" style="position:absolute;left:-10px;top:11px;width:6px;height:6px;
				border-radius:50%;background:var(--orange-500);"></span>`
			: "";
		const value = this.editable
			? `<input class="form-control input-sm" data-field="quantity" data-part-node="${part.node_id}"
				value="${flt(part.qty)}" title="${title}" style="${INPUT}text-align:right;">`
			: `<span style="display:block;text-align:right;" title="${title}">${flt(part.qty)}</span>`;
		return `<span style="position:relative;display:block;">${dot}${value}</span>`;
	}

	get_add_row(parent_node_id, depth) {
		return `<div style="${ROW}"><span style="width:${depth * 16 + 16}px;flex:none;"></span>
			<span class="design-item-cell design-tree-add" data-part-node="${parent_node_id}"
				style="flex:1;min-width:0;display:flex;"></span>
			${this.get_actions_cell(this.get_icon_button("x", __("Close"), "close-add", parent_node_id))}</div>`;
	}

	open_add_link(container) {
		container.find(".design-tree-add").each((_, cell) => {
			const parent_node_id = cint($(cell).attr("data-part-node"));
			open_item_link(cell, {
				placeholder: __("Add material to {0}", [this.view.get_node_label(parent_node_id)]),
				on_change: (item_code) => this.add_material(parent_node_id, item_code),
				focus: false,
			});
		});
	}

	async get_item(item_code) {
		return (await frappe.db.get_value("Item", item_code, ["item_name", "stock_uom"])).message || {};
	}

	async set_item(node_id, item_code) {
		if (node_id) {
			const item = await this.get_item(item_code);
			this.update(this.view.get_part(node_id), {
				item_code,
				item_name: item.item_name,
				uom: item.stock_uom,
			});
		} else {
			await this.frm.set_value("item_code", item_code);
			this.view.render();
		}
	}

	async add_material(parent_node_id, item_code) {
		const item = await this.get_item(item_code);
		const last_node_id = Math.max(0, ...(this.frm.doc.items || []).map((row) => cint(row.node_id)));
		const row = frappe.model.add_child(this.frm.doc, "BOM Creator Item", "items");
		Object.assign(row, {
			node_id: last_node_id + 1,
			parent_node_id,
			part_number: item_code,
			part_name: item.item_name || item_code,
			item_code,
			item_name: item.item_name,
			uom: item.stock_uom,
			qty: 1,
			source: "Manual",
		});
		this.frm.dirty();
		this.view.render();
		this.view.wrapper.find(`.design-tree-add[data-part-node="${parent_node_id}"] input`).trigger("focus");
	}

	update(part, values) {
		Object.assign(part, values);
		this.frm.dirty();
		this.view.render();
	}

	handle_action($element) {
		const node_id = cint($element.attr("data-part-node"));
		const part = this.view.get_part(node_id);
		const actions = {
			add: () => this.open_add_row(node_id),
			"close-add": () => (this.adding_to = null),
			toggle: () =>
				this.collapsed.has(node_id) ? this.collapsed.delete(node_id) : this.collapsed.add(node_id),
			remove: () => this.remove_part(part),
			menu: () => this.open_menu($element.get(0), node_id),
			exclude: () => this.update(part, { exclude_from_bom: 1 }),
			restore: () => this.update(part, { exclude_from_bom: 0 }),
			image: () => this.set_image(node_id),
		};
		actions[$element.attr("data-action")]?.();
		this.view.render();
		if (this.adding_to !== null && this.adding_to !== undefined) {
			this.view.wrapper
				.find(`.design-tree-add[data-part-node="${this.adding_to}"] input`)
				.trigger("focus");
		}
	}

	open_add_row(node_id) {
		this.adding_to = this.adding_to === node_id ? null : node_id;
		this.collapsed.delete(node_id);
	}

	remove_part(part) {
		(this.view.children[part.node_id] || []).forEach((child) => this.remove_part(child));
		frappe.model.clear_doc(part.doctype, part.name);
		this.frm.dirty();
	}

	mark_selected(node_ids) {
		this.view.wrapper.find(".design-tree [data-node-id]").each((_, row) => {
			const node_id = cint($(row).attr("data-node-id"));
			if (!node_id) return;
			$(row).css("background", node_ids.has(node_id) ? "var(--subtle-accent)" : "");
		});
	}
}

function escape(value) {
	return frappe.utils.escape_html(value);
}

function get_part_fields(part, is_assembly, routing) {
	return [
		{ fieldname: "uom", fieldtype: "Link", options: "UOM", label: __("UOM"), reqd: 1 },
		{
			fieldname: "is_phantom_item",
			fieldtype: "Check",
			label: __("Is Phantom Item"),
			hidden: !is_assembly,
		},
		{ fieldname: "do_not_explode", fieldtype: "Check", label: __("Do Not Explode"), hidden: is_assembly },
		{
			fieldname: "bom_no",
			fieldtype: "Link",
			options: "BOM",
			label: __("BOM No"),
			hidden: is_assembly,
			depends_on: "eval:!doc.do_not_explode",
			get_query: () => ({ filters: { item: part.item_code, docstatus: 1 } }),
		},
		{ fieldname: "sourced_by_supplier", fieldtype: "Check", label: __("Sourced by Supplier") },
		{
			fieldname: "operation",
			fieldtype: "Link",
			options: "Operation",
			label: __("Operation"),
			hidden: !routing,
			get_query: () => ({
				query: "erpnext.manufacturing.doctype.routing.routing.get_operations",
				filters: { routing },
			}),
		},
		{ fieldname: "instruction", fieldtype: "Small Text", label: __("Instruction") },
	];
}

function get_change_dot(part) {
	const colors = { Added: "green", "Quantity Changed": "orange" };
	if (!colors[part.change_type]) return "";
	return `<span title="${__(part.change_type)}" style="flex:none;width:6px;height:6px;border-radius:50%;
		background:var(--${colors[part.change_type]}-500);"></span>`;
}
