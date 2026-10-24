export function get_item_link_html(node_id, item_code) {
	const escape = frappe.utils.escape_html;
	const label = item_code ? escape(item_code) : `<span class="text-muted">${__("Map Item")}</span>`;
	return `<span class="design-item-cell" data-part-node="${node_id}" style="width:130px;display:flex;min-width:0;">
		<button type="button" class="design-item-link form-control input-sm ellipsis" data-part-node="${node_id}"
			title="${escape(item_code || "")}">${label}</button></span>`;
}

export function open_item_link(cell, options) {
	return open_link_field(cell, {
		...options,
		doctype: "Item",
		placeholder: options.placeholder || __("Map Item"),
	});
}

export function open_link_field(
	cell,
	{ doctype, value, placeholder, on_change, get_new_item_values, focus = true, open_list = true }
) {
	let created_new_doc = false;
	const control = frappe.ui.form.make_control({
		parent: $(cell).empty(),
		df: {
			fieldtype: "Link",
			options: doctype,
			fieldname: frappe.scrub(doctype),
			placeholder,
			get_route_options_for_new_doc: () => {
				created_new_doc = true;
				return get_new_item_values?.() || {};
			},
			onchange: () => {
				const name = control.get_value();
				if (name && name !== value) on_change(name, created_new_doc);
			},
		},
		render_input: true,
		only_input: true,
	});
	control.set_input(value || "");
	keep_list_in_view(control.$input.get(0), control.awesomplete);
	if (!open_list) keep_list_closed_until_typing(control);
	if (focus) control.$input.trigger("focus");
	return control;
}

function keep_list_closed_until_typing(control) {
	let typed = false;
	control.$input.one("input", () => (typed = true));
	control.$input.on("awesomplete-open", () => {
		if (!typed) control.awesomplete.close();
	});
}

export function keep_list_in_view(input, awesomplete) {
	const close_on_scroll = (event) => {
		if (event.target !== awesomplete.ul) awesomplete.close();
	};

	$(input).on("awesomplete-open", () => {
		const bounds = input.getBoundingClientRect();
		const opens_up = window.innerHeight - bounds.bottom < 280 && bounds.top > 280;
		Object.assign(awesomplete.ul.style, {
			position: "fixed",
			left: `${bounds.left}px`,
			width: `${Math.max(bounds.width, 280)}px`,
			top: opens_up ? "auto" : `${bounds.bottom + 4}px`,
			bottom: opens_up ? `${window.innerHeight - bounds.top + 4}px` : "auto",
			maxHeight: "260px",
			overflowY: "auto",
			zIndex: 1050,
		});
		window.addEventListener("scroll", close_on_scroll, true);
	});
	$(input).on("awesomplete-close", () => window.removeEventListener("scroll", close_on_scroll, true));
}
