// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.ui.form.on("Pricing Scheme", {
	refresh(frm) {
		frm.trigger("setup_grids");
		frm.trigger("morph_tier_columns");
		frm.trigger("morph_trigger_scope");
		frm.trigger("morph_party_section");
		frm.trigger("update_scope_summary");
		frm.trigger("render_group_ladder");
		frm.trigger("render_dashboard");

		if (frm.is_new() && !(frm.doc.tiers || []).length) {
			frm.add_child("tiers", {});
			frm.refresh_field("tiers");
		}

		frm.add_custom_button(__("Test Pricing"), () => open_test_pricing_dialog(frm));
	},

	effect_type(frm) {
		frm.trigger("morph_tier_columns");
	},

	transaction_type(frm) {
		frm.trigger("morph_party_section");
		frm.trigger("refresh_overlaps");
		frm.trigger("render_group_ladder");
	},

	morph_party_section(frm) {
		set_section_label(
			frm,
			"party_section",
			frm.doc.transaction_type === "Buying" ? __("Suppliers") : __("Customers")
		);
	},

	applies_to(frm) {
		const all_items = frm.doc.applies_to === "All Items";
		let rows = frm.doc.trigger_scope || [];
		if (all_items) {
			rows.forEach((row) => {
				row.exclude = 1;
			});
		} else {
			frm.doc.trigger_scope = rows.filter((row) => row.scope_type !== "All Items");
		}
		frm.refresh_field("trigger_scope");
		frm.trigger("morph_trigger_scope");
		frm.trigger("update_scope_summary");
		frm.trigger("refresh_overlaps");
	},

	stacking_group(frm) {
		frm.trigger("refresh_overlaps");
		frm.trigger("render_group_ladder");
	},

	priority(frm) {
		frm.trigger("refresh_overlaps");
		frm.trigger("render_group_ladder");
	},

	valid_from(frm) {
		frm.trigger("refresh_overlaps");
	},

	valid_upto(frm) {
		frm.trigger("refresh_overlaps");
	},

	setup_grids(frm) {
		frm.fields_dict.trigger_scope.grid.set_multiple_add("value");
		frm.fields_dict.party_scope.grid.set_multiple_add("value");
		// section heads carry these labels; the grid's own label duplicates them
		["tiers", "benefit_scope", "party_scope"].forEach((field) =>
			frm.fields_dict[field].grid.wrapper.find(".control-label").first().hide()
		);
	},

	morph_tier_columns(frm) {
		// row-form visibility is depends_on-driven; this shapes the grid columns
		const grid = frm.fields_dict.tiers.grid;
		const list_columns = {
			Margin: ["min_qty", "max_qty", "margin_type", "value"],
			"Free Item": ["min_qty", "max_qty", "free_item", "free_qty"],
			"Header Discount": ["min_amount", "max_amount", "value"],
		}[frm.doc.effect_type] || ["min_qty", "max_qty", "value"];
		[
			"min_qty",
			"max_qty",
			"min_amount",
			"max_amount",
			"value",
			"margin_type",
			"free_item",
			"free_qty",
		].forEach((field) =>
			grid.update_docfield_property(field, "in_list_view", list_columns.includes(field) ? 1 : 0)
		);
		grid.update_docfield_property(
			"value",
			"label",
			{
				Rate: __("Rate"),
				"Discount Percentage": __("Discount %"),
				"Discount Amount": __("Discount Amount"),
				Margin: __("Margin Value"),
				"Header Discount": __("Discount % on Total"),
			}[frm.doc.effect_type] || __("Value")
		);
		set_section_label(
			frm,
			"tiers_section",
			{
				Rate: __("Fixed Rate Tiers"),
				"Discount Percentage": __("Percentage Discount Tiers"),
				"Discount Amount": __("Amount Discount Tiers"),
				Margin: __("Margin Tiers"),
				"Free Item": __("Free Item Tiers"),
				"Header Discount": __("Document Total Discount Tiers"),
			}[frm.doc.effect_type] || __("Offer")
		);
		const effect_description = {
			Rate: __("One row per quantity slab. Rate replaces the price list rate."),
			"Discount Percentage": __(
				"Enter the discount percent in the Discount % column, one row per quantity slab. Leave Min and Max Qty as 0 to always apply."
			),
			"Discount Amount": __(
				"Enter the per-unit discount amount, one row per quantity slab. Leave Min and Max Qty as 0 to always apply."
			),
			Margin: __("Margin added over the price list rate, one row per quantity slab."),
			"Free Item": __(
				"Free Qty per slab. Leave Free Item blank to give the purchased item itself. 'Per Every N Qty' repeats the freebie per dozen-style schemes."
			),
			"Header Discount": __("Discount percent applied on the document total."),
		}[frm.doc.effect_type];
		const band_note = __("Min is included, Max is not.");
		set_section_description(
			frm,
			"tiers_section",
			effect_description ? `${effect_description} ${band_note}` : ""
		);
		grid.reset_grid();
	},

	morph_trigger_scope(frm) {
		const all_items = get_applies_to(frm.doc) === "All Items";
		const grid = frm.fields_dict.trigger_scope.grid;
		grid.update_docfield_property("exclude", "hidden", all_items ? 1 : 0);
		set_grid_label(frm, "trigger_scope", all_items ? __("Exclusions") : __("Items"));
		if (!all_items && !(frm.doc.trigger_scope || []).length) {
			frm.add_child("trigger_scope", {});
			frm.refresh_field("trigger_scope");
		}
		grid.reset_grid();
	},

	update_scope_summary(frm) {
		const all_items = get_applies_to(frm.doc) === "All Items";
		const rows = frm.doc.trigger_scope || [];
		if (all_items && !rows.some((row) => row.value)) {
			set_grid_description(
				frm,
				"trigger_scope",
				__("Applies to every item. Add rows to exclude items, groups, or brands.")
			);
			return;
		}
		if (!all_items && !rows.some((row) => row.value && !row.exclude)) {
			set_grid_description(
				frm,
				"trigger_scope",
				__("Scheme never applies if empty. Add at least one include row.")
			);
			return;
		}
		frappe.call({
			method: "erpnext.accounts.services.pricing.pricing_overlaps.count_scope_items",
			args: { scheme: frm.doc },
			callback: ({ message }) => {
				set_grid_description(
					frm,
					"trigger_scope",
					__("Matches approximately {0} items (subtree, excludes applied).", [message])
				);
			},
		});
	},

	render_dashboard(frm) {
		if (frm.is_new()) return;
		frm.trigger("render_usage");
		frm.trigger("refresh_overlaps");
	},

	render_usage(frm) {
		frappe.call({
			method: "erpnext.accounts.services.pricing.pricing_overlaps.get_usage",
			args: { scheme: frm.doc.name },
			callback: ({ message: usage }) => {
				frm.dashboard.add_indicator(
					__("Applications: {0}", [usage.applications]),
					usage.applications ? "green" : "gray"
				);
				frm.dashboard.add_indicator(
					__("Discount given: {0}", [format_currency(usage.discount_given)]),
					"blue"
				);
				if (usage.cap_total_applications) {
					const capped = usage.applications >= usage.cap_total_applications;
					frm.dashboard.add_indicator(
						__("Used {0} of {1} times", [usage.applications, usage.cap_total_applications]),
						capped ? "red" : "orange"
					);
				}
			},
		});
	},

	render_group_ladder: frappe.utils.debounce((frm) => {
		if (!frm.doc.stacking_group) return;
		frappe.db
			.get_list("Pricing Scheme", {
				filters: {
					stacking_group: frm.doc.stacking_group,
					transaction_type: frm.doc.transaction_type,
					disabled: 0,
					name: ["!=", frm.doc.name || ""],
				},
				fields: ["name", "title", "priority"],
				order_by: "priority desc",
				limit: 20,
			})
			.then((schemes) => render_group_ladder(frm, schemes || []));
	}, 600),

	refresh_overlaps: frappe.utils.debounce((frm) => {
		frappe.call({
			method: "erpnext.accounts.services.pricing.pricing_overlaps.detect_overlaps",
			args: { scheme: frm.doc },
			callback: ({ message: overlaps }) => render_overlaps(frm, overlaps || []),
		});
	}, 600),
});

