export class PlacementPanel {
	constructor(view) {
		this.view = view;
		view.wrapper.on("click", ".design-placement [data-placement]", (event) =>
			this.handle_action($(event.currentTarget).attr("data-placement"))
		);
		$(document).on("keydown", (event) => {
			if (event.key === "Escape" && this.toolbar?.is(":visible")) this.finish();
		});
	}

	get frm() {
		return this.view.frm;
	}

	attach(viewer) {
		this.viewer = viewer;
		this.selected = null;
		viewer.on_pick_added = (object) => this.select(object);
		viewer.placement.on_change = (object) => this.save(object);
		this.toolbar = $(`<div class="design-placement" style="position:absolute;top:8px;left:8px;right:8px;
			display:none;align-items:center;gap:6px;flex-wrap:wrap;padding:6px 8px;background:var(--fg-color);
			border:1px solid var(--border-color);border-radius:var(--radius-md);
			box-shadow:var(--shadow-sm);z-index:2;"></div>`).appendTo(viewer.container);
	}

	get_parts() {
		return (this.frm.doc.items || [])
			.filter((part) => part.model_file && !this.view.is_excluded(part))
			.map((part) => ({
				node_id: part.node_id,
				model_file: part.model_file,
				placements: get_placements(part),
			}));
	}

	async sync() {
		if (!this.viewer?.meshes.length) return;
		await this.viewer.placement.sync(this.get_parts());
	}

	start(node_id) {
		if (!this.viewer?.meshes.length) {
			frappe.msgprint(__("Open a design with a STEP file to place parts in the model."));
			return;
		}
		this.select(null);
		this.node_id = node_id;
		this.viewer.on_place = (hit) => this.place(hit);
		this.show_toolbar(__("Click on the model where {0} goes.", [this.get_label(node_id)]), ["cancel"]);
	}

	async place(hit) {
		this.viewer.on_place = null;
		const part = this.view.get_part(this.node_id);
		const placements = get_placements(part);
		placements.push(await this.viewer.placement.get_drop_placement(part.model_file, hit));
		this.write(part, placements);
		await this.sync();
		this.select(this.viewer.placement.find(part.node_id, placements.length - 1));
	}

	select(object) {
		this.selected = object;
		if (!this.view.is_editable()) object = null;
		this.viewer.placement.select(object);
		if (!this.selected) {
			this.hide_toolbar();
			return;
		}

		const { node_id, index } = this.selected.userData;
		this.view.highlight_nodes([node_id]);
		if (!object) return;

		const part = this.view.get_part(node_id);
		const label = __("{0}: placement {1} of {2}", [this.get_label(node_id), index + 1, flt(part.qty)]);
		this.show_toolbar(label, ["translate", "rotate", "remove", "done"]);
	}

	save(object) {
		if (!object) return;
		const part = this.view.get_part(object.userData.node_id);
		const placements = get_placements(part);
		placements[object.userData.index] = this.viewer.placement.get_placement(object);
		this.write(part, placements, true);
	}

	remove() {
		const { node_id, index } = this.selected.userData;
		const part = this.view.get_part(node_id);
		const placements = get_placements(part);
		placements.splice(index, 1);
		this.select(null);
		this.write(part, placements);
	}

	write(part, placements, keep_objects = false) {
		part.placements = JSON.stringify(placements);
		if (keep_objects) this.viewer.placement.key = this.viewer.placement.get_key(this.get_parts());
		this.frm.dirty();
		this.view.render();
	}

	finish() {
		this.viewer.on_place = null;
		this.select(null);
	}

	handle_action(action) {
		const actions = {
			translate: () => this.viewer.placement.set_mode("translate"),
			rotate: () => this.viewer.placement.set_mode("rotate"),
			remove: () => this.remove(),
			done: () => this.finish(),
			cancel: () => this.finish(),
		};
		actions[action]?.();
	}

	show_toolbar(text, actions) {
		const buttons = {
			translate: { label: __("Move"), icon: "move" },
			rotate: { label: __("Rotate"), icon: "rotate-3d" },
			remove: { label: __("Remove"), icon: "trash-2" },
			done: { label: __("Done"), icon: "check" },
			cancel: { label: __("Cancel"), icon: "x" },
		};
		const html = actions.map((action) =>
			frappe.ui.button.html({ ...buttons[action], size: "sm", attrs: { "data-placement": action } })
		);
		this.toolbar
			.html(
				`<span class="small ellipsis" style="flex:1;min-width:120px;">${frappe.utils.escape_html(
					text
				)}</span>
				${html.join("")}`
			)
			.css("display", "flex");
	}

	hide_toolbar() {
		this.toolbar?.css("display", "none");
	}

	get_label(node_id) {
		return this.view.get_node_label(node_id);
	}
}

export function get_placements(part) {
	if (!part.placements) return [];
	return typeof part.placements === "string" ? JSON.parse(part.placements) : [...part.placements];
}
