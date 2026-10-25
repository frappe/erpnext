import { BomTree } from "./bom_tree";
import { open_item_link } from "./link_field";
import { ModelViewer } from "./model_viewer";
import { OperationsEditor } from "./operations_editor";
import { PartsTable } from "./parts_table";
import { PlacementPanel } from "./placement_panel";

export class DesignView {
	constructor(frm) {
		this.frm = frm;
		this.wrapper = $(frm.fields_dict.design_view.wrapper);
		this.state = { tab: "Operations", bom_node_id: 0, extra_bom_nodes: [] };
		this.item_images = {};
		this.active_item_node = null;
		this.placement_panel = new PlacementPanel(this);
		this.operations = new OperationsEditor(this);
		this.parts = new PartsTable(this);
		this.tree = new BomTree(this);
		this.wrapper.on("click", ".design-item-link", (event) =>
			this.open_item_cell(cint($(event.currentTarget).attr("data-part-node")))
		);
		this.wrapper.on(
			"focus",
			"input[data-field='quantity'], input[data-field='output_quantity'], input[data-field='time_in_mins']",
			(event) => setTimeout(() => event.currentTarget.select())
		);
	}

	refresh() {
		const doc = this.frm.doc;
		const has_model = /\.(step|stp)$/i.test(doc.design_file || "");

		if (this.layout_key !== `${doc.name}:${doc.design_file}`) {
			this.layout_key = `${doc.name}:${doc.design_file}`;
			this.state = { tab: "Operations", bom_node_id: 0, extra_bom_nodes: [] };
			this.make_layout(has_model);
		}

		this.render();
	}

	make_layout(has_model) {
		this.viewer?.destroy();
		this.viewer = null;
		this.geometry = {};
		this.wrapper.html(`
			<style>
				.bom-creator-view {
					display: flex; gap: var(--margin-lg); height: 560px; margin-bottom: var(--margin-md);
				}
				.bom-creator-view.without-model { height: auto; }
				.bom-creator-view :is(.design-item-cell, .design-link-cell, .design-uom-cell) .frappe-control,
				.bom-creator-view :is(.design-item-cell, .design-link-cell, .design-uom-cell) .form-group {
					width: 100%; margin: 0;
				}
				.bom-creator-view :is(.design-item-cell, .design-link-cell, .design-uom-cell) input.form-control,
				.bom-creator-view :is(.design-item-link, .design-uom-link) {
					height: 28px; background-color: var(--fg-color); border: 1px solid var(--border-color);
				}
				.bom-creator-view :is(.design-item-link, .design-uom-link) { width: 100%; padding: 0 8px; text-align: left; cursor: text; }
				.bom-creator-view.without-model .design-body { max-height: 560px; }
				.bom-creator-view .design-model {
					flex: 0 0 34%; position: relative; border: 1px solid var(--border-color);
					border-radius: var(--border-radius-md); overflow: hidden; background: var(--subtle-fg);
				}
				.bom-creator-view .design-panel { flex: 1; min-width: 0; display: flex; flex-direction: column; }
				.bom-creator-view .design-body { flex: 1; min-height: 0; overflow-y: auto; }
				@media (max-width: 991px) {
					.bom-creator-view { flex-direction: column; height: auto; }
					.bom-creator-view .design-model { flex: none; height: 360px; }
					.bom-creator-view .design-body { height: 480px; flex: none; }
				}
			</style>
			<div class="bom-creator-view ${has_model ? "" : "without-model"}">
				<div class="design-model" style="${has_model ? "" : "display:none;"}">
					<div class="design-model-message text-muted" style="position:absolute;inset:0;display:flex;
						align-items:center;justify-content:center;pointer-events:none;">${__("Loading 3D model...")}</div>
				</div>
				<div class="design-panel">
					<div class="design-tabs" style="display:flex;align-items:center;gap:var(--margin-sm);
						min-height:32px;margin-bottom:var(--margin-sm);"></div>
					<div class="design-body"></div>
					<div class="design-summary text-muted small" style="display:flex;flex-wrap:wrap;gap:4px 16px;
						padding-top:var(--margin-sm);"></div>
				</div>
			</div>`);

		if (has_model) this.load_model();
	}