frappe.ui.form.on("Pricing Scheme Item Scope", {
	trigger_scope_add(frm, cdt, cdn) {
		if (get_applies_to(frm.doc) === "All Items") {
			frappe.model.set_value(cdt, cdn, "exclude", 1);
		}
	},
	scope_type(frm) {
		frm.trigger("update_scope_summary");
		frm.trigger("refresh_overlaps");
	},
	value(frm) {
		frm.trigger("update_scope_summary");
		frm.trigger("refresh_overlaps");
	},
	exclude(frm) {
		frm.trigger("update_scope_summary");
	},
	trigger_scope_remove(frm) {
		frm.trigger("update_scope_summary");
		frm.trigger("refresh_overlaps");
	},
});

frappe.ui.form.on("Pricing Scheme Party Scope", {
	value(frm) {
		frm.trigger("refresh_overlaps");
	},
});

function get_applies_to(doc) {
	// Documents saved before the applies_to field carried scope in rows only.
	if (doc.applies_to) return doc.applies_to;
	const has_all_items_row = (doc.trigger_scope || []).some(
		(row) => row.scope_type === "All Items" && !row.exclude
	);
	return has_all_items_row ? "All Items" : "Specific Items";
}

function set_grid_label(frm, fieldname, label) {
	// Grid labels, like descriptions, are only drawn once at creation.
	const grid = frm.fields_dict[fieldname].grid;
	grid.df.label = label;
	grid.wrapper.find(".control-label").first().text(label);
}

