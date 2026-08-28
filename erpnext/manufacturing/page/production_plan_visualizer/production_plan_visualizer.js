frappe.pages["production-plan-visualizer"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Production Plan Visualizer"),
		single_column: true,
	});

	frappe.production_plan_visualizer = new erpnext.ProductionPlanVisualizer(page);
};

frappe.pages["production-plan-visualizer"].on_page_show = function () {
	const visualizer = frappe.production_plan_visualizer;
	if (visualizer && frappe.route_options && frappe.route_options.production_plan) {
		const plan = frappe.route_options.production_plan;
		frappe.route_options = null;
		visualizer.plan_field.set_value(plan);
	}
};

erpnext.ProductionPlanVisualizer = class ProductionPlanVisualizer {
	constructor(page) {
		this.page = page;
		this.data = null;
		this.active_tab = "plan";
		this.schedule_group = "item";
		this.schedule_scale = "day";
		this.body = $(this.page.body);
		this.make();
	}

	make() {
		this.body.html(`${this.styles()}<div class="ppv"></div>`);
		this.container = this.body.find(".ppv");
		this.make_plan_field();
		this.render_blank_state();
	}

	make_plan_field() {
		this.plan_field = this.page.add_field({
			fieldname: "production_plan",
			label: __("Production Plan"),
			fieldtype: "Link",
			options: "Production Plan",
			get_query: () => ({ filters: { docstatus: ["<", 2] } }),
			change: () => {
				const value = this.plan_field.get_value();
				if (value && value !== this.current_plan) {
					this.load(value);
				} else if (!value) {
					this.current_plan = null;
					this.render_blank_state();
				}
			},
		});
	}

	render_blank_state() {
		this.container.empty().append(
			frappe.ui.empty_state({
				icon: "layout-dashboard",
				title: __("Pick a Production Plan"),
				description: __("See its progress, sub-assemblies, materials and schedule in one place."),
				css_class: "ppv-blank",
			})
		);
	}

	load(plan) {
		this.current_plan = plan;
		this.render_skeleton();
		frappe
			.call({
				method: "erpnext.manufacturing.page.production_plan_visualizer.production_plan_visualizer.get_plan_overview",
				args: { production_plan: plan },
			})
			.then((r) => {
				if (this.current_plan !== plan) return;
				this.data = r.message;
				this.render();
			});
	}

	render_skeleton() {
		const line = (w, h) => frappe.ui.skeleton.html({ width: w, height: h });
		this.container.html(`
			<div class="ppv-hero">
				<div class="ppv-hero-main">
					${line("240px", "28px")}
					<div class="mt-2">${line("180px", "14px")}</div>
					<div class="mt-4">${line("100%", "8px")}</div>
				</div>
				<div class="ppv-stats">
					${[1, 2, 3, 4].map(() => `<div class="ppv-tile">${line("100%", "48px")}</div>`).join("")}
				</div>
			</div>
			<div class="mt-4">${line("100%", "220px")}</div>
		`);
	}

	render() {
		this.container.empty();
		this.render_hero();
		this.render_tabs();
		this.panel = $('<div class="ppv-panel"></div>').appendTo(this.container);
		this.render_active_panel();
	}

	render_hero() {
		const plan = this.data.plan;
		const hero = $(`
			<div class="ppv-hero">
				<div class="ppv-hero-main">
					<div class="ppv-hero-title">
						<a class="ppv-plan-link" href="/app/production-plan/${encodeURIComponent(plan.name)}">
							${frappe.utils.escape_html(plan.name)}</a>
						<span class="ppv-hero-badge"></span>
					</div>
					<div class="ppv-hero-meta">
						${frappe.utils.escape_html(plan.company)} &middot;
						${frappe.datetime.str_to_user(plan.posting_date)}
					</div>
					<div class="ppv-hero-progress"></div>
				</div>
				<div class="ppv-hero-ring"></div>
				<div class="ppv-stats"></div>
			</div>
		`);

		hero.find(".ppv-hero-badge").append(this.status_badge(plan.status, "md"));
		hero.find(".ppv-hero-progress").append(
			frappe.ui.progress({
				value: plan.completion,
				size: "md",
				label: __("{0} of {1} produced", [
					this.format_float(plan.total_produced_qty),
					this.format_float(plan.total_planned_qty),
				]),
				hint: true,
			})
		);
		hero.find(".ppv-hero-ring").html(this.completion_ring(plan.completion));
		hero.find(".ppv-stats").html(this.stat_tiles());
		this.container.append(hero);
	}

	completion_ring(completion) {
		const radius = 44;
		const circumference = 2 * Math.PI * radius;
		const offset = circumference * (1 - Math.min(completion, 100) / 100);
		return `
			<svg viewBox="0 0 110 110" class="ppv-ring">
				<circle class="ppv-ring-track" cx="55" cy="55" r="${radius}"></circle>
				<circle class="ppv-ring-fill" cx="55" cy="55" r="${radius}"
					stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"></circle>
				<text x="55" y="52" class="ppv-ring-value">${Math.round(completion)}%</text>
				<text x="55" y="70" class="ppv-ring-caption">${__("Complete")}</text>
			</svg>
		`;
	}

	stat_tiles() {
		const documents = this.all_documents();
		const tiles = [
			this.stat_tile(
				__("Work Orders"),
				documents.filter((d) => d.doctype === "Work Order")
			),
			this.stat_tile(
				__("Purchase Orders"),
				documents.filter((d) => d.doctype === "Purchase Order")
			),
			this.stat_tile(__("Material Requests"), this.data.material_requests),
			this.schedule_tile(),
		];
		return tiles.join("");
	}

	stat_tile(label, docs) {
		const status_dots = Object.entries(this.group_rows(docs, (d) => d.status || __("Draft")))
			.map(
				([status, rows]) =>
					`<span class="ppv-dot-item" title="${frappe.utils.escape_html(status)}">
						<span class="ppv-dot" data-theme="${this.status_theme(status)}"></span>${rows.length}
					</span>`
			)
			.join("");
		return `
			<div class="ppv-tile">
				<div class="ppv-tile-value">${docs.length}</div>
				<div class="ppv-tile-label">${frappe.utils.escape_html(label)}</div>
				<div class="ppv-tile-dots">${status_dots}</div>
			</div>
		`;
	}

	schedule_tile() {
		const blocks = this.data.schedule || [];
		const workstations = new Set(blocks.map((d) => d.workstation).filter(Boolean));
		const caption = workstations.size
			? __("{0} workstations", [workstations.size])
			: __("Not scheduled yet");
		return `
			<div class="ppv-tile">
				<div class="ppv-tile-value">${blocks.length}</div>
				<div class="ppv-tile-label">${__("Schedule Blocks")}</div>
				<div class="ppv-tile-dots">${frappe.utils.escape_html(caption)}</div>
			</div>
		`;
	}

	all_documents() {
		const rows = [...this.data.finished_goods, ...this.data.sub_assemblies];
		return rows.flatMap((row) => row.documents || []);
	}

	group_rows(rows, key_fn) {
		return rows.reduce((groups, row) => {
			const key = key_fn(row);
			(groups[key] = groups[key] || []).push(row);
			return groups;
		}, {});
	}

	render_tabs() {
		this.container.append(
			$('<div class="ppv-tabs"></div>').append(
				frappe.ui.tab_buttons({
					label: __("Sections"),
					type: "ghost",
					value: this.active_tab,
					options: [
						{ label: __("Plan"), value: "plan" },
						{
							label: `${__("Schedule")} (${(this.data.schedule || []).length})`,
							value: "schedule",
						},
					],
					on_change: (value) => {
						this.active_tab = value;
						this.render_active_panel();
					},
				})
			)
		);
	}

	render_active_panel() {
		this.panel.empty();
		if (this.active_tab === "plan") this.render_plan_tree();
		else this.render_schedule();
	}

	render_plan_tree() {
		if (!this.data.finished_goods.length) {
			this.panel_empty_state(__("No items to manufacture in this plan"));
			return;
		}
		this.panel.append(this.plan_search_bar());
		this.tree_list = $('<div class="ppv-tree"></div>').appendTo(this.panel);
		const subs_by_parent = this.group_rows(this.data.sub_assemblies, (d) => d.production_plan_item);
		const assignments = this.material_assignments();

		for (const fg of this.data.finished_goods) {
			const branch = $('<div class="ppv-branch"></div>');
			for (const sub of subs_by_parent[fg.row_name] || []) {
				const indent = sub.indent || 0;
				branch.append(this.sub_assembly_row(sub));
				for (const material of assignments.map[sub.row_name] || []) {
					branch.append(this.material_row(material, indent + 1));
				}
			}
			delete subs_by_parent[fg.row_name];
			for (const material of assignments.map[fg.row_name] || []) {
				branch.append(this.material_row(material, 0));
			}
			const node = this.plan_node(fg, branch);
			node.attr("data-search", node.text().toLowerCase());
			this.tree_list.append(node);
		}

		this.append_plan_group(__("Other Sub Assemblies"), Object.values(subs_by_parent).flat(), (d) =>
			this.sub_assembly_row(d)
		);
		this.append_plan_group(__("Other Materials"), assignments.leftovers, (d) => this.material_row(d, 0));

		this.no_results = frappe.ui.empty_state({ icon: "search", title: __("No matching items") }).hide();
		this.panel.append(this.no_results);
		this.apply_plan_filter();
	}

	append_plan_group(label, rows, make_row) {
		if (!rows.length) return;
		const group = $('<div class="ppv-group"></div>').append(
			`<div class="ppv-group-head">${frappe.utils.escape_html(label)}</div>`
		);
		for (const row of rows) {
			const el = make_row(row);
			el.attr("data-search", el.text().toLowerCase());
			group.append(el);
		}
		this.tree_list.append(group);
	}

	plan_search_bar() {
		const bar = $(`
			<div class="ppv-search">
				<span class="ppv-search-icon">${frappe.utils.icon("search", "sm", "", "", "", true)}</span>
				<input type="search" class="ppv-search-input"
					placeholder="${__("Search item, code or document...")}" />
				<span class="ppv-search-count"></span>
			</div>
		`);
		this.search_input = bar.find("input");
		this.search_count = bar.find(".ppv-search-count");
		this.search_input.val(this.plan_search || "");
		this.search_input.on("input", () => {
			this.plan_search = this.search_input.val();
			this.apply_plan_filter();
		});
		return bar;
	}

	apply_plan_filter() {
		const query = (this.plan_search || "").trim().toLowerCase();
		const matches = (el) => !query || ($(el).attr("data-search") || "").includes(query);
		let visible = 0;
		let total = 0;

		this.tree_list.children(".ppv-node").each((_, el) => {
			total += 1;
			const show = matches(el);
			$(el).toggle(show);
			if (show) visible += 1;
		});

		let group_visible = 0;
		this.tree_list.children(".ppv-group").each((_, group) => {
			let shown = 0;
			$(group)
				.children("[data-search]")
				.each((_, el) => {
					const show = matches(el);
					$(el).toggle(show);
					if (show) shown += 1;
				});
			$(group).toggle(shown > 0);
			group_visible += shown;
		});

		this.search_count.text(query ? __("{0} of {1} items", [visible, total]) : "");
		this.no_results.toggle(Boolean(query) && !visible && !group_visible);
	}

	plan_node(fg, branch) {
		const node = $('<div class="ppv-node"></div>');
		const card = this.item_card(fg, { show_dates: true });
		node.append(card);
		if (!branch.children().length) return node;

		node.append(branch);
		const caret = frappe.ui.button({
			icon: "chevron-down",
			variant: "ghost",
			size: "sm",
			title: __("Collapse"),
			css_class: "ppv-caret",
			onclick: () => {
				branch.slideToggle(150);
				caret.toggleClass("ppv-collapsed");
			},
		});
		card.find(".ppv-card-head").prepend(caret);
		return node;
	}

	material_assignments() {
		const row_materials = this.data.row_materials || {};
		const bom_consumers = {};
		for (const [row_name, items] of Object.entries(row_materials)) {
			for (const item of items) {
				(bom_consumers[item] = bom_consumers[item] || []).push(row_name);
			}
		}

		const map = {};
		const leftovers = [];
		for (const material of this.data.materials || []) {
			const consumers = material.consumers.length
				? material.consumers
				: bom_consumers[material.item_code] || [];
			if (consumers.length) {
				(map[consumers[0]] = map[consumers[0]] || []).push(material);
			} else {
				leftovers.push(material);
			}
		}
		return { map, leftovers };
	}

	material_row(material, indent) {
		const completion = material.quantity ? (material.ordered_qty / material.quantity) * 100 : 0;
		const el = $(`
			<div class="ppv-sub-row ppv-material-row" style="--ppv-indent: ${indent}">
				<div class="ppv-sub-item">
					<div class="ppv-sub-title">
						<a href="/app/item/${encodeURIComponent(material.item_code)}">
							${frappe.utils.escape_html(material.item_name || material.item_code)}</a>
						<span class="ppv-sub-type"></span>
					</div>
					<div class="ppv-card-sub">${frappe.utils.escape_html(material.item_code)}</div>
				</div>
				<div class="ppv-qty-row ppv-qty-compact">
					${this.qty_cell(__("Planned"), material.quantity)}
					${this.qty_cell(__("Requested"), material.requested_qty)}
					${this.qty_cell(__("Ordered"), material.ordered_qty)}
				</div>
				<div class="ppv-sub-progress"></div>
				<div class="ppv-chips"></div>
			</div>
		`);
		el.find(".ppv-sub-type").append(
			frappe.ui.badge({
				label: __(material.material_request_type || "Material"),
				size: "sm",
				variant: "ghost",
			})
		);
		el.find(".ppv-sub-progress").append(frappe.ui.progress({ value: completion, hint: true }));
		this.append_document_chips(el.find(".ppv-chips"), material.documents);
		return el;
	}

	item_card(row, { show_dates } = {}) {
		const completion = row.qty ? (row.produced_qty / row.qty) * 100 : 0;
		const card = $(`
			<div class="ppv-card">
				<div class="ppv-card-head">
					<div>
						<div class="ppv-card-title">
							<a href="/app/item/${encodeURIComponent(row.item_code)}">
								${frappe.utils.escape_html(row.item_name || row.item_code)}</a>
						</div>
						<div class="ppv-card-sub">${frappe.utils.escape_html(row.item_code)}</div>
					</div>
					<div class="ppv-card-badges"></div>
				</div>
				<div class="ppv-qty-row">
					${this.qty_cell(__("Planned"), row.qty)}
					${this.qty_cell(__("Produced"), row.produced_qty)}
					${this.qty_cell(__("Pending"), row.pending_qty)}
				</div>
				<div class="ppv-card-progress"></div>
				<div class="ppv-chips"></div>
			</div>
		`);

		const badges = card.find(".ppv-card-badges");
		if (row.sales_order) {
			badges.append(frappe.ui.badge({ label: row.sales_order, theme: "violet", variant: "outline" }));
		}
		if (show_dates && row.planned_start_date) {
			badges.append(
				frappe.ui.badge({
					label: frappe.datetime.str_to_user(row.planned_start_date.split(" ")[0]),
					icon: "calendar",
					variant: "ghost",
				})
			);
		}
		card.find(".ppv-card-progress").append(
			frappe.ui.progress({ value: completion, size: "md", hint: true })
		);
		this.append_document_chips(card.find(".ppv-chips"), row.documents);
		return card;
	}

	sub_assembly_row(row) {
		const completion = row.qty ? (row.produced_qty / row.qty) * 100 : 0;
		const el = $(`
			<div class="ppv-sub-row" style="--ppv-indent: ${row.indent}">
				<div class="ppv-sub-item">
					<div class="ppv-sub-title">
						<a href="/app/item/${encodeURIComponent(row.item_code)}">
							${frappe.utils.escape_html(row.item_name || row.item_code)}</a>
						<span class="ppv-sub-type"></span>
					</div>
					<div class="ppv-card-sub">${frappe.utils.escape_html(row.item_code)}</div>
				</div>
				<div class="ppv-qty-row ppv-qty-compact">
					${this.qty_cell(__("Planned"), row.qty)}
					${this.qty_cell(__("Done"), row.produced_qty)}
					${this.qty_cell(__("Pending"), row.pending_qty)}
				</div>
				<div class="ppv-sub-progress"></div>
				<div class="ppv-chips"></div>
			</div>
		`);
		el.find(".ppv-sub-type").append(
			frappe.ui.badge({
				label: __(row.type_of_manufacturing || "In House"),
				size: "sm",
				theme: row.type_of_manufacturing === "Subcontract" ? "amber" : "blue",
				variant: "outline",
			})
		);
		el.find(".ppv-sub-progress").append(frappe.ui.progress({ value: completion, hint: true }));
		this.append_document_chips(el.find(".ppv-chips"), row.documents);
		return el;
	}

	append_document_chips(target, documents) {
		if (!documents || !documents.length) {
			target.append(`<span class="ppv-no-docs">${__("No documents yet")}</span>`);
			return;
		}
		for (const doc of documents) {
			const route = `/app/${frappe.router.slug(doc.doctype)}/${encodeURIComponent(doc.name)}`;
			const label = doc.status ? `${doc.name} · ${__(doc.status)}` : doc.name;
			const icons = {
				"Purchase Order": "shopping-cart",
				"Material Request": "clipboard-list",
			};
			$(`<a class="ppv-chip-link" href="${route}"></a>`)
				.append(
					frappe.ui.badge({
						label: label,
						theme: this.status_theme(doc.status),
						icon: icons[doc.doctype] || "factory",
					})
				)
				.appendTo(target);
		}
	}

	render_schedule() {
		const blocks = this.data.schedule || [];
		if (!blocks.length) {
			this.panel_empty_state(
				__("No schedule yet — use Schedule Items on the Production Plan to build one")
			);
			return;
		}
		this.panel.append(this.schedule_toolbar());
		this.panel.append(this.schedule_timeline(blocks));
	}

	schedule_toolbar() {
		const toggle = (label, value, options, on_change) =>
			frappe.ui.tab_buttons({
				label,
				type: "subtle",
				size: "sm",
				value,
				options,
				on_change,
			});
		return $('<div class="ppv-schedule-toolbar"></div>')
			.append(
				toggle(
					__("Group by"),
					this.schedule_group,
					[
						{ label: __("By Item"), value: "item" },
						{ label: __("By Workstation"), value: "workstation" },
					],
					(value) => {
						this.schedule_group = value;
						this.render_active_panel();
					}
				)
			)
			.append(
				toggle(
					__("Scale"),
					this.schedule_scale,
					[
						{ label: __("Day"), value: "day" },
						{ label: __("Hour"), value: "hour" },
					],
					(value) => {
						this.schedule_scale = value;
						this.render_active_panel();
					}
				)
			);
	}

	schedule_timeline(blocks) {
		const raw_start = Math.min(...blocks.map((d) => frappe.datetime.str_to_obj(d.from_time).getTime()));
		const raw_end = Math.max(...blocks.map((d) => frappe.datetime.str_to_obj(d.to_time).getTime()));
		const axis = this.timeline_ticks(raw_start, raw_end);
		const span = Math.max(axis.end - axis.start, 1);

		const timeline = $(
			`<div class="ppv-timeline" style="--ppv-ticks: ${axis.ticks.length}; --ppv-tick-w: ${axis.tick_width}"></div>`
		);
		timeline.append(`
			<div class="ppv-timeline-header">
				<div class="ppv-timeline-label">${__("Timeline")}</div>
				<div class="ppv-axis">${axis.ticks
					.map((tick) => `<div class="ppv-axis-tick">${frappe.utils.escape_html(tick)}</div>`)
					.join("")}</div>
			</div>
		`);
		for (const descriptor of this.schedule_rows(blocks)) {
			timeline.append(this.timeline_row(descriptor, axis.start, span));
		}
		return $('<div class="ppv-timeline-scroll"></div>').append(timeline);
	}

	timeline_ticks(start, end) {
		const hour_ms = 3600000;
		if (this.schedule_scale === "hour") {
			const span_hours = Math.max((end - start) / hour_ms, 1);
			const step = span_hours <= 24 ? 1 : span_hours <= 72 ? 3 : span_hours <= 240 ? 6 : 12;
			const first = new Date(start);
			first.setMinutes(0, 0, 0);
			first.setHours(Math.floor(first.getHours() / step) * step);
			const ticks = [];
			for (let time = first.getTime(); time < end; time += step * hour_ms) {
				const date = new Date(time);
				ticks.push(
					date.getHours() === 0
						? frappe.datetime.obj_to_user(date).slice(0, 5)
						: `${String(date.getHours()).padStart(2, "0")}:00`
				);
			}
			return {
				ticks,
				start: first.getTime(),
				end: first.getTime() + ticks.length * step * hour_ms,
				tick_width: "72px",
			};
		}
		const first = new Date(start);
		first.setHours(0, 0, 0, 0);
		const ticks = [];
		for (let time = first.getTime(); time < end; time += 24 * hour_ms) {
			ticks.push(frappe.datetime.obj_to_user(new Date(time)).slice(0, 5));
		}
		return {
			ticks,
			start: first.getTime(),
			end: first.getTime() + ticks.length * 24 * hour_ms,
			tick_width: "96px",
		};
	}

	schedule_rows(blocks) {
		if (this.schedule_group === "workstation") {
			const groups = this.group_rows(blocks, (d) => d.workstation || d.supplier || __("Unassigned"));
			return Object.entries(groups).map(([label, rows]) => ({
				label,
				indent: 0,
				blocks: rows,
			}));
		}
		return this.schedule_tree(blocks);
	}

	schedule_tree(blocks) {
		const by_row = this.group_rows(blocks, (d) => d.plan_row || "");
		const material_blocks = this.group_rows(
			blocks.filter((d) => d.row_type === "Raw Material"),
			(d) => d.item_code
		);
		const row_materials = this.data.row_materials || {};
		const subs_by_parent = this.group_rows(this.data.sub_assemblies, (d) => d.production_plan_item);
		const used_materials = new Set();
		const used_rows = new Set();

		const material_rows = (row_name, indent) =>
			(row_materials[row_name] || []).flatMap((item) => {
				if (used_materials.has(item) || !material_blocks[item]) return [];
				used_materials.add(item);
				const rows = material_blocks[item];
				return [{ label: rows[0].item_name || item, indent, blocks: rows }];
			});

		const out = [];
		for (const fg of this.data.finished_goods) {
			used_rows.add(fg.row_name);
			const branch = [];
			for (const sub of subs_by_parent[fg.row_name] || []) {
				used_rows.add(sub.row_name);
				const indent = 1 + (sub.indent || 0);
				const sub_blocks = by_row[sub.row_name] || [];
				const children = material_rows(sub.row_name, indent + 1);
				if (sub_blocks.length || children.length) {
					branch.push(
						{ label: sub.item_name || sub.item_code, indent, blocks: sub_blocks },
						...children
					);
				}
			}
			branch.push(...material_rows(fg.row_name, 1));
			const fg_blocks = by_row[fg.row_name] || [];
			if (fg_blocks.length || branch.length) {
				out.push({ label: fg.item_name || fg.item_code, indent: 0, blocks: fg_blocks }, ...branch);
			}
		}

		const leftover = blocks.filter((d) =>
			d.row_type === "Raw Material" ? !used_materials.has(d.item_code) : !used_rows.has(d.plan_row)
		);
		for (const [label, rows] of Object.entries(
			this.group_rows(leftover, (d) => d.item_name || d.item_code || d.subject)
		)) {
			out.push({ label, indent: 0, blocks: rows });
		}
		return out;
	}

	timeline_row(descriptor, start, span) {
		const { label, indent, blocks } = descriptor;
		const row = $(`
			<div class="ppv-timeline-row" data-depth="${indent > 0 ? "child" : "root"}">
				<div class="ppv-timeline-label" style="--ppv-row-indent: ${indent}"
					title="${frappe.utils.escape_html(label)}">
					${indent > 0 ? '<span class="ppv-tree-branch">└</span>' : ""}
					${frappe.utils.escape_html(label)}</div>
				<div class="ppv-track"></div>
			</div>
		`);
		const track = row.find(".ppv-track");
		for (const block of blocks) {
			const from = frappe.datetime.str_to_obj(block.from_time).getTime();
			const to = frappe.datetime.str_to_obj(block.to_time).getTime();
			const left = ((from - start) / span) * 100;
			const width = Math.max(((to - from) / span) * 100, 0.6);
			const title = [
				block.subject,
				`${frappe.datetime.str_to_user(block.from_time)} → ${frappe.datetime.str_to_user(
					block.to_time
				)}`,
				block.workstation || block.supplier || "",
			]
				.filter(Boolean)
				.join("\n");
			$(`<a class="ppv-block" data-row-type="${frappe.utils.escape_html(block.row_type || "")}"
				style="left: ${left}%; width: ${width}%"
				href="/app/production-plan-schedule/${encodeURIComponent(block.name)}"
				title="${frappe.utils.escape_html(title)}">
				<span>${frappe.utils.escape_html(block.operation || block.item_name || block.subject || "")}</span>
			</a>`).appendTo(track);
		}
		return row;
	}

	qty_cell(label, value, { integer } = {}) {
		return `
			<div class="ppv-qty-cell">
				<div class="ppv-qty-label">${frappe.utils.escape_html(label)}</div>
				<div class="ppv-qty-value">${integer ? cint(value) : this.format_float(value)}</div>
			</div>
		`;
	}

	format_float(value) {
		return format_number(flt(value));
	}

	status_badge(status, size) {
		return frappe.ui.badge({
			label: __(status || "Draft"),
			theme: this.status_theme(status),
			size: size || "md",
		});
	}

	status_theme(status) {
		const themes = {
			Completed: "green",
			Transferred: "green",
			Received: "green",
			Ordered: "green",
			"In Process": "blue",
			Submitted: "blue",
			"In Progress": "blue",
			Pending: "amber",
			"Not Started": "amber",
			"Partially Ordered": "amber",
			"Partially Received": "amber",
			"To Receive and Bill": "amber",
			"To Receive": "amber",
			"To Bill": "amber",
			Stopped: "red",
			Cancelled: "red",
			Draft: "gray",
			Closed: "gray",
			"On Hold": "gray",
		};
		return themes[status] || "gray";
	}

	panel_empty_state(title) {
		this.panel.append(
			frappe.ui.empty_state({
				icon: "inbox",
				title: title,
				css_class: "ppv-panel-empty",
			})
		);
	}

	styles() {
		return `<style>
			.ppv { max-width: 1100px; margin: 0 auto; padding-bottom: var(--padding-2xl); }
			.ppv-blank, .ppv-panel-empty { min-height: 320px; }

			.ppv-hero {
				display: grid;
				grid-template-columns: 1fr auto;
				gap: var(--padding-lg) var(--padding-2xl);
				background: var(--card-bg, var(--fg-color));
				border: 1px solid var(--border-color);
				border-radius: var(--border-radius-lg);
				padding: var(--padding-xl);
				margin-top: var(--padding-md);
			}
			.ppv-hero-title { display: flex; align-items: center; gap: 10px; }
			.ppv-plan-link {
				font-size: var(--text-xl);
				font-weight: 600;
				color: var(--heading-color);
				text-decoration: none;
			}
			.ppv-hero-meta { color: var(--text-muted); margin-top: 2px; font-size: var(--text-sm); }
			.ppv-hero-progress { margin-top: var(--padding-lg); max-width: 460px; }

			.ppv-ring { width: 110px; height: 110px; }
			.ppv-ring-track { fill: none; stroke: var(--bg-color); stroke-width: 10; }
			.ppv-ring-fill {
				fill: none;
				stroke: var(--primary);
				stroke-width: 10;
				stroke-linecap: round;
				transform: rotate(-90deg);
				transform-origin: 55px 55px;
				transition: stroke-dashoffset 0.6s ease;
			}
			.ppv-ring-value {
				text-anchor: middle;
				font-size: 22px;
				font-weight: 700;
				fill: var(--heading-color);
			}
			.ppv-ring-caption { text-anchor: middle; font-size: 10px; fill: var(--text-muted); }

			.ppv-stats {
				grid-column: 1 / -1;
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
				gap: var(--padding-md);
				border-top: 1px solid var(--border-color);
				padding-top: var(--padding-lg);
			}
			.ppv-tile-value {
				font-size: var(--text-2xl);
				font-weight: 700;
				color: var(--heading-color);
				font-variant-numeric: tabular-nums;
			}
			.ppv-tile-label {
				font-size: var(--text-xs);
				text-transform: uppercase;
				letter-spacing: 0.05em;
				color: var(--text-muted);
				margin-top: 2px;
			}
			.ppv-tile-dots {
				display: flex; gap: 10px; margin-top: 6px;
				font-size: var(--text-xs); color: var(--text-muted);
			}
			.ppv-dot-item { display: inline-flex; align-items: center; gap: 4px; }
			.ppv-dot { width: 7px; height: 7px; border-radius: 999px; background: var(--gray-400); }
			.ppv-dot[data-theme="green"] { background: var(--green-500); }
			.ppv-dot[data-theme="blue"] { background: var(--blue-500); }
			.ppv-dot[data-theme="amber"] { background: var(--yellow-500); }
			.ppv-dot[data-theme="red"] { background: var(--red-500); }

			.ppv-tabs { margin: var(--padding-lg) 0 var(--padding-md); }

			.ppv-search {
				display: flex;
				align-items: center;
				gap: 8px;
				max-width: 380px;
				margin-bottom: var(--padding-md);
				background: var(--fg-color);
				border: 1px solid var(--border-color);
				border-radius: var(--border-radius);
				padding: 6px 10px;
			}
			.ppv-search:focus-within { border-color: var(--primary); }
			.ppv-search-icon { display: flex; color: var(--text-muted); }
			.ppv-search-input {
				flex: 1;
				border: none;
				outline: none;
				background: transparent;
				font-size: var(--text-md);
				color: var(--text-color);
			}
			.ppv-search-count {
				color: var(--text-muted);
				font-size: var(--text-xs);
				white-space: nowrap;
			}

			.ppv-node { margin-bottom: var(--padding-md); }
			.ppv-node > .ppv-card { margin-bottom: 0; }
			.ppv-branch {
				margin: var(--padding-sm) 0 0 var(--padding-xl);
				padding-left: var(--padding-lg);
				border-left: 2px solid var(--border-color);
			}
			.ppv-caret { margin-right: 4px; align-self: flex-start; }
			.ppv-caret svg { transition: transform 0.15s ease; }
			.ppv-caret.ppv-collapsed svg { transform: rotate(-90deg); }
			.ppv-material-row { border-style: dashed; }
			.ppv-material-row .ppv-sub-title a { font-weight: 500; }

			.ppv-card {
				background: var(--card-bg, var(--fg-color));
				border: 1px solid var(--border-color);
				border-radius: var(--border-radius-lg);
				padding: var(--padding-lg);
				margin-bottom: var(--padding-md);
				transition: box-shadow 0.15s ease;
			}
			.ppv-card:hover { box-shadow: var(--shadow-sm); }
			.ppv-card-head { display: flex; gap: var(--padding-md); }
			.ppv-card-head .ppv-card-badges { margin-left: auto; }
			.ppv-card-title a { color: var(--heading-color); font-weight: 600; text-decoration: none; }
			.ppv-card-sub { color: var(--text-muted); font-size: var(--text-sm); margin-top: 1px; }
			.ppv-card-badges { display: flex; gap: 6px; align-items: flex-start; flex-wrap: wrap; }
			.ppv-card-progress { margin-top: var(--padding-sm); max-width: 460px; }

			.ppv-qty-row {
				display: flex;
				gap: var(--padding-2xl);
				margin-top: var(--padding-md);
				justify-content: flex-end;
			}
			.ppv-qty-cell { text-align: right; min-width: 90px; }
			.ppv-qty-label {
				font-size: var(--text-xs);
				text-transform: uppercase;
				letter-spacing: 0.05em;
				color: var(--text-muted);
				text-align: right;
			}
			.ppv-qty-value {
				font-size: var(--text-lg);
				font-weight: 600;
				color: var(--heading-color);
				font-variant-numeric: tabular-nums;
				text-align: right;
			}
			.ppv-qty-compact .ppv-qty-value { font-size: var(--text-base); }
			.ppv-qty-compact { gap: var(--padding-lg); margin-top: 0; }

			.ppv-chips {
				display: flex; flex-wrap: wrap; gap: 6px;
				margin-top: var(--padding-md);
			}
			.ppv-chip-link { text-decoration: none; }
			.ppv-no-docs { color: var(--text-muted); font-size: var(--text-sm); }

			.ppv-group-head {
				font-size: var(--text-xs);
				text-transform: uppercase;
				letter-spacing: 0.05em;
				color: var(--text-muted);
				margin: var(--padding-lg) 0 var(--padding-sm);
			}
			.ppv-sub-row {
				display: grid;
				grid-template-columns: minmax(220px, 1.2fr) auto minmax(140px, 0.8fr);
				gap: var(--padding-sm) var(--padding-xl);
				align-items: center;
				background: var(--card-bg, var(--fg-color));
				border: 1px solid var(--border-color);
				border-radius: var(--border-radius-lg);
				padding: var(--padding-md) var(--padding-lg);
				margin-bottom: var(--padding-sm);
				margin-left: calc(var(--ppv-indent, 0) * 24px);
			}
			.ppv-sub-title { display: flex; align-items: center; gap: 8px; }
			.ppv-sub-title a { color: var(--heading-color); font-weight: 600; text-decoration: none; }
			.ppv-sub-row .ppv-chips { grid-column: 1 / -1; margin-top: 0; }

			.ppv-schedule-toolbar {
				display: flex;
				gap: var(--padding-md);
				flex-wrap: wrap;
				margin-bottom: var(--padding-md);
			}
			.ppv-timeline-scroll { overflow-x: auto; border: 1px solid var(--border-color);
				border-radius: var(--border-radius-lg); background: var(--card-bg, var(--fg-color)); }
			.ppv-timeline { min-width: calc(220px + var(--ppv-ticks) * var(--ppv-tick-w, 96px)); }
			.ppv-timeline-header, .ppv-timeline-row {
				display: grid;
				grid-template-columns: 220px 1fr;
				border-bottom: 1px solid var(--border-color);
			}
			.ppv-timeline-row:last-child { border-bottom: none; }
			.ppv-timeline-label {
				padding: var(--padding-md) var(--padding-lg);
				padding-left: calc(var(--padding-lg) + var(--ppv-row-indent, 0) * 18px);
				font-weight: 600;
				color: var(--heading-color);
				border-right: 1px solid var(--border-color);
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.ppv-timeline-row[data-depth="child"] .ppv-timeline-label {
				font-weight: 400;
				color: var(--text-color);
			}
			.ppv-tree-branch { color: var(--text-muted); margin-right: 4px; }
			.ppv-axis { display: grid; grid-template-columns: repeat(var(--ppv-ticks), 1fr); }
			.ppv-axis-tick {
				padding: var(--padding-md) 8px;
				font-size: var(--text-xs);
				color: var(--text-muted);
				border-right: 1px dashed var(--border-color);
				white-space: nowrap;
			}
			.ppv-track {
				position: relative;
				min-height: 44px;
				background-image: repeating-linear-gradient(
					to right,
					transparent,
					transparent calc(100% / var(--ppv-ticks) - 1px),
					var(--border-color) calc(100% / var(--ppv-ticks) - 1px),
					var(--border-color) calc(100% / var(--ppv-ticks))
				);
			}
			.ppv-block {
				position: absolute;
				top: 8px;
				height: 28px;
				border-radius: var(--border-radius);
				background: var(--blue-100);
				border: 1px solid var(--blue-300);
				color: var(--blue-700);
				font-size: var(--text-xs);
				line-height: 26px;
				padding: 0 8px;
				overflow: hidden;
				white-space: nowrap;
				text-overflow: ellipsis;
				text-decoration: none;
			}
			.ppv-block:hover { filter: brightness(0.97); text-decoration: none; }
			.ppv-block[data-row-type="Finished Good"] {
				background: var(--purple-100); border-color: var(--purple-300); color: var(--purple-700);
			}
			.ppv-block[data-row-type="Raw Material"] {
				background: var(--yellow-100); border-color: var(--yellow-300); color: var(--yellow-700);
			}

			@media (max-width: 768px) {
				.ppv-hero { grid-template-columns: 1fr; }
				.ppv-hero-ring { display: none; }
				.ppv-qty-row { gap: var(--padding-lg); }
				.ppv-sub-row { grid-template-columns: 1fr; }
			}
		</style>`;
	}
};
