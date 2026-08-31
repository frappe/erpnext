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
	if (!visualizer) return;
	if (frappe.route_options && frappe.route_options.production_plan) {
		const plan = frappe.route_options.production_plan;
		frappe.route_options = null;
		visualizer.plan_field.set_value(plan);
	}
	visualizer.fit_viewport();
};

erpnext.ProductionPlanVisualizer = class ProductionPlanVisualizer {
	constructor(page) {
		this.page = page;
		this.data = null;
		this.focus = "all";
		this.active_tab = "manufacture";
		this.schedule_group = "item";
		this.schedule_scale = "day";
		this.today_offset = null;
		this.body = $(this.page.body);
		this.make();
	}

	make() {
		$(this.page.wrapper).addClass("ppv-page").find(".page-head").css("border-bottom", "none");
		this.body.html(`${this.styles()}<div class="ppv"></div>`);
		this.container = this.body.find(".ppv");
		this.make_plan_field();
		$(window).on(
			"resize.ppv",
			frappe.utils.debounce(() => this.fit_viewport(), 150)
		);
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

	fit_viewport() {
		if (!this.container || !this.container.is(":visible")) return;
		const top = this.container[0].getBoundingClientRect().top;
		const height = Math.max(window.innerHeight - top - 20, 460);
		this.container.css("height", `${height}px`);
	}

	render_blank_state() {
		this.container.empty().append(
			$('<div class="ppv-fill"></div>').append(
				frappe.ui.empty_state({
					icon: "layout-dashboard",
					title: __("Pick a Production Plan"),
					description: __(
						"Track readiness, shortages, work orders and the shop floor schedule on one screen."
					),
				})
			)
		);
		this.fit_viewport();
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
				this.focus = "all";
				this.active_tab = "manufacture";
				this.render();
			});
	}

	render_skeleton() {
		const line = (w, h) => frappe.ui.skeleton.html({ width: w, height: h });
		this.container.html(`
			<div class="ppv-kpis">
				${[1, 2, 3, 4, 5].map(() => `<div class="ppv-kpi">${line("100%", "44px")}</div>`).join("")}
			</div>
			<div class="ppv-workspace">
				<div class="ppv-pane"><div style="padding: 12px">${line("100%", "240px")}</div></div>
				<div class="ppv-pane"><div style="padding: 12px">${line("100%", "240px")}</div></div>
			</div>
		`);
		this.fit_viewport();
	}

	render() {
		this.build_index();
		this.container.empty();
		this.render_kpis();
		this.render_workspace();
		this.fit_viewport();
	}

	build_index() {
		this.data.schedule = (this.data.schedule || []).filter((d) => d.from_time && d.to_time);
		const subs_by_parent = this.group_rows(this.data.sub_assemblies, (d) => d.production_plan_item);
		const owner_of_row = {};
		for (const fg of this.data.finished_goods) {
			owner_of_row[fg.row_name] = fg.row_name;
			for (const sub of subs_by_parent[fg.row_name] || []) owner_of_row[sub.row_name] = fg.row_name;
		}

		const bom_consumers = {};
		for (const [row_name, items] of Object.entries(this.data.row_materials || {})) {
			for (const item of items) (bom_consumers[item] = bom_consumers[item] || []).push(row_name);
		}

		const subs_by_signature = {};
		for (const sub of this.data.sub_assemblies) {
			const key = `${sub.item_code}::${sub.bom_no || ""}`;
			(subs_by_signature[key] = subs_by_signature[key] || []).push(sub);
		}

		const fg_label = {};
		for (const fg of this.data.finished_goods) fg_label[fg.row_name] = fg.item_name || fg.item_code;

		this.index = { subs_by_parent, owner_of_row, bom_consumers, subs_by_signature, fg_label };
		for (const material of this.data.materials || []) {
			material.owners = this.material_owners(material);
		}
		this.compute_stats();
	}

	material_owners(material) {
		const key = `${material.main_item_code || ""}::${material.from_bom || ""}`;
		const candidates = this.index.subs_by_signature[key] || [];
		if (candidates.length) return this.owners_of(candidates.map((d) => d.row_name));
		if (material.consumer) return this.owners_of([material.consumer]);
		return this.owners_of(this.index.bom_consumers[material.item_code] || []);
	}

	owners_of(row_names) {
		const owners = new Set();
		for (const row_name of row_names) {
			const owner = this.index.owner_of_row[row_name];
			if (owner) owners.add(owner);
		}
		return [...owners];
	}

	compute_stats() {
		const documents = this.all_documents();
		const materials = this.data.materials || [];
		const rows = [...this.data.finished_goods, ...this.data.sub_assemblies];
		this.stats = {
			work_orders: documents.filter((d) => d.doctype === "Work Order"),
			purchase_orders: documents.filter((d) => d.doctype === "Purchase Order"),
			material_requests: this.data.material_requests || [],
			short_materials: materials.filter((d) => this.open_qty(d) > 0),
			unstarted: rows.filter((d) => !(d.documents || []).length),
			coverage: this.material_coverage(materials),
			schedule: this.data.schedule || [],
		};
	}

	open_qty(material) {
		return flt(flt(material.to_procure_qty) - flt(material.requested_qty), 6);
	}

	material_coverage(materials) {
		const to_procure = materials.reduce((sum, d) => sum + flt(d.to_procure_qty), 0);
		if (!to_procure) return 100;
		const open = materials.reduce((sum, d) => sum + Math.max(this.open_qty(d), 0), 0);
		return ((to_procure - open) / to_procure) * 100;
	}

	all_documents() {
		const rows = [...this.data.finished_goods, ...this.data.sub_assemblies];
		return rows.flatMap((row) => row.documents || []);
	}

	group_rows(rows, key_fn) {
		return (rows || []).reduce((groups, row) => {
			const key = key_fn(row);
			(groups[key] = groups[key] || []).push(row);
			return groups;
		}, {});
	}

	render_kpis() {
		const stats = this.stats;
		const rail = $('<div class="ppv-kpis"></div>').appendTo(this.container);
		rail.append(this.hero_tile());
		rail.append(
			this.kpi_tile({
				label: __("Material Readiness"),
				value: `${Math.round(stats.coverage)}%`,
				tone: stats.short_materials.length ? "red" : "green",
				hint: stats.short_materials.length
					? __("{0} materials still to request", [stats.short_materials.length])
					: __("Everything requested or in stock"),
				tab: "materials",
			})
		);
		rail.append(
			this.kpi_tile({
				label: __("Work Orders"),
				value: stats.work_orders.length,
				tone: stats.unstarted.length ? "amber" : null,
				hint: stats.unstarted.length
					? __("{0} rows not started", [stats.unstarted.length])
					: __("Every row has a document"),
				dots: stats.work_orders,
				tab: "manufacture",
			})
		);
		rail.append(this.procurement_tile());
		rail.append(this.schedule_tile());
	}

	hero_tile() {
		const plan = this.data.plan;
		const tile = $(`
			<div class="ppv-kpi ppv-hero">
				<div class="ppv-ring-wrap">${this.completion_ring(plan.completion)}</div>
				<div class="ppv-hero-body">
					<div class="ppv-hero-top">
						<a class="ppv-hero-name" href="/app/production-plan/${encodeURIComponent(plan.name)}"
							title="${this.esc(plan.name)}">${this.esc(plan.name)}</a>
						<span class="ppv-hero-status"></span>
					</div>
					<div class="ppv-hero-qty">
						<b>${this.format_float(plan.total_produced_qty)}</b>
						<span class="ppv-muted">&nbsp;/&nbsp;${this.format_float(plan.total_planned_qty)}&nbsp;${__(
			"produced"
		)}</span>
					</div>
					<div class="ppv-hero-meta">${this.esc(plan.company)} &middot; ${frappe.datetime.str_to_user(
			plan.posting_date
		)}</div>
				</div>
			</div>
		`);
		tile.find(".ppv-hero-status").append(this.status_badge(plan.status, "sm"));
		return tile;
	}

	kpi_tile({ label, value, hint, tone, dots, tab }) {
		const tile = $(`
			<div class="ppv-kpi" data-tone="${tone || ""}" data-clickable="${tab ? 1 : 0}">
				<div class="ppv-kpi-label">${this.esc(label)}</div>
				<div class="ppv-kpi-value">${this.esc(value)}</div>
				<div class="ppv-kpi-hint">${this.esc(hint)}</div>
			</div>
		`);
		if (dots && dots.length) tile.find(".ppv-kpi-hint").prepend(this.status_dots(dots));
		if (tab) tile.on("click", () => this.set_tab(tab));
		return tile;
	}

	status_dots(rows) {
		return Object.entries(this.group_rows(rows, (d) => d.status || __("Draft")))
			.map(
				([status, group]) =>
					`<span class="ppv-dot-item" title="${this.esc(status)}">
						<span class="ppv-dot" data-theme="${this.status_theme(status)}"></span>${group.length}
					</span>`
			)
			.join("");
	}

	procurement_tile() {
		const orders = this.stats.purchase_orders;
		const requests = this.stats.material_requests;
		return this.kpi_tile({
			label: __("Procurement"),
			value: orders.length + requests.length,
			hint: __("{0} requests · {1} orders", [requests.length, orders.length]),
			dots: [...orders, ...requests],
			tab: "materials",
		});
	}

	schedule_tile() {
		const blocks = this.stats.schedule;
		if (!blocks.length) {
			return this.kpi_tile({
				label: __("Schedule"),
				value: "—",
				hint: __("Not scheduled yet"),
			});
		}
		const workstations = new Set(blocks.map((d) => d.workstation).filter(Boolean));
		const start = frappe.datetime.str_to_user(blocks[0].from_time.split(" ")[0]);
		const end = frappe.datetime.str_to_user(
			blocks.reduce((max, d) => (d.to_time > max ? d.to_time : max), blocks[0].to_time).split(" ")[0]
		);
		return this.kpi_tile({
			label: __("Schedule"),
			value: blocks.length,
			hint: `${start} → ${end} · ${__("{0} workstations", [workstations.size])}`,
			tab: "schedule",
		});
	}

	completion_ring(completion) {
		const radius = 26;
		const circumference = 2 * Math.PI * radius;
		const offset = circumference * (1 - Math.min(completion, 100) / 100);
		return `
			<svg viewBox="0 0 64 64" class="ppv-ring">
				<circle class="ppv-ring-track" cx="32" cy="32" r="${radius}"></circle>
				<circle class="ppv-ring-fill" cx="32" cy="32" r="${radius}"
					stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"></circle>
				<text x="32" y="36" class="ppv-ring-value">${Math.round(completion)}%</text>
			</svg>
		`;
	}

	render_workspace() {
		const workspace = $('<div class="ppv-workspace"></div>').appendTo(this.container);
		this.rail = $('<div class="ppv-pane ppv-rail"></div>').appendTo(workspace);
		this.detail = $('<div class="ppv-pane ppv-detail"></div>').appendTo(workspace);
		this.render_rail();
		this.render_detail();
	}

	render_rail() {
		this.rail.empty().append(`
			<div class="ppv-pane-head">
				<span class="ppv-pane-title">${__("Finished Goods")}</span>
				<span class="ppv-count">${this.data.finished_goods.length}</span>
			</div>
		`);
		this.rail.append(this.rail_search());
		this.rail_body = $('<div class="ppv-pane-body"></div>').appendTo(this.rail);
		this.rail_body.append(this.rail_row_all());
		for (const fg of this.data.finished_goods) this.rail_body.append(this.rail_row(fg));
		this.apply_rail_filter();
	}

	rail_search() {
		const bar = $(`
			<div class="ppv-search">
				<span class="ppv-search-icon">${frappe.utils.icon("search", "sm", "", "", "", true)}</span>
				<input type="search" class="ppv-search-input" placeholder="${__("Filter items...")}" />
			</div>
		`);
		this.rail_query = "";
		bar.find("input").on("input", (e) => {
			this.rail_query = (e.target.value || "").trim().toLowerCase();
			this.apply_rail_filter();
		});
		return bar;
	}

	apply_rail_filter() {
		let visible = 0;
		this.rail_body.find(".ppv-rail-row[data-search]").each((_, el) => {
			const show = !this.rail_query || ($(el).attr("data-search") || "").includes(this.rail_query);
			$(el).toggle(show);
			if (show) visible += 1;
		});
		this.rail_body.find(".ppv-rail-none").toggle(!visible);
		this.highlight_focus();
	}

	rail_row_all() {
		const plan = this.data.plan;
		const row = $(`
			<div class="ppv-rail-row ppv-rail-all" data-focus="all" data-risk="all">
				<div class="ppv-rail-top">
					<span class="ppv-rail-name">${__("All Items")}</span>
					<span class="ppv-rail-pct">${Math.round(plan.completion)}%</span>
				</div>
				<div class="ppv-rail-sub">${__("{0} finished goods · {1} sub assemblies", [
					this.data.finished_goods.length,
					this.data.sub_assemblies.length,
				])}</div>
			</div>
		`);
		row.on("click", () => this.set_focus("all"));
		return row;
	}

	rail_row(fg) {
		const completion = fg.qty ? (fg.produced_qty / fg.qty) * 100 : 0;
		const risk = this.risk_of(fg);
		const row = $(`
			<div class="ppv-rail-row" data-focus="${this.esc(fg.row_name)}" data-risk="${risk.level}"
				data-search="${this.esc(`${fg.item_name || ""} ${fg.item_code}`.toLowerCase())}">
				<div class="ppv-rail-top">
					<span class="ppv-rail-name" title="${this.esc(fg.item_name || fg.item_code)}">${this.esc(
			fg.item_name || fg.item_code
		)}</span>
					<span class="ppv-rail-pct">${Math.round(completion)}%</span>
				</div>
				<div class="ppv-rail-sub">${this.esc(fg.item_code)} &middot; ${this.format_float(fg.qty)} ${this.esc(
			fg.stock_uom || ""
		)}</div>
				<div class="ppv-rail-bar"><span style="width: ${Math.min(completion, 100)}%"></span></div>
				<div class="ppv-rail-flag">${this.esc(risk.label)}</div>
			</div>
		`);
		row.on("click", () => this.set_focus(fg.row_name));
		return row;
	}

	risk_of(fg) {
		const short = (this.data.materials || []).filter(
			(d) => this.open_qty(d) > 0 && d.owners.includes(fg.row_name)
		);
		if (short.length) {
			return { level: "short", label: __("{0} materials short", [short.length]) };
		}
		if (fg.qty && fg.produced_qty >= fg.qty) return { level: "done", label: __("Completed") };
		const rows = [fg, ...(this.index.subs_by_parent[fg.row_name] || [])];
		if (rows.every((d) => !(d.documents || []).length)) {
			return { level: "idle", label: __("Not started") };
		}
		return { level: "running", label: __("In progress") };
	}

	set_focus(row_name) {
		this.focus = row_name;
		this.highlight_focus();
		this.render_detail_body();
	}

	highlight_focus() {
		this.rail_body.find(".ppv-rail-row").each((_, el) => {
			$(el).toggleClass("is-active", $(el).attr("data-focus") === this.focus);
		});
	}

	set_tab(tab) {
		if (this.active_tab === tab) return;
		this.active_tab = tab;
		this.render_detail();
	}

	focused_goods() {
		if (this.focus === "all") return this.data.finished_goods;
		return this.data.finished_goods.filter((d) => d.row_name === this.focus);
	}

	render_detail() {
		this.detail.empty();
		const head = $('<div class="ppv-pane-head"></div>').appendTo(this.detail);
		head.append(
			frappe.ui.tab_buttons({
				type: "subtle",
				size: "sm",
				value: this.active_tab,
				options: [
					{ label: __("Items to Manufacture"), value: "manufacture" },
					{ label: __("Raw Materials"), value: "materials" },
					{ label: __("Schedule"), value: "schedule" },
				],
				on_change: (value) => {
					this.active_tab = value;
					this.render_detail_body();
				},
			})
		);
		head.append(this.detail_search());
		this.detail_body = $('<div class="ppv-pane-body"></div>').appendTo(this.detail);
		this.render_detail_body();
	}

	detail_search() {
		const bar = $(`
			<div class="ppv-search ppv-search-inline">
				<span class="ppv-search-icon">${frappe.utils.icon("search", "sm", "", "", "", true)}</span>
				<input type="search" class="ppv-search-input" placeholder="${__("Search item or document...")}" />
			</div>
		`);
		bar.find("input").on("input", (e) => {
			this.detail_query = (e.target.value || "").trim().toLowerCase();
			this.apply_detail_filter();
		});
		this.detail_query = "";
		return bar;
	}

	apply_detail_filter() {
		const query = this.detail_query;
		this.detail_body.find("tr[data-search]").each((_, el) => {
			$(el).toggle(!query || ($(el).attr("data-search") || "").includes(query));
		});
	}

	render_detail_body() {
		this.detail_body.empty();
		if (this.active_tab === "manufacture") this.render_manufacture_items();
		else if (this.active_tab === "materials") this.render_materials();
		else this.render_schedule();
		this.apply_detail_filter();
	}

	make_table(columns) {
		const head = columns
			.map(
				(col) =>
					`<th class="${col.class || ""}" style="${col.style || ""}">${this.esc(col.label)}</th>`
			)
			.join("");
		const table = $(`<table class="ppv-table"><thead><tr>${head}</tr></thead><tbody></tbody></table>`);
		return { table, body: table.find("tbody") };
	}

	render_manufacture_items() {
		const goods = this.focused_goods();
		if (!goods.length) {
			this.render_empty(__("No items to manufacture in this plan"));
			return;
		}
		const { table, body } = this.make_table([
			{ label: __("Item") },
			{ label: __("Planned"), class: "ppv-num" },
			{ label: __("In Stock"), class: "ppv-num" },
			{ label: __("Done"), class: "ppv-num" },
			{ label: __("Pending"), class: "ppv-num" },
			{ label: __("Progress"), class: "ppv-col-progress" },
			{ label: __("Documents"), class: "ppv-col-docs" },
		]);

		for (const fg of goods) {
			body.append(this.manufacture_row(fg, { kind: "fg", indent: 0 }));
			for (const sub of this.index.subs_by_parent[fg.row_name] || []) {
				body.append(this.manufacture_row(sub, { kind: "sub", indent: 1 + (sub.indent || 0) }));
			}
		}
		this.detail_body.append(table);
		this.append_orphan_subs(body);
	}

	append_orphan_subs(body) {
		if (this.focus !== "all") return;
		const orphans = this.data.sub_assemblies.filter((d) => !this.index.owner_of_row[d.row_name]);
		if (!orphans.length) return;
		body.append(this.group_row(__("Unlinked Sub Assemblies"), 7));
		for (const sub of orphans) body.append(this.manufacture_row(sub, { kind: "sub", indent: 1 }));
	}

	group_row(label, span) {
		return $(`<tr class="ppv-row-group"><td colspan="${span}">${this.esc(label)}</td></tr>`);
	}

	manufacture_row(row, { kind, indent }) {
		const completion = row.qty ? (row.produced_qty / row.qty) * 100 : 0;
		const uom = row.stock_uom || row.uom || "";
		const tr = $(`
			<tr data-kind="${kind}" data-search="${this.esc(
			`${row.item_name || ""} ${row.item_code} ${(row.documents || [])
				.map((d) => d.name)
				.join(" ")}`.toLowerCase()
		)}">
				<td class="ppv-cell-item" style="--ppv-indent: ${indent}">
					<div class="ppv-item-line">
						<a href="/app/item/${encodeURIComponent(row.item_code)}">${this.esc(row.item_name || row.item_code)}</a>
						<span class="ppv-item-tag"></span>
					</div>
					<div class="ppv-item-sub">${this.esc(row.item_code)}</div>
				</td>
				<td class="ppv-num">${this.format_float(row.qty)} <span class="ppv-uom">${this.esc(uom)}</span></td>
				<td class="ppv-num">${kind === "sub" ? this.format_float(row.available_qty) : "—"}</td>
				<td class="ppv-num">${this.format_float(row.produced_qty)}</td>
				<td class="ppv-num ${row.pending_qty > 0 ? "ppv-pending" : ""}">${this.format_float(row.pending_qty)}</td>
				<td class="ppv-col-progress"></td>
				<td class="ppv-col-docs"></td>
			</tr>
		`);
		tr.find(".ppv-item-tag").append(this.manufacture_tag(row, kind));
		tr.find(".ppv-col-progress").append(frappe.ui.progress({ value: completion, hint: true }));
		this.append_document_chips(tr.find(".ppv-col-docs"), row.documents);
		return tr;
	}

	manufacture_tag(row, kind) {
		if (kind === "fg") {
			if (!row.sales_order) return frappe.ui.badge({ label: __("Finished Good"), size: "sm" });
			return frappe.ui.badge({
				label: row.sales_order,
				theme: "violet",
				variant: "outline",
				size: "sm",
			});
		}
		return frappe.ui.badge({
			label: __(row.type_of_manufacturing || "In House"),
			size: "sm",
			theme: row.type_of_manufacturing === "Subcontract" ? "amber" : "blue",
			variant: "outline",
		});
	}

	render_materials() {
		const { owned, unassigned } = this.focused_materials();
		if (!owned.length && !unassigned.length) {
			this.render_empty(__("No raw materials planned for this plan yet"));
			return;
		}
		const { table, body } = this.make_table([
			{ label: __("Material") },
			{ label: __("Required"), class: "ppv-num" },
			{ label: __("In Stock"), class: "ppv-num" },
			{ label: __("To Procure"), class: "ppv-num" },
			{ label: __("Requested"), class: "ppv-num" },
			{ label: __("Ordered"), class: "ppv-num" },
			{ label: __("Received"), class: "ppv-num" },
			{ label: __("Status"), class: "ppv-col-status" },
			{ label: __("Requests"), class: "ppv-col-docs" },
		]);

		for (const material of owned) body.append(this.material_row(material));
		if (unassigned.length) {
			body.append(this.group_row(__("Not linked to a finished good"), 9));
			for (const material of unassigned) body.append(this.material_row(material));
		}
		this.detail_body.append(table);
	}

	focused_materials() {
		const materials = [...(this.data.materials || [])].sort(
			(a, b) => this.open_qty(b) - this.open_qty(a)
		);
		const owned =
			this.focus === "all"
				? materials.filter((d) => d.owners.length)
				: materials.filter((d) => d.owners.includes(this.focus));

		return { owned, unassigned: materials.filter((d) => !d.owners.length) };
	}

	material_row(material) {
		const open = this.open_qty(material);
		const tr = $(`
			<tr data-open="${open > 0 ? 1 : 0}" data-search="${this.esc(
			`${material.item_name || ""} ${material.item_code} ${(material.documents || [])
				.map((d) => d.name)
				.join(" ")}`.toLowerCase()
		)}">
				<td class="ppv-cell-item">
					<div class="ppv-item-line">
						<a href="/app/item/${encodeURIComponent(material.item_code)}">${this.esc(
			material.item_name || material.item_code
		)}</a>
						<span class="ppv-item-tag"></span>
					</div>
					<div class="ppv-item-sub">${this.esc(material.item_code)}${
			material.warehouse ? ` &middot; ${this.esc(material.warehouse)}` : ""
		}</div>
				</td>
				<td class="ppv-num">${this.format_float(material.required_qty)} <span class="ppv-uom">${this.esc(
			material.uom || ""
		)}</span></td>
				<td class="ppv-num">${this.format_float(material.available_qty)}</td>
				<td class="ppv-num">${this.format_float(material.to_procure_qty)}</td>
				<td class="ppv-num">${this.format_float(material.requested_qty)}</td>
				<td class="ppv-num">${this.format_float(material.ordered_qty)}</td>
				<td class="ppv-num">${this.format_float(material.received_qty)}</td>
				<td class="ppv-col-status"></td>
				<td class="ppv-col-docs"></td>
			</tr>
		`);
		const tag = tr.find(".ppv-item-tag");
		tag.append(
			frappe.ui.badge({
				label: __(material.material_request_type || "Material"),
				size: "sm",
				variant: "ghost",
			})
		);
		if (material.owners.length > 1) tag.append(this.shared_badge(material));
		tr.find(".ppv-col-status").append(this.material_status(material, open));
		this.append_document_chips(tr.find(".ppv-col-docs"), material.documents);
		return tr;
	}

	material_status(material, open) {
		const documents = material.documents || [];
		if (open > 0) {
			return this.pill(__("Request {0}", [this.format_float(open)]), "red");
		}
		if (!flt(material.to_procure_qty) && !documents.length) {
			return this.pill(__("In Stock"), "green");
		}

		const statuses = [...new Set(documents.map((d) => d.status).filter(Boolean))];
		if (statuses.length === 1) return this.pill(__(statuses[0]), this.status_theme(statuses[0]));
		if (flt(material.received_qty) >= flt(material.to_procure_qty)) {
			return this.pill(__("Received"), "green");
		}
		if (flt(material.ordered_qty) >= flt(material.to_procure_qty)) {
			return this.pill(__("Ordered"), "blue");
		}
		return this.pill(__("Requested"), "amber");
	}

	shared_badge(material) {
		const names = material.owners.map((row_name) => this.index.fg_label[row_name]).filter(Boolean);
		return frappe.ui.badge({
			label: __("Shared"),
			size: "sm",
			theme: "violet",
			variant: "outline",
			title: __("Quantity covers {0}", [names.join(", ")]),
		});
	}

	pill(label, theme) {
		return frappe.ui.badge({ label, theme, size: "sm" });
	}

	append_document_chips(target, documents) {
		if (!documents || !documents.length) {
			target.append(`<span class="ppv-no-docs">${__("None")}</span>`);
			return;
		}
		const icons = { "Purchase Order": "shopping-cart", "Material Request": "clipboard-list" };
		for (const doc of documents) {
			const route = `/app/${frappe.router.slug(doc.doctype)}/${encodeURIComponent(doc.name)}`;
			$(`<a class="ppv-chip-link" href="${route}"></a>`)
				.append(
					frappe.ui.badge({
						label: doc.name,
						size: "sm",
						theme: this.status_theme(doc.status),
						icon: icons[doc.doctype] || "factory",
						title: __(doc.status || "Draft"),
					})
				)
				.appendTo(target);
		}
	}

	render_empty(title) {
		this.detail_body.append(
			$('<div class="ppv-fill"></div>').append(frappe.ui.empty_state({ icon: "inbox", title }))
		);
	}

	render_schedule() {
		const blocks = this.focused_schedule();
		if (!blocks.length) {
			this.render_empty(__("No schedule yet — use Schedule Items on the Production Plan to build one"));
			return;
		}
		this.detail_body.append(this.schedule_toolbar());
		this.detail_body.append(this.schedule_timeline(blocks));
	}

	focused_schedule() {
		const blocks = this.data.schedule || [];
		if (this.focus === "all") return blocks;
		const rows = new Set([this.focus]);
		for (const sub of this.index.subs_by_parent[this.focus] || []) rows.add(sub.row_name);
		const items = new Set(
			(this.data.materials || []).filter((d) => d.owners.includes(this.focus)).map((d) => d.item_code)
		);
		return blocks.filter((d) =>
			d.row_type === "Raw Material" ? items.has(d.item_code) : rows.has(d.plan_row)
		);
	}

	schedule_toolbar() {
		const toggle = (value, options, on_change) =>
			frappe.ui.tab_buttons({ type: "ghost", size: "sm", value, options, on_change });
		return $('<div class="ppv-schedule-toolbar"></div>')
			.append(
				toggle(
					this.schedule_group,
					[
						{ label: __("By Item"), value: "item" },
						{ label: __("By Workstation"), value: "workstation" },
					],
					(value) => {
						this.schedule_group = value;
						this.render_detail_body();
					}
				)
			)
			.append(
				toggle(
					this.schedule_scale,
					[
						{ label: __("Day"), value: "day" },
						{ label: __("Hour"), value: "hour" },
					],
					(value) => {
						this.schedule_scale = value;
						this.render_detail_body();
					}
				)
			).append(`<span class="ppv-legend">
				<span class="ppv-legend-item"><i data-row-type="Finished Good"></i>${__("Finished Good")}</span>
				<span class="ppv-legend-item"><i data-row-type="Sub Assembly"></i>${__("Sub Assembly")}</span>
				<span class="ppv-legend-item"><i data-row-type="Raw Material"></i>${__("Raw Material")}</span>
			</span>`);
	}

	schedule_timeline(blocks) {
		const raw_start = Math.min(...blocks.map((d) => frappe.datetime.str_to_obj(d.from_time).getTime()));
		const raw_end = Math.max(...blocks.map((d) => frappe.datetime.str_to_obj(d.to_time).getTime()));
		const axis = this.timeline_ticks(raw_start, raw_end);
		const span = Math.max(axis.end - axis.start, 1);
		const now = new Date().getTime();
		this.today_offset = now > axis.start && now < axis.end ? ((now - axis.start) / span) * 100 : null;

		const timeline = $(
			`<div class="ppv-timeline" style="--ppv-ticks: ${axis.ticks.length}; --ppv-tick-w: ${axis.tick_width}"></div>`
		);
		timeline.append(`
			<div class="ppv-timeline-header">
				<div class="ppv-timeline-label">${__("Timeline")}</div>
				<div class="ppv-axis">${axis.ticks
					.map((tick) => `<div class="ppv-axis-tick">${this.esc(tick)}</div>`)
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
		if (this.schedule_scale === "hour") return this.hour_ticks(start, end, hour_ms);

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
			tick_width: "84px",
		};
	}

	hour_ticks(start, end, hour_ms) {
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
			tick_width: "64px",
		};
	}

	schedule_rows(blocks) {
		if (this.schedule_group === "workstation") {
			const groups = this.group_rows(blocks, (d) => d.workstation || d.supplier || __("Unassigned"));
			return Object.entries(groups).map(([label, rows]) => ({ label, indent: 0, blocks: rows }));
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
		for (const fg of this.focused_goods()) {
			used_rows.add(fg.row_name);
			const branch = [];
			for (const sub of this.index.subs_by_parent[fg.row_name] || []) {
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

		return out.concat(this.leftover_rows(blocks, used_rows, used_materials));
	}

	leftover_rows(blocks, used_rows, used_materials) {
		const leftover = blocks.filter((d) =>
			d.row_type === "Raw Material" ? !used_materials.has(d.item_code) : !used_rows.has(d.plan_row)
		);
		const groups = this.group_rows(leftover, (d) => d.item_name || d.item_code || d.subject);
		return Object.entries(groups).map(([label, rows]) => ({ label, indent: 0, blocks: rows }));
	}

	timeline_row(descriptor, start, span) {
		const { label, indent, blocks } = descriptor;
		const row = $(`
			<div class="ppv-timeline-row" data-depth="${indent > 0 ? "child" : "root"}">
				<div class="ppv-timeline-label" style="--ppv-row-indent: ${indent}" title="${this.esc(label)}">
					${this.esc(label)}</div>
				<div class="ppv-track"></div>
			</div>
		`);
		const track = row.find(".ppv-track");
		if (this.today_offset !== null) {
			track.append(`<span class="ppv-today" style="left: ${this.today_offset}%"></span>`);
		}
		for (const block of blocks) track.append(this.timeline_block(block, start, span));
		return row;
	}

	timeline_block(block, start, span) {
		const from = frappe.datetime.str_to_obj(block.from_time).getTime();
		const to = frappe.datetime.str_to_obj(block.to_time).getTime();
		const left = ((from - start) / span) * 100;
		const width = Math.max(((to - from) / span) * 100, 0.6);
		const title = [
			block.subject,
			`${frappe.datetime.str_to_user(block.from_time)} → ${frappe.datetime.str_to_user(block.to_time)}`,
			block.workstation || block.supplier || "",
		]
			.filter(Boolean)
			.join("\n");
		return `<a class="ppv-block" data-row-type="${this.esc(block.row_type || "")}"
			style="left: ${left}%; width: ${width}%"
			href="/app/production-plan-schedule/${encodeURIComponent(block.name)}"
			title="${this.esc(title)}"><span>${this.esc(
			block.operation || block.item_name || block.subject || ""
		)}</span></a>`;
	}

	esc(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
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
			Issued: "blue",
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

	styles() {
		return `<style>
			.ppv-page .page-form {
				background: transparent;
				border: none;
				padding: 0;
				margin: 0 2px var(--padding-sm);
			}

			.ppv {
				display: flex;
				flex-direction: column;
				gap: var(--padding-sm);
				margin: 0 2px;
				overflow: hidden;
			}
			.ppv-fill { flex: 1 1 auto; display: flex; align-items: center; justify-content: center; }
			.ppv-muted { color: var(--text-muted); }
			.ppv-uom { color: var(--text-muted); font-size: var(--text-xs); }

			.ppv-kpis {
				flex: 0 0 auto;
				display: grid;
				grid-template-columns: 1.7fr repeat(4, minmax(0, 1fr));
				gap: var(--padding-sm);
			}
			.ppv-kpi {
				display: flex;
				flex-direction: column;
				justify-content: center;
				gap: 2px;
				min-height: 76px;
				padding: 10px 14px;
				background: var(--card-bg, var(--fg-color));
				border: 1px solid var(--border-color);
				border-radius: var(--radius-md);
			}
			.ppv-kpi[data-clickable="1"] { cursor: pointer; }
			.ppv-kpi[data-clickable="1"]:hover { border-color: var(--gray-400); }
			.ppv-kpi-label {
				font-size: var(--text-xs);
				text-transform: uppercase;
				letter-spacing: 0.05em;
				color: var(--text-muted);
			}
			.ppv-kpi-value {
				font-size: 22px;
				line-height: 1.2;
				font-weight: 700;
				color: var(--heading-color);
				font-variant-numeric: tabular-nums;
			}
			.ppv-kpi[data-tone="red"] .ppv-kpi-value { color: var(--red-600); }
			.ppv-kpi[data-tone="green"] .ppv-kpi-value { color: var(--green-600); }
			.ppv-kpi[data-tone="amber"] .ppv-kpi-value { color: var(--yellow-700); }
			.ppv-kpi-hint {
				display: flex;
				align-items: center;
				gap: 8px;
				flex-wrap: wrap;
				font-size: var(--text-xs);
				color: var(--text-muted);
			}
			.ppv-dot-item { display: inline-flex; align-items: center; gap: 4px; }
			.ppv-dot { width: 7px; height: 7px; border-radius: 999px; background: var(--gray-400); }
			.ppv-dot[data-theme="green"] { background: var(--green-500); }
			.ppv-dot[data-theme="blue"] { background: var(--blue-500); }
			.ppv-dot[data-theme="amber"] { background: var(--yellow-500); }
			.ppv-dot[data-theme="red"] { background: var(--red-500); }

			.ppv-hero { flex-direction: row; align-items: center; gap: 14px; }
			.ppv-ring { width: 62px; height: 62px; }
			.ppv-ring-track { fill: none; stroke: var(--bg-color); stroke-width: 7; }
			.ppv-ring-fill {
				fill: none;
				stroke: var(--primary);
				stroke-width: 7;
				stroke-linecap: round;
				transform: rotate(-90deg);
				transform-origin: 32px 32px;
				transition: stroke-dashoffset 0.6s ease;
			}
			.ppv-ring-value {
				text-anchor: middle;
				font-size: 15px;
				font-weight: 700;
				fill: var(--heading-color);
			}
			.ppv-hero-body { min-width: 0; }
			.ppv-hero-top { display: flex; align-items: center; gap: 8px; }
			.ppv-hero-name {
				font-size: var(--text-lg);
				font-weight: 600;
				color: var(--heading-color);
				text-decoration: none;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.ppv-hero-qty { font-size: var(--text-sm); color: var(--text-color); margin-top: 2px; }
			.ppv-hero-meta { font-size: var(--text-xs); color: var(--text-muted); }

			.ppv-workspace {
				flex: 1 1 auto;
				min-height: 0;
				display: grid;
				grid-template-columns: 284px minmax(0, 1fr);
				gap: var(--padding-sm);
			}
			.ppv-pane {
				display: flex;
				flex-direction: column;
				min-height: 0;
				background: var(--card-bg, var(--fg-color));
				border: 1px solid var(--border-color);
				border-radius: var(--radius-md);
				overflow: hidden;
			}
			.ppv-pane-head {
				flex: 0 0 auto;
				display: flex;
				align-items: center;
				gap: 8px;
				min-height: 44px;
				padding: 6px 12px;
				border-bottom: 1px solid var(--border-color);
			}
			.ppv-pane-title { font-weight: 600; font-size: var(--text-sm); color: var(--heading-color); }
			.ppv-count {
				font-size: var(--text-xs);
				color: var(--text-muted);
				background: var(--bg-color);
				border-radius: 999px;
				padding: 1px 7px;
			}
			.ppv-pane-body { flex: 1 1 auto; min-height: 0; overflow: auto; }

			.ppv-search {
				display: flex;
				align-items: center;
				gap: 6px;
				margin: 8px 12px;
				background: var(--fg-color);
				border: 1px solid var(--border-color);
				border-radius: var(--radius-sm);
				padding: 4px 8px;
			}
			.ppv-search-inline { margin: 0 0 0 auto; min-width: 200px; max-width: 260px; }
			.ppv-search:focus-within { border-color: var(--primary); }
			.ppv-search-icon { display: flex; color: var(--text-muted); }
			.ppv-search-input {
				flex: 1;
				min-width: 0;
				border: none;
				outline: none;
				background: var(--fg-color);
				font-size: var(--text-sm);
				color: var(--text-color);
			}

			.ppv-rail-row {
				position: relative;
				padding: 9px 12px 9px 15px;
				border-bottom: 1px solid var(--border-color);
				cursor: pointer;
			}
			.ppv-rail-row::before {
				content: "";
				position: absolute;
				left: 0; top: 0; bottom: 0;
				width: 3px;
				background: transparent;
			}
			.ppv-rail-row[data-risk="short"]::before { background: var(--red-500); }
			.ppv-rail-row[data-risk="idle"]::before { background: var(--yellow-500); }
			.ppv-rail-row[data-risk="running"]::before { background: var(--blue-500); }
			.ppv-rail-row[data-risk="done"]::before { background: var(--green-500); }
			.ppv-rail-row:hover { background: var(--bg-color); }
			.ppv-rail-row.is-active { background: var(--bg-color); }
			.ppv-rail-row.is-active .ppv-rail-name { color: var(--primary); }
			.ppv-rail-top { display: flex; align-items: baseline; gap: 8px; }
			.ppv-rail-name {
				flex: 1;
				min-width: 0;
				font-weight: 600;
				font-size: var(--text-sm);
				color: var(--heading-color);
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.ppv-rail-pct {
				font-size: var(--text-xs);
				color: var(--text-muted);
				font-variant-numeric: tabular-nums;
			}
			.ppv-rail-sub {
				font-size: var(--text-xs);
				color: var(--text-muted);
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.ppv-rail-bar {
				height: 3px;
				border-radius: 999px;
				background: var(--bg-color);
				margin-top: 6px;
				overflow: hidden;
			}
			.ppv-rail-bar span { display: block; height: 100%; background: var(--primary); }
			.ppv-rail-flag { font-size: var(--text-xs); color: var(--text-muted); margin-top: 4px; }
			.ppv-rail-row[data-risk="short"] .ppv-rail-flag { color: var(--red-600); }

			.ppv-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: var(--text-sm); }
			.ppv-table thead th {
				position: sticky;
				top: 0;
				z-index: 2;
				background: var(--card-bg, var(--fg-color));
				border-bottom: 1px solid var(--border-color);
				padding: 8px 12px;
				font-size: var(--text-xs);
				font-weight: 500;
				text-transform: uppercase;
				letter-spacing: 0.05em;
				color: var(--text-muted);
				white-space: nowrap;
				text-align: left;
			}
			.ppv-table td {
				padding: 7px 12px;
				border-bottom: 1px solid var(--border-color);
				vertical-align: middle;
			}
			.ppv-table th.ppv-num, .ppv-table td.ppv-num {
				text-align: right;
				white-space: nowrap;
				font-variant-numeric: tabular-nums;
			}
			.ppv-table tbody tr:hover { background: var(--bg-color); }
			.ppv-table tbody tr[data-open="1"] td:first-child { box-shadow: inset 3px 0 0 var(--red-500); }
			.ppv-row-group td {
				background: var(--bg-color);
				font-size: var(--text-xs);
				text-transform: uppercase;
				letter-spacing: 0.05em;
				color: var(--text-muted);
			}
			.ppv-cell-item { padding-left: calc(12px + var(--ppv-indent, 0) * 18px) !important; min-width: 220px; }
			.ppv-item-line { display: flex; align-items: center; gap: 6px; }
			.ppv-item-line a { color: var(--heading-color); font-weight: 500; text-decoration: none; }
			.ppv-table tr[data-kind="fg"] .ppv-item-line a { font-weight: 600; }
			.ppv-item-sub { font-size: var(--text-xs); color: var(--text-muted); }
			.ppv-pending { color: var(--yellow-700); }
			.ppv-col-progress { width: 130px; }
			.ppv-col-status { width: 120px; }
			.ppv-col-docs { width: 210px; }
			.ppv-col-docs > * { margin-right: 4px; }
			.ppv-chip-link { text-decoration: none; }
			.ppv-no-docs { color: var(--text-muted); font-size: var(--text-xs); }

			.ppv-schedule-toolbar {
				display: flex;
				align-items: center;
				gap: var(--padding-md);
				flex-wrap: wrap;
				padding: 8px 12px;
				border-bottom: 1px solid var(--border-color);
			}
			.ppv-legend { display: flex; gap: 12px; margin-left: auto; font-size: var(--text-xs); color: var(--text-muted); }
			.ppv-legend-item { display: inline-flex; align-items: center; gap: 5px; }
			.ppv-legend-item i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
			.ppv-legend-item i[data-row-type="Finished Good"] { background: var(--purple-300); }
			.ppv-legend-item i[data-row-type="Sub Assembly"] { background: var(--blue-300); }
			.ppv-legend-item i[data-row-type="Raw Material"] { background: var(--yellow-300); }

			.ppv-timeline-scroll { overflow: auto; }
			.ppv-timeline { min-width: calc(200px + var(--ppv-ticks) * var(--ppv-tick-w, 84px)); }
			.ppv-timeline-header, .ppv-timeline-row {
				display: grid;
				grid-template-columns: 200px 1fr;
				border-bottom: 1px solid var(--border-color);
			}
			.ppv-timeline-header {
				position: sticky;
				top: 0;
				z-index: 3;
				background: var(--card-bg, var(--fg-color));
			}
			.ppv-timeline-row:last-child { border-bottom: none; }
			.ppv-timeline-label {
				position: sticky;
				left: 0;
				z-index: 2;
				background: var(--card-bg, var(--fg-color));
				padding: 8px 10px;
				padding-left: calc(10px + var(--ppv-row-indent, 0) * 16px);
				font-size: var(--text-sm);
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
			.ppv-axis { display: grid; grid-template-columns: repeat(var(--ppv-ticks), 1fr); }
			.ppv-axis-tick {
				padding: 8px 6px;
				font-size: var(--text-xs);
				color: var(--text-muted);
				border-right: 1px dashed var(--border-color);
				white-space: nowrap;
			}
			.ppv-track {
				position: relative;
				min-height: 38px;
				background-image: repeating-linear-gradient(
					to right,
					transparent,
					transparent calc(100% / var(--ppv-ticks) - 1px),
					var(--border-color) calc(100% / var(--ppv-ticks) - 1px),
					var(--border-color) calc(100% / var(--ppv-ticks))
				);
			}
			.ppv-today {
				position: absolute;
				top: 0;
				bottom: 0;
				width: 2px;
				background: var(--red-400);
				z-index: 1;
			}
			.ppv-block {
				position: absolute;
				top: 6px;
				height: 26px;
				border-radius: var(--radius-sm);
				background: var(--blue-100);
				border: 1px solid var(--blue-300);
				color: var(--blue-700);
				font-size: var(--text-xs);
				line-height: 24px;
				padding: 0 8px;
				overflow: hidden;
				white-space: nowrap;
				text-overflow: ellipsis;
				text-decoration: none;
				z-index: 2;
			}
			.ppv-block:hover { filter: brightness(0.97); text-decoration: none; }
			.ppv-block[data-row-type="Finished Good"] {
				background: var(--purple-100); border-color: var(--purple-300); color: var(--purple-700);
			}
			.ppv-block[data-row-type="Raw Material"] {
				background: var(--yellow-100); border-color: var(--yellow-300); color: var(--yellow-700);
			}

			@media (max-width: 1200px) {
				.ppv-kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); }
				.ppv-hero { grid-column: span 3; }
			}
			@media (max-width: 900px) {
				.ppv { height: auto !important; overflow: visible; }
				.ppv-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
				.ppv-hero { grid-column: span 2; }
				.ppv-workspace { grid-template-columns: 1fr; }
				.ppv-pane-body { max-height: 60vh; }
			}
		</style>`;
	}
};