function set_section_label(frm, fieldname, label) {
	// Section.refresh() only toggles visibility, so a label set via
	// frm.set_df_property never reaches the rendered section head. Only the
	// head's text node is replaced: set_label() would wipe the collapse chevron.
	const section = frm.fields_dict[fieldname];
	section.df.label = label;
	const text_node = section.head.contents().filter((_, node) => node.nodeType === Node.TEXT_NODE)[0];
	if (text_node) {
		text_node.nodeValue = label;
	} else {
		section.set_label(label);
	}
}

function set_section_description(frm, fieldname, description) {
	// Sections render their description only once at creation, and only
	// when one is set in the schema.
	const section = frm.fields_dict[fieldname];
	section.df.description = description;
	if (!section.description_wrapper) {
		section.description_wrapper = $('<div class="col-sm-12 form-section-description"></div>').insertAfter(
			section.head
		);
	}
	section.description_wrapper.html(description).toggle(Boolean(description));
}

function set_grid_description(frm, fieldname, description) {
	// Grids render their description only once at creation (grid.js make()),
	// so frm.set_df_property never surfaces a description set later.
	const grid = frm.fields_dict[fieldname].grid;
	grid.df.description = description;
	$(grid.parent).find(".grid-description").html(description).toggle(Boolean(description));
}

function render_group_ladder(frm, schemes) {
	const group = frappe.utils.escape_html(frm.doc.stacking_group);
	if (!schemes.length) {
		set_section_description(
			frm,
			"composition_section",
			__("No other active {0} schemes in the {1} group.", [__(frm.doc.transaction_type), group])
		);
		return;
	}

	const mine = cint(frm.doc.priority);
	const lines = schemes.map((scheme) => {
		const priority = cint(scheme.priority);
		const link = `<a href="/app/pricing-scheme/${scheme.name}">${frappe.utils.escape_html(
			scheme.title || scheme.name
		)}</a>`;
		const verdict =
			priority > mine
				? __("wins over this scheme")
				: priority < mine
				? __("loses to this scheme")
				: __("ties with this scheme and will block saving on overlapping scope");
		return `<div>${link} (${__("priority {0}", [priority])}) ${verdict}.</div>`;
	});

	const used = [...new Set(schemes.map((scheme) => cint(scheme.priority)))].sort((a, b) => a - b);
	lines.push(
		`<div class="text-muted">${__("Priorities in use in {0}: {1}.", [group, used.join(", ")])}</div>`
	);
	set_section_description(frm, "composition_section", lines.join(""));
}

function render_overlaps(frm, overlaps) {
	// the dashboard DOM is rebuilt on form refresh, so a cached section ref can go stale
	if (!frm.overlap_section || !document.body.contains(frm.overlap_section[0])) {
		frm.overlap_section = frm.dashboard.add_section("", __("Overlapping Schemes"));
	}
	const body = frm.overlap_section;
	body.empty();

	// set_intro appends a banner per call; clear first so re-renders don't stack them
	frm.set_intro("");
	const conflict = overlaps.find((o) => o.severity === "conflict");
	if (conflict) {
		frm.set_intro(
			__("Conflicts with {0}: same offer group and priority. Saving will be blocked.", [
				`<a href="/app/pricing-scheme/${conflict.scheme}">${frappe.utils.escape_html(
					conflict.title
				)}</a>`,
			]),
			"red"
		);
	}

	if (!overlaps.length) {
		body.append(`<div class="text-muted">${__("No overlapping schemes.")}</div>`);
		frm.dashboard.show();
		return;
	}

	const colors = { conflict: "red", shadowed: "orange", wins: "orange", stacks: "blue" };
	overlaps.forEach((o) => {
		body.append(`
			<div class="flex align-center" style="gap: 8px; padding: 3px 0;">
				<span class="indicator ${colors[o.severity]}"></span>
				<a href="/app/pricing-scheme/${o.scheme}">${frappe.utils.escape_html(o.title)}</a>
				<span class="text-muted small">${frappe.utils.escape_html(o.detail)}</span>
			</div>`);
	});
	frm.dashboard.show();
}