	async load_model() {
		const message = this.wrapper.find(".design-model-message");
		this.viewer = new ModelViewer(this.wrapper.find(".design-model").get(0), (path) =>
			this.highlight_nodes(this.get_node_ids_for_path(path))
		);

		try {
			this.placement_panel.attach(this.viewer);
			await this.viewer.load(this.frm.doc.design_file);
			message.remove();
			this.geometry = {};
			this.render();
		} catch (error) {
			message.text(error.message);
		}
	}

	render() {
		this.index_parts();
		this.load_item_images();
		this.placement_panel.sync();
		const produces = Boolean(this.frm.doc.track_semi_finished_goods);
		this.render_header(produces);
		const body = this.wrapper.find(".design-body");
		if (!produces) {
			this.tree.render(body);
		} else if (this.state.tab === "Parts") {
			this.parts.render(body);
		} else {
			this.operations.render(body);
		}
		this.render_summary(produces);
		if (this.active_item_node !== null) this.open_item_cell(this.active_item_node, { open_list: false });
	}

	open_item_cell(node_id, { open_list = true } = {}) {
		const cell = this.wrapper.find(`.design-item-cell[data-part-node="${node_id}"]`);
		if (!cell.length) return;

		this.active_item_node = node_id;
		const control = open_item_link(cell, {
			value: node_id ? this.get_part(node_id)?.item_code : this.frm.doc.item_code,
			open_list,
			on_change: async (item_code, created_new_item) => {
				await this.tree.set_item(node_id, item_code);
				if (created_new_item) await this.make_item_images([item_code]);
			},
			get_new_item_values: () => this.get_new_item_values(node_id),
		});
		control.input.addEventListener(
			"keydown",
			(event) => this.move_item_cell(event, node_id, control),
			true
		);
		control.$input.on("focusout", () =>
			setTimeout(() => {
				if (!$(document.activeElement).closest(".design-item-cell").length)
					this.active_item_node = null;
			})
		);
	}

	move_item_cell(event, node_id, control) {
		if (event.key === "Escape" && control.awesomplete.isOpened) {
			event.preventDefault();
			event.stopPropagation();
			control.awesomplete.close();
			return;
		}

		const step = { ArrowDown: 1, ArrowUp: -1 }[event.key];
		if (!step || control.awesomplete.isOpened) return;

		const node_ids = this.wrapper
			.find(".design-item-cell[data-part-node]")
			.map((_, cell) => cint($(cell).attr("data-part-node")))
			.get();
		const next = node_ids[node_ids.indexOf(node_id) + step];
		if (next === undefined) return;

		event.preventDefault();
		this.open_item_cell(next);
		this.wrapper
			.find(`.design-item-cell[data-part-node="${next}"]`)
			.get(0)
			?.scrollIntoView({ block: "nearest" });
	}

	render_header(produces) {
		const header = this.wrapper.find(".design-tabs").empty().toggle(produces);
		if (produces) header.append(this.get_tabs());
	}

	get_tabs() {
		const count = (value) => $(frappe.ui.badge.html({ label: String(value), size: "sm" }));
		return frappe.ui.tab_buttons({
			type: "underline",
			label: __("View"),
			options: [
				{
					label: __("Operations"),
					value: "Operations",
					suffix: count(this.frm.doc.operations?.length || 0),
				},
				{ label: __("Parts"), value: "Parts", suffix: count(this.frm.doc.items?.length || 0) },
			],
			value: this.state.tab,
			on_change: (value) => {
				this.state.tab = value;
				this.render();
			},
		});
	}

	render_summary(produces) {
		const texts = produces ? this.get_operation_summary() : this.get_tree_summary();
		this.wrapper.find(".design-summary").html(texts.map((text) => `<span>${text}</span>`).join(""));
	}

	get_operation_summary() {
		const operations = this.frm.doc.operations || [];
		const minutes = operations.reduce((total, row) => total + flt(row.time_in_mins), 0);
		const unused = this.get_unused_parts().length;
		return [
			__("{0} operations", [operations.length]),
			__("{0} minutes", [format_number(minutes, null, 0)]),
			unused ? __("{0} parts not used", [unused]) : "",
			__("{0} BOMs will be created", [this.get_bom_node_ids().length]),
			this.get_cost_summary(),
		].filter(Boolean);
	}

	get_tree_summary() {
		const all_parts = this.frm.doc.items || [];
		const parts = all_parts.filter((part) => !this.is_excluded(part));
		const has_children = new Set(parts.map((part) => part.parent_node_id));
		const assemblies = new Set(
			parts
				.filter((part) => has_children.has(part.node_id))
				.map((part) => part.item_code || part.node_id)
		);
		const unmapped = this.frm.doc.docstatus === 1 ? parts.filter((part) => !part.item_code).length : 0;
		const removed = all_parts.filter((part) => part.exclude_from_bom).length;
		return [
			__("{0} parts", [parts.length]),
			removed ? __("{0} removed from BOM", [removed]) : "",
			unmapped ? __("{0} parts not mapped", [unmapped]) : "",
			__("{0} BOMs will be created", [assemblies.size + 1]),
			this.get_cost_summary(),
		].filter(Boolean);
	}

	get_cost_summary() {
		const cost = flt(this.frm.doc.raw_material_cost);
		return cost ? __("Total Cost {0}", [format_currency(cost, this.frm.doc.currency)]) : "";
	}

	is_excluded(part) {
		for (let current = part; current; current = this.get_part(current.parent_node_id)) {
			if (current.exclude_from_bom) return true;
		}
		return false;
	}

	index_parts() {
		this.parts_by_node = {};
		this.children = {};
		for (const row of this.frm.doc.items || []) {
			this.parts_by_node[row.node_id] = row;
			(this.children[row.parent_node_id || 0] ??= []).push(row);
		}
	}

	is_editable() {
		return this.frm.doc.docstatus === 0 || ["Submitted", "Failed"].includes(this.frm.doc.status);
	}

	get_part(node_id) {
		return this.parts_by_node[node_id];
	}

	get_node_label(node_id) {
		if (!node_id) return this.frm.doc.design_name || __("Finished Good");
		const part = this.get_part(node_id);
		return part ? part.part_name || part.part_number : __("Missing Part");
	}

	get_node_item(node_id) {
		return node_id ? this.get_part(node_id)?.item_code : this.frm.doc.item_code;
	}

	get_bom_node_ids() {
		const rows = [...(this.frm.doc.operations || []), ...(this.frm.doc.materials || [])];
		return [...new Set([0, ...rows.map((row) => cint(row.bom_node_id))])];
	}

	get_used_node_ids() {
		const used = new Set(this.get_bom_node_ids());
		(this.frm.doc.materials || []).forEach((row) => row.part_node_id && used.add(cint(row.part_node_id)));
		(this.frm.doc.operations || []).forEach(
			(row) => row.output_node_id && used.add(cint(row.output_node_id))
		);
		return used;
	}

	is_inside_used_part(part, used) {
		const bom_node_ids = this.get_bom_node_ids();
		for (
			let parent = this.get_part(part.parent_node_id);
			parent;
			parent = this.get_part(parent.parent_node_id)
		) {
			if (used.has(parent.node_id)) return !bom_node_ids.includes(parent.node_id);
		}
		return false;
	}

	get_unused_parts() {
		const used = this.get_used_node_ids();
		return (this.frm.doc.items || []).filter(
			(part) =>
				!part.is_expandable &&
				!used.has(part.node_id) &&
				!this.is_excluded(part) &&
				!this.is_inside_used_part(part, used)
		);
	}

	get_default_quantity(node_id, bom_node_id) {
		let quantity = 1;
		let part = this.get_part(node_id);
		while (part && part.node_id !== bom_node_id) {
			quantity *= flt(part.qty) || 1;
			part = this.get_part(part.parent_node_id);
		}
		return quantity;
	}

	highlight_nodes(node_ids) {
		this.selected_node_ids = new Set(node_ids);
		this.parts.mark_selected(this.selected_node_ids);
		this.tree.mark_selected(this.selected_node_ids);
		const matchers = [...this.selected_node_ids]
			.map((node_id) => this.get_part(node_id))
			.filter(Boolean)
			.map((part) => this.get_matcher(part));
		this.viewer?.highlight((path) => matchers.some((matches) => matches(path)));
	}