function open_test_pricing_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Test Pricing"),
		size: "large",
		fields: [
			{ fieldname: "customer", fieldtype: "Link", options: "Customer", label: __("Customer") },
			{
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
				label: __("Company"),
				reqd: 1,
				default: frm.doc.company || frappe.defaults.get_user_default("Company"),
			},
			{ fieldname: "col1", fieldtype: "Column Break" },
			{
				fieldname: "transaction_date",
				fieldtype: "Date",
				label: __("Date"),
				default: frappe.datetime.get_today(),
			},
			{ fieldname: "coupon", fieldtype: "Link", options: "Coupon", label: __("Coupon") },
			{ fieldname: "sec1", fieldtype: "Section Break" },
			{
				fieldname: "items",
				fieldtype: "Table",
				label: __("Items"),
				cannot_add_rows: false,
				in_place_edit: true,
				fields: [
					{
						fieldname: "item_code",
						fieldtype: "Link",
						options: "Item",
						label: __("Item"),
						in_list_view: 1,
					},
					{ fieldname: "qty", fieldtype: "Float", label: __("Qty"), in_list_view: 1, default: 1 },
					{
						fieldname: "rate",
						fieldtype: "Currency",
						label: __("Rate (blank = price list)"),
						in_list_view: 1,
					},
				],
			},
			{ fieldname: "sec2", fieldtype: "Section Break" },
			{ fieldname: "results", fieldtype: "HTML" },
		],
		primary_action_label: __("Run"),
		primary_action(values) {
			frappe.call({
				method: "erpnext.accounts.services.pricing.pricing_preview.preview_pricing",
				args: {
					company: values.company,
					customer: values.customer,
					transaction_date: values.transaction_date,
					items: values.items || [],
					coupon: values.coupon,
				},
				callback: ({ message }) => render_preview(dialog, message),
			});
		},
	});
	dialog.show();
}

function render_preview(dialog, result) {
	const lines = (result.lines || [])
		.map(
			(l) => `<tr>
				<td>${frappe.utils.escape_html(l.item_code)}</td>
				<td class="text-right">${l.qty}</td>
				<td class="text-right">${format_currency(l.base_rate)}</td>
				<td class="text-right"><b>${format_currency(l.final_rate)}</b></td>
				<td class="small text-muted">${l.schemes.join(", ") || "-"}</td>
			</tr>`
		)
		.join("");
	const free = (result.free_items || [])
		.map(
			(f) =>
				`<tr><td>${frappe.utils.escape_html(f.item_code)}</td><td class="text-right">${
					f.qty
				}</td><td colspan="2" class="text-right">${__("Free")}</td><td class="small text-muted">${
					f.scheme
				}</td></tr>`
		)
		.join("");
	const trace = (result.trace || [])
		.map((t) => {
			const icon = t.status === "matched" ? "✓" : "✕";
			const cls = t.status === "matched" ? "text-success" : "text-muted";
			return `<div class="${cls} small">${icon} ${frappe.utils.escape_html(
				t.scheme
			)}: ${frappe.utils.escape_html(t.reason || t.status)}</div>`;
		})
		.join("");

	dialog.fields_dict.results.$wrapper.html(`
		<table class="table table-bordered table-sm">
			<thead><tr><th>${__("Item")}</th><th class="text-right">${__("Qty")}</th><th class="text-right">${__(
		"Base"
	)}</th><th class="text-right">${__("Final")}</th><th>${__("Schemes")}</th></tr></thead>
			<tbody>${lines}${free}</tbody>
		</table>
		<div style="margin-top: 8px;"><b class="small">${__("Trace")}</b>${
		trace || `<div class="text-muted small">${__("No candidate schemes.")}</div>`
	}</div>
	`);
}