	get_matcher(part) {
		let top = part;
		while (this.get_part(top.parent_node_id)) top = this.get_part(top.parent_node_id);
		const names = this.get_names(part);
		return (path) =>
			[top.part_name, top.part_number].includes(this.get_top_name(path)) && names.has(path.at(-1));
	}

	get_names(part) {
		const names = new Set([part.part_name, part.part_number]);
		(this.children[part.node_id] || []).forEach((child) =>
			this.get_names(child).forEach((name) => names.add(name))
		);
		return names;
	}

	get_top_name(path) {
		const root = path.findIndex((name) =>
			[this.frm.doc.design_name, this.frm.doc.part_number].includes(name)
		);
		return path[root >= 0 ? root + 1 : path.findIndex(Boolean)];
	}

	get_node_ids_for_path(path) {
		if (!path) return [];
		const parts = (this.frm.doc.items || []).filter(
			(part) => !part.is_expandable && this.get_matcher(part)(path)
		);
		return parts.slice(0, 1).map((part) => part.node_id);
	}

	load_item_images(item_codes) {
		const doc = this.frm.doc;
		const codes = (item_codes || [doc.item_code, ...(doc.items || []).map((part) => part.item_code)])
			.filter(Boolean)
			.filter((code) => item_codes || !(code in this.item_images));
		if (!codes.length) return Promise.resolve();

		codes.forEach((code) => (this.item_images[code] ??= ""));
		return frappe.db
			.get_list("Item", {
				filters: { name: ["in", codes] },
				fields: ["name", "image"],
				limit: codes.length,
			})
			.then((items) => {
				items.forEach((item) => (this.item_images[item.name] = item.image || ""));
				this.render();
			});
	}

	get_new_item_values(node_id) {
		const doc = this.frm.doc;
		const part = this.get_part(node_id);
		const item_code = part ? part.part_number : doc.part_number || doc.design_name;
		const item_name = part ? part.part_name || part.part_number : doc.design_name;
		return {
			item_code,
			item_name,
			description: part?.description || item_name,
			...(doc.item_group ? { item_group: doc.item_group } : {}),
		};
	}

	has_geometry(node_id) {
		if (!this.viewer?.meshes.length) return false;
		if (!node_id) return true;
		if (this.get_part(node_id)?.model_file) return true;

		this.geometry ??= {};
		if (!(node_id in this.geometry)) {
			const matches = this.get_matcher(this.get_part(node_id));
			this.geometry[node_id] = this.viewer.meshes.some((mesh) => matches(mesh.userData.path));
		}
		return this.geometry[node_id];
	}

	async capture_node_image(node_id) {
		const part = this.get_part(node_id);
		if (part?.model_file) {
			return this.viewer.capture_meshes(
				await this.viewer.placement.get_template_meshes(part.model_file)
			);
		}

		const matches = part ? this.get_matcher(part) : () => true;
		return this.viewer.capture(matches, { single: Boolean(part && !part.is_expandable) });
	}

	async save_item_image(item_code, data_url) {
		const form = new FormData();
		form.append("file", await (await fetch(data_url)).blob(), `${item_code}.png`);
		Object.entries({ is_private: "0", doctype: "Item", docname: item_code, fieldname: "image" }).forEach(
			([key, value]) => form.append(key, value)
		);
		const response = await fetch("/api/method/upload_file", {
			method: "POST",
			body: form,
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
		});
		if (!response.ok) frappe.throw(__("The item image could not be uploaded."));

		await this.set_item_image(item_code, (await response.json()).message.file_url);
	}

	async set_item_image(item_code, file_url) {
		await frappe.db.set_value("Item", item_code, "image", file_url);
		this.item_images[item_code] = file_url;
		this.render();
	}

	async make_item_images(item_codes) {
		await this.load_item_images(item_codes);
		const doc = this.frm.doc;
		for (const item_code of item_codes) {
			const node_id =
				item_code === doc.item_code
					? 0
					: (doc.items || []).find((part) => part.item_code === item_code)?.node_id;
			if (node_id === undefined || this.item_images[item_code] || !this.has_geometry(node_id)) continue;
			await this.save_item_image(item_code, await this.capture_node_image(node_id));
		}
	}

	destroy() {
		this.viewer?.destroy();
	}
}
