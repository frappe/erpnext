// Shop Floor — an immersive, keyboard-first operator/manager interface.
//
// Two experiences share one app shell (see get_shop_floor_context on the server):
//   • manager  — a paginated board of work orders bucketed Pending / In Progress and Completed.
//                Drilling into a work order opens its job cards in the operator pane.
//   • operator — a focused workstation/work-order view to start, pause, complete and submit jobs.
//
// The whole surface is driveable from the keyboard (press ? for the cheat sheet) so an operator
// at a terminal never needs the mouse.

// Job Card status → indicator colour, mirrored from workstation.get_status_color so the manager
// board can paint per-operation chips without a round-trip.
const JC_STATUS_COLORS = {
	Completed: "green",
	Submitted: "blue",
	"Work In Progress": "orange",
	"Material Transferred": "yellow",
	"On Hold": "red",
	Open: "gray",
	"Not Started": "gray",
};

const MANAGER_BUCKETS = [
	{ key: "open", label: __("Pending / In Progress"), dot: "orange" },
	{ key: "completed", label: __("Completed"), dot: "green" },
];

const PAGE_LENGTH = 20;

class ShopFloor {
	constructor({ wrapper }, page) {
		this.wrapper = $(wrapper);
		this.page = page;
		this.timer_intervals = {};
		this.capacity = 1;
		this.mode = null;
		// Remembers each Materials panel's open/closed state (keyed by job card) so it
		// survives re-renders — otherwise a reload right after a click resets the panel.
		this.materials_open = {};
		// Same idea for the per-operation Work Instructions panel.
		this.instructions_open = {};

		// View state.
		this.view = "operator"; // overwritten once context loads
		this.active_bucket = "open";
		this.with_job_cards_only = true; // board default: hide WOs that have no job cards
		this.buckets = {}; // key -> { rows, total, start, loaded }
		this.selected_wo = null;
		this.focus_index = -1;
		this.op_state = { workstation: null, work_order: null };

		this.make();
		this.bind_realtime();
		this.bind_lifecycle();
		this.init();
	}

	init() {
		frappe.call("erpnext.manufacturing.page.shop_floor.shop_floor.get_shop_floor_context").then((r) => {
			const ctx = r.message || {};
			this.view = ctx.role_view === "manager" ? "manager" : "operator";
			this.can_manage = !!ctx.can_manage;
			this.user_employee = ctx.user_employee || null;
			this.render_shell_controls();
			this.render_view();
			this.bind_keys();
			this.initialized = true;
			this.apply_route_options();
		});
	}

	// ── App shell ────────────────────────────────────────────────────────────
	make() {
		this.wrapper.append(`
			${this.styles()}
			<div class="sf-app">
				<div class="sf-topbar">
					<div class="sf-topbar-left"></div>
					<div class="sf-topbar-center"></div>
					<div class="sf-topbar-right">
						<button class="btn btn-default btn-sm sf-btn-theme"></button>
						<button class="btn btn-default btn-sm sf-btn-home" title="${__("Home")}">
							${frappe.utils.icon("house", "sm")}
						</button>
						<button class="btn btn-default btn-sm sf-btn-refresh" title="${__("Refresh")} (r)">
							${frappe.utils.icon("refresh-cw", "sm")}
						</button>
						<button class="btn btn-default btn-sm sf-btn-scan" title="${__("Scan Job Card")} (b)">
							${frappe.utils.icon("scan", "sm")}
						</button>
						<button class="btn btn-default btn-sm sf-btn-help" title="${__("Keyboard Shortcuts")} (?)">?</button>
					</div>
				</div>
				<div class="sf-body">
					<div class="sf-board"></div>
					<div class="sf-detail"></div>
					<div class="sf-operator"></div>
				</div>
			</div>
		`);

		this.app = this.wrapper.find(".sf-app");
		this.brand_icon = `<img class="sf-brand-icon" src="/assets/erpnext/images/erpnext-logo.svg" alt="${__(
			"ERPNext"
		)}">`;
		this.topbar_left = this.wrapper.find(".sf-topbar-left");
		this.topbar_center = this.wrapper.find(".sf-topbar-center");
		this.body = this.wrapper.find(".sf-body");
		this.board_container = this.wrapper.find(".sf-board");
		this.detail_container = this.wrapper.find(".sf-detail");
		this.op_container = this.wrapper.find(".sf-operator");

		this.wrapper.find(".sf-btn-home").on("click", () => (window.location.href = "/app"));
		this.wrapper.find(".sf-btn-refresh").on("click", () => this.refresh());
		this.wrapper.find(".sf-btn-scan").on("click", () => this.open_scanner());
		this.wrapper.find(".sf-btn-help").on("click", () => this.show_help());
		this.wrapper.find(".sf-btn-theme").on("click", () => this.toggle_theme());
		this.update_theme_button();
	}

	// Kiosk-friendly light/dark switch: flips the standard desk theme and persists it on the
	// User (same as the Ctrl+Shift+G switcher), so the choice survives reloads and follows the
	// operator's login on any device.
	toggle_theme() {
		const next = frappe.ui.get_current_theme() === "dark" ? "light" : "dark";
		document.documentElement.setAttribute("data-theme-mode", next);
		frappe.ui.set_theme(next);
		frappe.xcall("frappe.core.doctype.user.user.switch_theme", {
			theme: next.charAt(0).toUpperCase() + next.slice(1),
		});
		this.update_theme_button();
	}

	update_theme_button() {
		const dark = frappe.ui.get_current_theme() === "dark";
		this.wrapper
			.find(".sf-btn-theme")
			.html(dark ? "☀" : "☾")
			.attr("title", dark ? __("Switch to Light Theme") : __("Switch to Dark Theme"));
	}

	render_shell_controls() {
		this.topbar_left.empty();
		this.topbar_center.empty();

		// View toggle — only managers can flip between the board and a bare operator view.
		const toggle = this.can_manage
			? `<div class="sf-view-toggle">
					<button class="sf-view-btn ${this.view === "manager" ? "active" : ""}" data-view="manager">${__(
					"Board"
			  )}</button>
					<button class="sf-view-btn ${this.view === "operator" ? "active" : ""}" data-view="operator">${__(
					"Operator"
			  )}</button>
				</div>`
			: "";

		if (this.view === "manager") {
			this.topbar_left.html(`
				<span class="sf-title">${this.brand_icon}${__("Shop Floor")}</span>
				${toggle}
				<div class="sf-tabs">
					${MANAGER_BUCKETS.map(
						(b) => `<button class="sf-tab ${
							b.key === this.active_bucket ? "active" : ""
						}" data-bucket="${b.key}">
							<span class="sf-dot ${b.dot}"></span>${b.label}
							<span class="sf-tab-count" data-bucket-count="${b.key}"></span>
						</button>`
					).join("")}
				</div>
			`);
			this.topbar_center.html(`
				<div class="sf-search">
					${frappe.utils.icon("search", "sm")}
					<input type="text" class="sf-search-input" placeholder="${__("Search work orders…")} (/)">
				</div>
				<label class="sf-toggle" title="${__("Only show work orders that have job cards")}">
					<input type="checkbox" class="sf-jc-toggle" ${this.with_job_cards_only ? "checked" : ""}>
					<span>${__("With job cards only")}</span>
				</label>
			`);

			this.topbar_left.find(".sf-tab").on("click", (e) => {
				this.switch_bucket($(e.currentTarget).attr("data-bucket"));
			});
			let timer = null;
			this.topbar_center.find(".sf-search-input").on("input", (e) => {
				const val = e.target.value;
				clearTimeout(timer);
				timer = setTimeout(() => this.search_work_orders(val), 300);
			});
			this.topbar_center.find(".sf-jc-toggle").on("change", (e) => {
				this.toggle_job_cards_only(e.target.checked);
			});
		} else {
			this.topbar_left.html(
				`<span class="sf-title">${this.brand_icon}${__("Shop Floor")}</span>${toggle}`
			);
			this.build_operator_filters();
		}

		this.topbar_left.find(".sf-view-btn").on("click", (e) => {
			this.set_view($(e.currentTarget).attr("data-view"));
		});
	}

	build_operator_filters() {
		this.topbar_center.html('<div class="sf-filters"></div>');
		const $filters = this.topbar_center.find(".sf-filters");

		this.workstation_filter = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Workstation",
				fieldname: "workstation",
				placeholder: __("Machine"),
				onchange: () => this.load_operator(),
			},
			parent: $filters,
			render_input: true,
		});
		this.workstation_filter.$wrapper.addClass("sf-filter-control");

		this.work_order_filter = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Work Order",
				fieldname: "work_order",
				placeholder: __("Work Order"),
				onchange: () => this.load_operator(),
			},
			parent: $filters,
			render_input: true,
		});
		this.work_order_filter.$wrapper.addClass("sf-filter-control");
	}

	set_view(view) {
		if (!view || view === this.view) return;
		this.view = view;
		this.selected_wo = null;
		this.focus_index = -1;
		this.render_shell_controls();
		this.render_view();
	}

	render_view() {
		const manager = this.view === "manager";
		this.board_container.toggle(manager);
		this.detail_container.toggle(manager && !!this.selected_wo);
		this.op_container.toggle(!manager);
		this.body.toggleClass("detail-open", manager && !!this.selected_wo);

		if (manager) {
			this.load_bucket(this.active_bucket);
		} else {
			this.load_operator();
		}
	}

	// ── Manager board ────────────────────────────────────────────────────────
	switch_bucket(bucket) {
		if (!bucket || bucket === this.active_bucket) return;
		this.active_bucket = bucket;
		this.selected_wo = null;
		this.focus_index = -1;
		this.topbar_left.find(".sf-tab").removeClass("active");
		this.topbar_left.find(`.sf-tab[data-bucket="${bucket}"]`).addClass("active");
		this.detail_container.hide();
		this.body.removeClass("detail-open");
		this.load_bucket(bucket);
	}

	search_work_orders(term) {
		this.search_term = term;
		// Re-query every bucket from scratch on the next visit; reload the active one now.
		this.buckets = {};
		this.load_bucket(this.active_bucket);
	}

	toggle_job_cards_only(checked) {
		this.with_job_cards_only = !!checked;
		// Filter changes every bucket's contents + counts; drop caches and clear stale counts.
		this.buckets = {};
		this.topbar_left.find(".sf-tab-count").text("");
		this.load_bucket(this.active_bucket);
	}

	load_bucket(bucket, append = false) {
		const state = this.buckets[bucket] || { rows: [], total: 0, start: 0, loaded: false };
		const start = append ? state.start : 0;

		frappe.call({
			method: "erpnext.manufacturing.page.shop_floor.shop_floor.get_work_orders",
			args: {
				status_group: bucket,
				start: start,
				page_length: PAGE_LENGTH,
				search: this.search_term || null,
				with_job_cards_only: this.with_job_cards_only ? 1 : 0,
			},
			callback: (r) => {
				const data = r.message || {};
				const rows = data.work_orders || [];
				this.buckets[bucket] = {
					rows: append ? state.rows.concat(rows) : rows,
					total: cint(data.total),
					start: start + rows.length,
					loaded: true,
				};
				this.update_tab_count(bucket);
				if (bucket === this.active_bucket) this.render_board();
			},
		});
	}

	update_tab_count(bucket) {
		const state = this.buckets[bucket];
		if (!state) return;
		this.topbar_left.find(`[data-bucket-count="${bucket}"]`).text(state.total ? state.total : "");
	}

	render_board() {
		const state = this.buckets[this.active_bucket] || { rows: [], total: 0 };
		this.focus_index = -1;

		if (!state.rows.length) {
			this.board_container.html(`<div class="sf-empty">${__("No work orders here.")}</div>`);
			return;
		}

		const cards = state.rows.map((wo) => this.work_order_card(wo)).join("");
		const more =
			state.rows.length < state.total
				? `<button class="btn btn-default sf-load-more">${__("Load more")} (${state.rows.length}/${
						state.total
				  })</button>`
				: `<div class="sf-board-foot text-muted">${__("Showing all {0}", [state.total])}</div>`;

		this.board_container.html(
			`<div class="sf-wo-grid">${cards}</div><div class="sf-board-more">${more}</div>`
		);

		this.board_container.find(".sf-wo-card").on("click", (e) => {
			this.open_wo($(e.currentTarget).attr("data-name"));
		});
		this.board_container
			.find(".sf-load-more")
			.on("click", () => this.load_bucket(this.active_bucket, true));
	}

	work_order_card(wo) {
		const item = wo.item_name || wo.production_item;

		// Hero image = the current operation's workstation. No item-image fallback — when the
		// workstation has no image uploaded we show its initials, never the product image.
		const image = wo.workstation_image
			? `<img src="${wo.workstation_image}" alt="">`
			: `<span class="sf-wo-image-fallback">${frappe.get_abbr(wo.workstation_name || item, 2)}</span>`;

		const workstation_line = wo.workstation_name
			? `<div class="sf-wo-ws"><span class="sf-wo-ws-icon">🏭</span> ${frappe.utils.escape_html(
					wo.workstation_name
			  )}${wo.current_operation ? ` · ${frappe.utils.escape_html(wo.current_operation)}` : ""}</div>`
			: "";

		// Operations bar: green segment (done) + orange segment (in progress); grey track = pending.
		const done_pct = Math.min(cint(wo.per_operations), 100);
		const wip_pct = Math.min(cint(wo.per_in_progress), 100 - done_pct);

		return `
			<div class="sf-wo-card" data-sf-focusable data-kind="wo" data-name="${wo.name}" tabindex="0">
				<div class="sf-wo-top">
					<div class="sf-wo-image">${image}</div>
					<div class="sf-wo-head">
						<div class="sf-wo-title">${frappe.utils.escape_html(item)}</div>
						${workstation_line}
						<div class="sf-wo-id">
							<span class="sf-wo-status-dot ${wo.status_colour}" title="${frappe.utils.escape_html(__(wo.status))}"></span>
							<a href="/app/work-order/${wo.name}" onclick="event.stopPropagation()">${wo.name}</a>
						</div>
					</div>
				</div>
				<div class="sf-wo-progress-block">
					<div class="sf-wo-progress-label">
						<span>${__("Operations")}</span>
						<span class="sf-wo-progress-count">${cint(wo.completed_operations)} / ${cint(wo.total_operations)}</span>
					</div>
					<div class="sf-progress">
						<div class="sf-progress-seg sf-seg-done" style="width: ${done_pct}%"></div>
						<div class="sf-progress-seg sf-seg-wip" style="width: ${wip_pct}%"></div>
					</div>
				</div>
			</div>
		`;
	}

	open_wo(name) {
		if (!name) return;
		this.selected_wo = name;
		this.op_state = { workstation: null, work_order: name };
		this.detail_container.show();
		this.body.addClass("detail-open");
		this.board_container
			.find(".sf-wo-card")
			.removeClass("sf-selected")
			.filter(`[data-name="${name}"]`)
			.addClass("sf-selected");
		// The detail pane reuses the operator rendering for a single work order.
		this.detail_container.html(`
			<div class="sf-detail-head">
				<button class="btn btn-default btn-sm sf-detail-back">${frappe.utils.icon("left", "sm")} ${__(
			"Back"
		)} (Esc)</button>
				<span class="sf-detail-title">${frappe.utils.escape_html(name)}</span>
				<a class="btn btn-default btn-sm" href="/app/work-order/${name}" target="_blank">${__("Open")}</a>
			</div>
			<div class="sf-detail-body"></div>
		`);
		this.detail_container.find(".sf-detail-back").on("click", () => this.close_wo());
		this.op_container_target = this.detail_container.find(".sf-detail-body");
		this.load_operator_data(this.op_container_target, { work_order: name });
	}

	close_wo() {
		this.selected_wo = null;
		this.op_container_target = null;
		this.detail_container.hide().empty();
		this.body.removeClass("detail-open");
		this.board_container.find(".sf-wo-card").removeClass("sf-selected");
	}

	// ── Operator pane ──────────────────────────────────────────────────────────
	// Resolves the container the operator content renders into: the standalone operator
	// view, or the manager's drill-down detail pane.
	current_op_container() {
		return this.view === "manager" ? this.op_container_target : this.op_container;
	}

	load_operator() {
		const workstation = this.workstation_filter ? this.workstation_filter.get_value() : null;
		const work_order = this.work_order_filter ? this.work_order_filter.get_value() : null;
		this.op_state = { workstation, work_order };

		if (!workstation && !work_order) {
			this.clear_timers();
			this.op_container.html(
				`<div class="sf-empty">${__("Select a machine or work order to begin")}</div>`
			);
			return;
		}
		this.load_operator_data(this.op_container, { workstation, work_order });
	}

	load_operator_data($container, { workstation, work_order }) {
		frappe.call({
			method: "erpnext.manufacturing.page.shop_floor.shop_floor.get_data",
			args: {
				workstation: work_order ? null : workstation,
				work_order: work_order || null,
			},
			callback: (r) => {
				const data = r.message || {};
				this.job_cards = data.job_cards || [];
				this.capacity = cint(data.capacity) || 1;
				this.mode = data.mode || (work_order ? "work_order" : "workstation");
				this.oee = data.oee || null;
				if (data.user_employee) this.user_employee = data.user_employee;
				this.today_sessions = data.today_sessions || [];
				this.workstation = workstation;
				this.work_order = work_order;
				this.compute_state();
				this.dedupe_today_sessions();
				this.render_operator($container);
			},
		});
	}

	// A job card already shown under Completed Operations shouldn't repeat in
	// Today's Sessions — keep it in Completed Operations only.
	dedupe_today_sessions() {
		const shown = new Set((this.completed || []).map((jc) => jc.name));
		this.today_sessions = (this.today_sessions || []).filter((s) => !shown.has(s.name));
	}

	// Re-fetch whichever operator content is currently on screen (used after every action).
	reload() {
		if (this.view === "manager" && this.selected_wo) {
			this.load_operator_data(this.op_container_target, { work_order: this.selected_wo });
			// Keep the board chips fresh too.
			this.buckets = {};
			this.load_bucket(this.active_bucket);
		} else if (this.view === "manager") {
			this.load_bucket(this.active_bucket);
		} else {
			this.load_operator();
		}
	}

	refresh() {
		if (this.view === "manager") {
			this.buckets = {};
		}
		this.reload();
	}

	compute_state() {
		this.active_jobs = [];
		this.queue = [];
		this.pending_submission = [];
		this.completed = [];
		// Submitted but the finished goods aren't booked yet (status "To Manufacture") — its own
		// actionable section, kept out of Completed Operations / Today's Sessions.
		this.to_manufacture = [];

		for (const jc of this.job_cards) {
			// Same materials-ready rule as job_card.js make_dashboard.
			jc._materials_ready = !!(
				jc.skip_material_transfer ||
				flt(jc.transferred_qty) >= flt(jc.for_quantity) + flt(jc.process_loss_qty) ||
				!jc.finished_good
			);

			// Submitted JCs are historical from the Shop Floor's POV — only appear here in work_order
			// mode (and, for "To Manufacture", in workstation mode too — see _fetch_job_cards).
			if (jc.docstatus === 1) {
				if (jc.status === "To Manufacture") {
					this.to_manufacture.push(jc);
				} else {
					this.completed.push(jc);
				}
				continue;
			}

			const last_log =
				jc.time_logs && jc.time_logs.length ? jc.time_logs[jc.time_logs.length - 1] : null;
			const is_running = last_log && !last_log.to_time && !jc.is_paused;
			const is_paused = jc.is_paused;

			if (is_running || is_paused) {
				this.active_jobs.push(jc);
			} else if (jc.status === "Completed") {
				// All qty accounted for but still draft — waiting on Submit.
				this.pending_submission.push(jc);
			} else {
				this.queue.push(jc);
			}
		}

		// Slot rules — all active jobs are always shown; the grid (col-md-6) wraps them 2 per row.
		//   workstation mode: capacity-many slots, expanded to fit every active job (+ empty placeholders).
		//   work_order mode:  one slot per active job (no empty placeholders).
		let slot_count;
		if (this.mode === "work_order") {
			slot_count = this.active_jobs.length;
		} else {
			slot_count = Math.max(this.capacity, this.active_jobs.length, 1);
		}

		this.slots = [];
		for (let i = 0; i < slot_count; i++) {
			this.slots.push(this.active_jobs[i] || null);
		}

		// Auto-pick: when nothing is running, surface the next queue item in the slot.
		if (this.active_jobs.length === 0 && this.queue.length > 0) {
			const next_up = this.queue.shift();
			next_up._is_next_up = true;
			this.slots[0] = next_up;
		}

		this.summary = {
			active_count: this.active_jobs.length,
			// "To Manufacture" (submitted, qty done, but the Manufacture Stock Entry is still pending)
			// isn't actually finished — count it as Pending, not Completed.
			queue_count: this.queue.length + this.to_manufacture.length,
			completed_count: this.completed.length + this.pending_submission.length,
			capacity: this.capacity,
		};
	}

	render_operator($container) {
		this.clear_timers();
		$container.empty();

		const html = frappe.render_template("shop_floor_template", {
			workstation: this.workstation,
			work_order: this.work_order,
			mode: this.mode,
			slots: this.slots,
			active_jobs: this.active_jobs,
			queue: this.queue,
			pending_submission: this.pending_submission,
			to_manufacture: this.to_manufacture,
			completed: this.completed,
			today_sessions: this.today_sessions || [],
			summary: this.summary,
			oee: this.oee,
		});
		$container.html(html);

		// Restore each Materials panel to its remembered open/closed state.
		$container.find(".mes-materials-inline").each((i, el) => {
			const $el = $(el);
			const name = $el.attr("data-job-card");
			if (!name) return;
			if (name in this.materials_open) {
				$el.toggleClass("is-open", this.materials_open[name]);
			} else {
				this.materials_open[name] = $el.hasClass("is-open");
			}
		});

		// Restore each Work Instructions panel to its remembered open/closed state.
		$container.find(".mes-instructions-inline").each((i, el) => {
			const $el = $(el);
			const name = $el.attr("data-job-card");
			if (name && name in this.instructions_open) {
				$el.toggleClass("is-open", this.instructions_open[name]);
			}
		});

		this.bind_events($container);

		for (const jc of this.active_jobs) {
			if (jc.is_paused) {
				this.render_timer(jc.name, this.elapsed_seconds(jc), $container);
			} else {
				this.start_timer_for(jc, $container);
			}
		}
	}

	clear_timers() {
		for (const id of Object.values(this.timer_intervals)) {
			clearInterval(id);
		}
		this.timer_intervals = {};
	}

	bind_events($container) {
		const me = this;

		$container.find(".mes-materials-summary").on("click", function (e) {
			if ($(e.target).closest(".mes-btn-transfer").length) return;
			const $inline = $(this).closest(".mes-materials-inline");
			const open = !$inline.hasClass("is-open");
			$inline.toggleClass("is-open", open);
			const name = $inline.attr("data-job-card");
			if (name) me.materials_open[name] = open;
		});

		$container.find(".mes-instructions-summary").on("click", function () {
			const $inline = $(this).closest(".mes-instructions-inline");
			const open = !$inline.hasClass("is-open");
			$inline.toggleClass("is-open", open);
			const name = $inline.attr("data-job-card");
			if (name) me.instructions_open[name] = open;
		});

		// Clicking a "QC Required" / "QC Available" pill runs the inline check ahead of End Session.
		$container.find(".mes-qc-pill").on("click", function () {
			const name = $(this).attr("data-job-card");
			const jc = (me.active_jobs || []).find((j) => j.name === name);
			if (jc) me.run_quality_check(jc, () => me.reload());
		});

		$container.find(".mes-btn-start").on("click", function () {
			me.start_job($(this).attr("data-job-card"));
		});
		$container.find(".mes-btn-pause").on("click", function () {
			me.pause_job($(this).attr("data-job-card"));
		});
		$container.find(".mes-btn-resume").on("click", function () {
			me.resume_job($(this).attr("data-job-card"));
		});
		$container.find(".mes-btn-end-session").on("click", function () {
			me.end_session($(this).attr("data-job-card"));
		});
		$container.find(".mes-btn-submit").on("click", function () {
			me.submit_job_card($(this).attr("data-job-card"));
		});
		$container.find(".mes-btn-make-entry").on("click", function () {
			me.make_manufacture_entry($(this).attr("data-job-card"));
		});
		$container.find(".mes-btn-transfer").on("click", function (e) {
			e.preventDefault();
			me.transfer_materials($(this).attr("data-job-card"));
		});
	}

	// ── Operator actions (unchanged behaviour, reload() instead of load()) ─────
	start_job(job_card) {
		const me = this;
		if (this.mode === "workstation" && this.active_jobs.length >= this.capacity) {
			frappe.msgprint({
				title: __("Capacity Reached"),
				message: __(
					"This machine can run at most {0} job(s) in parallel. Pause or complete a running job before starting another.",
					[this.capacity]
				),
				indicator: "orange",
			});
			return;
		}

		const default_employee = this.user_employee;
		const dialog = new frappe.ui.Dialog({
			title: __("Start Job"),
			fields: [
				{
					label: __("Start Time"),
					fieldname: "start_time",
					fieldtype: "Datetime",
					default: frappe.datetime.now_datetime(),
				},
				{ fieldtype: "Section Break" },
				{
					label: __("Employees"),
					fieldname: "employees",
					fieldtype: "Table",
					data: default_employee ? [{ employee: default_employee }] : [],
					fields: [
						{
							label: __("Employee"),
							fieldname: "employee",
							fieldtype: "Link",
							options: "Employee",
							in_list_view: 1,
						},
					],
				},
			],
			primary_action_label: __("Start"),
			primary_action: (values) => {
				dialog.hide();
				me.update_job_card(job_card, "start_timer", {
					start_time: values.start_time,
					employees: values.employees || [],
				});
			},
		});
		dialog.show();
		this.bind_enter_submit(dialog);
	}

	// Make a dialog fully keyboard-operable: Enter triggers the primary action, so an operator
	// never has to reach for the mouse. Enter is left alone inside multi-line fields and while an
	// autocomplete (Link/Select) dropdown is open, so it can still pick a value.
	bind_enter_submit(dialog) {
		dialog.$wrapper.on("keydown.sfenter", (e) => {
			if (e.key !== "Enter" || e.shiftKey) return;
			if ($(e.target).is("textarea")) return;
			if ($(".awesomplete > ul:not([hidden])").length) return;
			const $btn = dialog.get_primary_btn();
			if (
				$btn &&
				$btn.length &&
				$btn.is(":visible") &&
				!$btn.hasClass("disabled") &&
				!$btn.prop("disabled")
			) {
				e.preventDefault();
				e.stopPropagation();
				$btn.trigger("click");
			}
		});
	}

	pause_job(jc_name) {
		this.update_job_card(jc_name, "pause_job", { end_time: frappe.datetime.now_datetime() });
	}

	resume_job(jc_name) {
		this.update_job_card(jc_name, "resume_job", { start_time: frappe.datetime.now_datetime() });
	}

	end_session(jc_name) {
		const me = this;
		const jc = this.active_jobs.find((j) => j.name === jc_name);
		if (!jc) return;

		let pending = flt(jc.for_quantity) - flt(jc.total_completed_qty);
		if (flt(jc.pending_qty) > 0) {
			pending = flt(jc.pending_qty);
		}

		const fields = [
			{
				fieldtype: "Float",
				label: __("Qty to Manufacture"),
				fieldname: "for_quantity",
				reqd: 1,
				default: pending,
				change() {
					const d = me.session_dialog;
					d.set_value("completed_qty", d.get_value("for_quantity"));
					d.set_value("process_loss_qty", 0);
				},
			},
			{
				fieldtype: "Float",
				label: __("Completed Quantity"),
				fieldname: "completed_qty",
				reqd: 1,
				default: pending,
				change() {
					const d = me.session_dialog;
					const remaining = flt(d.get_value("for_quantity")) - flt(d.get_value("completed_qty"));
					if (remaining > 0 && remaining !== flt(d.get_value("pending_qty"))) {
						d.set_value("pending_qty", remaining);
					}
				},
			},
			{
				fieldtype: "Float",
				label: __("Pending Quantity"),
				fieldname: "pending_qty",
				default: 0.0,
				change() {
					const d = me.session_dialog;
					const pl =
						flt(d.get_value("for_quantity")) -
						flt(d.get_value("completed_qty")) -
						flt(d.get_value("pending_qty"));
					if (pl >= 0 && pl !== flt(d.get_value("process_loss_qty"))) {
						d.set_value("process_loss_qty", pl);
					}
				},
			},
			{
				fieldtype: "Float",
				label: __("Process Loss Quantity"),
				fieldname: "process_loss_qty",
				default: 0.0,
				change() {
					const d = me.session_dialog;
					const remaining =
						flt(d.get_value("for_quantity")) -
						flt(d.get_value("completed_qty")) -
						flt(d.get_value("process_loss_qty"));
					if (remaining >= 0 && remaining !== flt(d.get_value("pending_qty"))) {
						d.set_value("pending_qty", remaining);
					}
				},
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Datetime",
				label: __("End Time"),
				fieldname: "end_time",
				default: frappe.datetime.now_datetime(),
			},
		];

		const get_payload = () => {
			const data = me.session_dialog.get_values();
			if (!data) return null;
			if (flt(data.completed_qty) <= 0) {
				frappe.throw(__("Completed Quantity should be greater than 0"));
			}
			return {
				job_card: jc.name,
				qty: flt(data.completed_qty),
				for_quantity: flt(data.for_quantity),
				pending_qty: flt(data.pending_qty),
				process_loss_qty: flt(data.process_loss_qty),
				end_time: data.end_time,
			};
		};

		const save_and_continue = () => {
			const args = get_payload();
			if (!args) return;
			me.session_dialog.hide();
			frappe.call({
				method: "erpnext.manufacturing.page.shop_floor.shop_floor.save_and_continue",
				args: args,
				freeze: true,
				freeze_message: __("Saving job card..."),
				callback: () => me.reload(),
			});
		};

		const finalize_submit = (args) => {
			frappe.call({
				method: "erpnext.manufacturing.page.shop_floor.shop_floor.complete_and_submit",
				args: args,
				freeze: true,
				freeze_message: __("Submitting job card..."),
				callback: (r) => {
					me.reload();
					if (r.message && r.message.finished_good) {
						me.prompt_manufacture_entry(jc.name);
					}
				},
			});
		};

		const submit_session = () => {
			const args = get_payload();
			if (!args) return;
			me.session_dialog.hide();
			// Guided QC gate: a job card that requires inspection must pass an inline Quality Check
			// before it is submitted (mirrors Job Card.validate_inspection on the server). Once the
			// inspection is recorded, finalize the session submit.
			if (jc.qc && jc.qc.required && jc.qc.status !== "Accepted") {
				me.run_quality_check(jc, () => finalize_submit(args));
			} else {
				finalize_submit(args);
			}
		};

		me.session_dialog = new frappe.ui.Dialog({
			title: __("End Session"),
			fields: fields,
			primary_action_label: __("Submit"),
			primary_action: submit_session,
			secondary_action_label: __("Save & Continue"),
			secondary_action: save_and_continue,
		});
		me.session_dialog.show();
		me.bind_enter_submit(me.session_dialog);
	}

	// ── Inline Quality Check ─────────────────────────────────────────────────────
	// Fetch the operation's Quality Inspection template and open a guided pass/fail checklist.
	// `on_pass` runs once the inspection has been recorded (and is not rejected).
	run_quality_check(jc, on_pass) {
		const me = this;
		frappe.call({
			method: "erpnext.manufacturing.page.shop_floor.shop_floor.get_quality_inspection_checklist",
			args: { job_card: jc.name },
			freeze: true,
			freeze_message: __("Loading quality checklist..."),
			callback: (r) => {
				const info = r.message || {};
				if (!info.template || !(info.parameters || []).length) {
					// Inspection is required but the operation has no template/parameters to fill —
					// there is nothing to capture inline. Point the user at the configuration.
					frappe.msgprint({
						title: __("Quality Inspection Template Missing"),
						indicator: "orange",
						message: __(
							"This operation requires a Quality Inspection but no template with parameters is configured. Set a Quality Inspection Template on Operation {0} to inspect from the Shop Floor.",
							[jc.operation || ""]
						),
					});
					return;
				}
				me.show_qc_dialog(jc, info, on_pass);
			},
		});
	}

	show_qc_dialog(jc, info, on_pass) {
		const me = this;
		const params = info.parameters || [];
		// Per-row operator input, keyed by row index (avoids escaping issues with parameter names).
		const state = {}; // idx -> "Accepted" | "Rejected"

		const rows = params
			.map((p, i) => {
				const spec = frappe.utils.escape_html(p.specification);
				let criteria = "";
				if (p.numeric) {
					const lo = p.min_value !== null && p.min_value !== undefined ? p.min_value : "−∞";
					const hi = p.max_value !== null && p.max_value !== undefined ? p.max_value : "∞";
					criteria = __("Acceptable range: {0} to {1}", [lo, hi]);
				} else if (p.value) {
					criteria = __("Expected: {0}", [frappe.utils.escape_html(p.value)]);
				}
				const control = p.numeric
					? `<input type="number" step="any" class="form-control mes-qc-reading" data-idx="${i}" placeholder="${__(
							"Measured value"
					  )}">`
					: `<span class="mes-qc-passfail" data-idx="${i}">
							<button type="button" class="pass" data-val="Accepted">${__("Pass")}</button>
							<button type="button" class="fail" data-val="Rejected">${__("Fail")}</button>
						</span>`;
				return `<div class="mes-qc-row">
						<div class="mes-qc-spec">
							<div class="mes-qc-spec-name">${spec}</div>
							${criteria ? `<div class="mes-qc-spec-sub">${criteria}</div>` : ""}
						</div>
						<div class="mes-qc-controls">${control}</div>
					</div>`;
			})
			.join("");

		const dialog = new frappe.ui.Dialog({
			title: __("Quality Check"),
			size: "large",
			fields: [
				{
					fieldtype: "HTML",
					options: `<div class="mes-qc-intro text-muted" style="margin-bottom: 8px;">${__(
						"Inspect {0} for job card {1}",
						[frappe.utils.escape_html(info.item_code || ""), frappe.utils.escape_html(jc.name)]
					)}</div><div class="mes-qc-list">${rows}</div>`,
				},
			],
			primary_action_label: __("Submit Inspection"),
			primary_action: () => {
				const readings = [];
				let missing = false;
				params.forEach((p, i) => {
					if (p.numeric) {
						const val = dialog.$wrapper.find(`.mes-qc-reading[data-idx="${i}"]`).val();
						if (val === "" || val === undefined || val === null) missing = true;
						readings.push({ specification: p.specification, reading_value: val });
					} else {
						if (!state[i]) missing = true;
						readings.push({
							specification: p.specification,
							status: state[i],
							reading_value: "",
						});
					}
				});
				if (missing) {
					frappe.msgprint(__("Please complete every check before submitting the inspection."));
					return;
				}
				dialog.hide();
				frappe.call({
					method: "erpnext.manufacturing.page.shop_floor.shop_floor.submit_quality_inspection",
					args: { job_card: jc.name, readings: JSON.stringify(readings) },
					freeze: true,
					freeze_message: __("Recording inspection..."),
					callback: (r) => {
						const res = r.message || {};
						if (res.status === "Rejected") {
							// Don't auto-proceed on a rejected inspection — the server gate may block the
							// submit anyway (per Stock Settings), and the operator should decide next steps.
							frappe.msgprint({
								title: __("Inspection Rejected"),
								indicator: "red",
								message: __(
									"Quality Inspection {0} is Rejected. Resolve the issue or follow your rejection process before submitting the job card.",
									[res.name || ""]
								),
							});
							me.reload();
							return;
						}
						if (on_pass) on_pass();
					},
				});
			},
		});

		dialog.show();
		// Pass/Fail toggles for qualitative parameters.
		dialog.$wrapper.find(".mes-qc-passfail button").on("click", function () {
			const $btn = $(this);
			const $grp = $btn.closest(".mes-qc-passfail");
			$grp.find("button").removeClass("active");
			$btn.addClass("active");
			state[$grp.attr("data-idx")] = $btn.attr("data-val");
		});
	}

	prompt_manufacture_entry(jc_name) {
		const me = this;
		const dialog = new frappe.ui.Dialog({
			title: __("Job Card Submitted"),
			fields: [
				{
					fieldtype: "HTML",
					options: `
						<div style="text-align: left; padding: 12px 0 4px;">
							<div style="font-size: 1.05em; margin-bottom: 6px;">
								${__("Job card {0} has been submitted.", [frappe.utils.escape_html(jc_name)])}
							</div>
							<div style="color: var(--text-muted);">
								${__("Create a Manufacture stock entry for the finished goods?")}
							</div>
						</div>
					`,
				},
			],
			primary_action_label: __("Make Manufacture Entry"),
			primary_action: () => {
				dialog.hide();
				me.make_manufacture_entry(jc_name);
			},
			secondary_action_label: __("Skip"),
			secondary_action: () => dialog.hide(),
		});
		dialog.show();
		this.bind_enter_submit(dialog);
	}

	submit_job_card(jc_name) {
		const me = this;
		frappe.confirm(__("Submit job card {0}? This finalizes the job card.", [jc_name]), () => {
			frappe.call({
				method: "erpnext.manufacturing.page.shop_floor.shop_floor.submit_job_card",
				args: { job_card: jc_name },
				freeze: true,
				freeze_message: __("Submitting job card..."),
				callback: () => me.reload(),
			});
		});
	}

	make_manufacture_entry(jc_name) {
		frappe.call({
			method: "erpnext.manufacturing.page.shop_floor.shop_floor.make_manufacture_stock_entry",
			args: { job_card: jc_name },
			freeze: true,
			freeze_message: __("Preparing stock entry..."),
			callback: (r) => {
				if (r.message && r.message.name) {
					window.open(`/app/stock-entry/${encodeURIComponent(r.message.name)}`, "_blank");
				}
			},
		});
	}

	transfer_materials(jc_name) {
		if (!jc_name) return;
		frappe.call({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_stock_entry",
			args: { source_name: jc_name },
			callback: (r) => {
				const doc = frappe.model.sync(r.message);
				frappe.set_route("Form", doc[0].doctype, doc[0].name);
			},
		});
	}

	update_job_card(job_card, method, data, on_success) {
		const me = this;
		frappe.call({
			method: "erpnext.manufacturing.doctype.workstation.workstation.update_job_card",
			args: {
				job_card: job_card,
				method: method,
				start_time: data.start_time || "",
				employees: data.employees || [],
				end_time: data.end_time || "",
				qty: data.qty || 0,
				for_quantity: data.for_quantity || 0,
				pending_qty: data.pending_qty || 0,
				process_loss_qty: data.process_loss_qty || 0,
				auto_submit: data.auto_submit || 0,
			},
			freeze: true,
			freeze_message: __("Updating job card..."),
			callback: () => {
				me.reload();
				if (on_success) on_success();
			},
		});
	}

	// ── Timers ────────────────────────────────────────────────────────────────
	start_timer_for(jc, $container) {
		let elapsed = this.elapsed_seconds(jc);
		this.render_timer(jc.name, elapsed, $container);
		this.timer_intervals[jc.name] = setInterval(() => {
			elapsed += 1;
			this.render_timer(jc.name, elapsed, $container);
		}, 1000);
	}

	elapsed_seconds(jc) {
		let total = 0;
		for (const log of jc.time_logs || []) {
			if (log.to_time) {
				if (log.time_in_mins) {
					total += flt(log.time_in_mins, 2) * 60;
				} else {
					total += moment(log.to_time).diff(log.from_time, "seconds");
				}
			} else {
				total += moment().diff(log.from_time, "seconds");
			}
		}
		return total;
	}

	render_timer(jc_name, seconds, $container) {
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds - h * 3600) / 60);
		const s = cint(seconds - h * 3600 - m * 60);
		const pad = (n) => (n < 10 ? "0" + n : String(n));

		const scope = $container || this.wrapper;
		const timer = scope.find(`.mes-job-timer[data-job-card="${jc_name}"]`);
		timer.find(".h").text(pad(h));
		timer.find(".m").text(pad(m));
		timer.find(".s").text(pad(s));
	}

	// ── Realtime + lifecycle ───────────────────────────────────────────────────
	bind_realtime() {
		frappe.realtime.on("update_workstation_status", (data) => {
			if (data && data.name === this.op_state.workstation) {
				this.reload();
			}
		});
	}

	bind_lifecycle() {
		// Frappe has no on_page_hide hook, so toggle immersive mode + keyboard binding on
		// route changes ourselves.
		this._route_handler = () => {
			const on_page = (frappe.get_route_str() || "").startsWith("shop-floor");
			if (on_page) {
				$(document.body).addClass("shop-floor-active");
				this.bind_keys();
			} else {
				$(document.body).removeClass("shop-floor-active");
				this.unbind_keys();
				this.clear_timers();
			}
		};
		frappe.router.on("change", this._route_handler);
	}

	on_show() {
		$(document.body).addClass("shop-floor-active");
		this.bind_keys();
		// Cached re-navigation (e.g. the Work Order "Shop Floor" button) lands here with fresh
		// route_options; init() handles the very first load before we're initialized.
		if (this.initialized) this.apply_route_options();
	}

	// ── Keyboard ────────────────────────────────────────────────────────────────
	bind_keys() {
		$(document).off("keydown.shopfloor");
		$(document).on("keydown.shopfloor", (e) => this.handle_key(e));
	}

	unbind_keys() {
		$(document).off("keydown.shopfloor");
	}

	is_typing(e) {
		const tag = (e.target.tagName || "").toLowerCase();
		return tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable;
	}

	handle_key(e) {
		// Let dialogs own the keyboard while open.
		if ($(".modal:visible").length) return;

		const typing = this.is_typing(e);

		// Escape works even while typing (blur the search / close the detail pane).
		if (e.key === "Escape") {
			if (typing) {
				e.target.blur();
				return;
			}
			if (this.view === "manager" && this.selected_wo) {
				this.close_wo();
				e.preventDefault();
			}
			return;
		}

		if (typing) return;

		switch (e.key) {
			case "?":
				this.show_help();
				e.preventDefault();
				return;
			case "/":
				this.topbar_center.find(".sf-search-input").focus();
				e.preventDefault();
				return;
			case "r":
				this.refresh();
				e.preventDefault();
				return;
			case "b":
				this.open_scanner();
				e.preventDefault();
				return;
			case "1":
			case "2":
				if (this.view === "manager" && MANAGER_BUCKETS[cint(e.key) - 1]) {
					this.switch_bucket(MANAGER_BUCKETS[cint(e.key) - 1].key);
					e.preventDefault();
				}
				return;
		}

		// View switch chord: "g" then "m"/"o".
		if (e.key === "g") {
			this._g_pending = true;
			setTimeout(() => (this._g_pending = false), 600);
			return;
		}
		if (this._g_pending && (e.key === "m" || e.key === "o")) {
			this._g_pending = false;
			if (this.can_manage) this.set_view(e.key === "m" ? "manager" : "operator");
			return;
		}

		// Navigation.
		if (e.key === "ArrowDown" || e.key === "j") {
			this.move_focus(1);
			e.preventDefault();
			return;
		}
		if (e.key === "ArrowUp" || e.key === "k") {
			this.move_focus(-1);
			e.preventDefault();
			return;
		}
		if (e.key === "Enter") {
			this.activate_focus();
			e.preventDefault();
			return;
		}

		// Job actions on the focused card — reuse the rendered buttons.
		const map = {
			s: ".mes-btn-start, .mes-btn-resume",
			p: ".mes-btn-pause, .mes-btn-resume",
			e: ".mes-btn-end-session",
			t: ".mes-btn-transfer",
		};
		if (e.key === "S" && e.shiftKey) {
			this.click_job_action(".mes-btn-submit");
			e.preventDefault();
			return;
		}
		if (map[e.key]) {
			this.click_job_action(map[e.key]);
			e.preventDefault();
		}
	}

	// Job actions act on the focused job card (operator view); when the focus is on a board
	// work order (manager view with the detail open) they fall back to the detail's active job.
	click_job_action(selector) {
		const $el = this.focused_el();
		if ($el && $el.attr("data-kind") === "job") {
			const $btn = $el.find(selector).filter(":visible").first();
			if ($btn.length) {
				$btn.trigger("click");
				return;
			}
		}
		const scope = this.current_op_container();
		if (scope && scope.length) {
			const $btn = scope.find(selector).filter(":visible").first();
			if ($btn.length) $btn.trigger("click");
		}
	}

	focusables() {
		// Manager always navigates the board work orders — even with the detail open, so the
		// arrow keys switch work orders. The standalone operator view navigates its job cards.
		const scope = this.view === "manager" ? this.board_container : this.current_op_container();
		if (!scope || !scope.length) return $();
		return scope.find("[data-sf-focusable]");
	}

	move_focus(delta) {
		const $items = this.focusables();
		if (!$items.length) return;
		this.focus_index = Math.max(0, Math.min($items.length - 1, this.focus_index + delta));
		$items.removeClass("sf-focused");
		const $target = $items.eq(this.focus_index);
		$target.addClass("sf-focused");
		$target[0].scrollIntoView({ block: "nearest", behavior: "smooth" });
		// Browsing work orders with the detail already open → switch the detail to the focused one.
		if (this.view === "manager" && this.selected_wo && $target.attr("data-kind") === "wo") {
			this.open_wo($target.attr("data-name"));
		}
	}

	focused_el() {
		const $items = this.focusables();
		if (this.focus_index < 0 || this.focus_index >= $items.length) return null;
		return $items.eq(this.focus_index);
	}

	activate_focus() {
		const $el = this.focused_el();
		if (!$el) return;
		if ($el.attr("data-kind") === "wo") {
			this.open_wo($el.attr("data-name"));
		} else {
			// First visible primary button drives the job card (Start / Resume / End Session).
			const $btn = $el.find(".btn-primary:visible").first();
			if ($btn.length) $btn.trigger("click");
		}
	}

	show_help() {
		const rows = [
			["?", __("Show this help")],
			["/", __("Search work orders")],
			["r", __("Refresh")],
			["b", __("Scan job card")],
			["g then m / o", __("Switch Board / Operator view")],
			["1 / 2", __("Switch board tab")],
			["↑ / ↓  or  j / k", __("Move selection")],
			["Enter", __("Open work order / run primary action")],
			["Esc", __("Close detail / blur search")],
			["s", __("Start / Resume job")],
			["p", __("Pause / Resume job")],
			["e", __("End session for active job")],
			["t", __("Transfer materials")],
			["Shift + S", __("Submit focused job card")],
		];
		const html = `<div class="sf-help">${rows
			.map((r) => `<div class="sf-help-row"><kbd>${r[0]}</kbd><span>${r[1]}</span></div>`)
			.join("")}</div>`;
		const d = new frappe.ui.Dialog({
			title: __("Keyboard Shortcuts"),
			fields: [{ fieldtype: "HTML", options: html }],
		});
		d.show();
	}

	// ── Scanner ──────────────────────────────────────────────────────────────
	open_scanner() {
		const me = this;
		const dialog = new frappe.ui.Dialog({
			title: __("Scan Job Card"),
			fields: [
				{
					label: __("Scan or enter Job Card"),
					fieldname: "job_card",
					fieldtype: "Data",
					options: "Barcode",
				},
			],
			primary_action_label: __("Continue"),
			primary_action: (values) => {
				if (!values.job_card) return;
				dialog.hide();
				me.handle_scanned_job_card(values.job_card);
			},
		});
		dialog.show();
		this.bind_enter_submit(dialog);
	}

	handle_scanned_job_card(job_card) {
		const me = this;
		const jc = (this.job_cards || []).find((j) => j.name === job_card);
		if (jc) {
			me.route_scanned_action(jc);
			return;
		}
		frappe.db.get_value("Job Card", job_card, ["status", "is_paused", "docstatus"]).then((r) => {
			const data = r && r.message;
			if (!data || !data.status) {
				frappe.msgprint(__("Job Card {0} was not found.", [job_card]));
				return;
			}
			if (cint(data.docstatus) === 1) {
				frappe.msgprint(__("Job Card {0} is already submitted.", [job_card]));
			} else if (cint(data.is_paused)) {
				me.resume_job(job_card);
			} else if (data.status === "Work In Progress") {
				frappe.msgprint(
					__(
						"Job Card {0} is already running. Open its machine or work order to pause or complete it.",
						[job_card]
					)
				);
			} else if (data.status === "Completed") {
				me.submit_job_card(job_card);
			} else {
				me.start_job(job_card);
			}
		});
	}

	route_scanned_action(jc) {
		const me = this;
		if (jc.docstatus === 1) {
			frappe.msgprint(__("Job Card {0} is already submitted.", [jc.name]));
			return;
		}
		if (jc.status === "Completed") {
			me.submit_job_card(jc.name);
			return;
		}
		if (jc.is_paused) {
			me.resume_job(jc.name);
			return;
		}
		const last_log = jc.time_logs && jc.time_logs.length ? jc.time_logs[jc.time_logs.length - 1] : null;
		const is_running = !!(last_log && !last_log.to_time);
		if (is_running) {
			me.prompt_running_action(jc);
		} else {
			me.start_job(jc.name);
		}
	}

	prompt_running_action(jc) {
		const me = this;
		const dialog = new frappe.ui.Dialog({
			title: __("Job {0} is running", [jc.name]),
			fields: [
				{
					fieldtype: "HTML",
					options: `
						<div style="padding: 8px 0; color: var(--text-muted);">
							${__("{0} is already in progress. Pause it or complete the session.", [
								frappe.utils.escape_html(jc.finished_good || jc.production_item || jc.name),
							])}
						</div>
					`,
				},
			],
			primary_action_label: __("Complete"),
			primary_action: () => {
				dialog.hide();
				me.end_session(jc.name);
			},
			secondary_action_label: __("Pause"),
			secondary_action: () => {
				dialog.hide();
				me.pause_job(jc.name);
			},
		});
		dialog.show();
		this.bind_enter_submit(dialog);
	}

	// ── Route options (e.g. the Work Order "Shop Floor" button) ────────────────
	apply_route_options() {
		const opts = frappe.route_options;
		if (!opts || (!opts.work_order && !opts.workstation)) {
			return;
		}
		frappe.route_options = null;

		// A specific work order / machine was requested — show it in the operator view.
		this.view = "operator";
		this.render_shell_controls();
		this.render_view();
		Promise.all([
			this.work_order_filter.set_value(opts.work_order || ""),
			this.workstation_filter.set_value(opts.workstation || ""),
		]).then(() => this.load_operator());
	}

	// ── Styles ──────────────────────────────────────────────────────────────────
	styles() {
		return `<style>
			/* Immersive mode — give the floor view the whole screen. */
			body.shop-floor-active .page-head { display: none; }
			body.shop-floor-active .layout-main-section { padding: 0; border: none; background: var(--fg-color); }
			body.shop-floor-active .layout-main-section-wrapper { margin-bottom: 0; }

			.sf-app {
				display: flex;
				flex-direction: column;
				height: calc(100vh - var(--navbar-height, 60px));
				background: var(--fg-color);
			}

			/* Top bar */
			.sf-topbar {
				flex: 0 0 auto;
				display: flex;
				align-items: center;
				gap: 16px;
				padding: 10px 16px;
				border-bottom: 1px solid var(--border-color);
				background: var(--card-bg, var(--fg-color));
			}
			.sf-topbar-left { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
			.sf-topbar-center { flex: 1 1 auto; display: flex; justify-content: center; align-items: center; gap: 14px; min-width: 0; }
			.sf-toggle { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-muted); white-space: nowrap; cursor: pointer; margin: 0; user-select: none; }
			.sf-toggle input { cursor: pointer; width: 15px; height: 15px; margin: 0; }
			.sf-topbar-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
			.sf-btn-theme { font-size: 15px; line-height: 1; min-width: 30px; }
			.sf-title { font-size: 18px; font-weight: 700; color: var(--text-color); display: inline-flex; align-items: center; gap: 8px; }
			.sf-title .sf-brand-icon { flex-shrink: 0; width: 22px; height: 22px; border-radius: 5px; }

			.sf-view-toggle { display: inline-flex; border: 1px solid var(--border-color); border-radius: var(--border-radius); overflow: hidden; }
			.sf-view-btn { border: none; background: var(--fg-color); padding: 5px 12px; font-size: 13px; color: var(--text-muted); cursor: pointer; }
			.sf-view-btn.active { background: var(--control-bg); color: var(--text-color); font-weight: 600; }

			.sf-tabs { display: flex; gap: 6px; }
			.sf-tab {
				display: inline-flex; align-items: center; gap: 6px;
				border: 1px solid transparent; background: transparent;
				padding: 6px 12px; border-radius: var(--border-radius);
				font-size: 14px; color: var(--text-muted); cursor: pointer;
			}
			.sf-tab:hover { background: var(--bg-color); }
			.sf-tab:focus, .sf-tab:focus-visible { outline: none; box-shadow: none; }
			.sf-tab.active { background: var(--control-bg); color: var(--text-color); font-weight: 600; }
			.sf-tab-count { font-variant-numeric: tabular-nums; color: var(--text-muted); }
			.sf-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
			.sf-dot.green { background: var(--green-500, #38a169); }
			.sf-dot.orange { background: var(--orange-500, #d97706); }
			.sf-dot.blue { background: var(--blue-500, #2490ef); }

			.sf-search { position: relative; width: 100%; max-width: 420px; display: flex; align-items: center; }
			.sf-search .icon { position: absolute; left: 10px; color: var(--text-muted); }
			.sf-search-input {
				width: 100%; padding: 7px 12px 7px 32px;
				border: 1px solid var(--border-color); border-radius: var(--border-radius);
				background: var(--control-bg); color: var(--text-color); font-size: 14px;
			}
			.sf-filters { display: flex; align-items: center; gap: 10px; width: 100%; max-width: 520px; }
			/* Frappe form controls bring their own form-group margins + label/help spacing; strip
			   them so the inputs sit flush and vertically centered in the topbar. */
			.sf-filter-control { flex: 1; margin: 0; }
			.sf-filter-control .form-group { margin: 0; }
			.sf-filter-control .control-label,
			.sf-filter-control .help-box,
			.sf-filter-control .clearfix { display: none; }

			/* Body */
			.sf-body { flex: 1 1 auto; min-height: 0; display: flex; overflow: hidden; }
			.sf-board { flex: 1 1 auto; overflow-y: auto; padding: 16px; }
			.sf-operator { flex: 1 1 auto; overflow-y: auto; padding: 16px; }
			.sf-detail { flex: 1 1 auto; overflow-y: auto; border-left: 1px solid var(--border-color); display: none; }
			.sf-body.detail-open .sf-board { flex: 0 0 380px; }

			.sf-empty { text-align: center; color: var(--text-muted); padding: 60px 20px; font-size: 1.1em; }

			/* Work order grid */
			.sf-wo-grid {
				display: grid;
				grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
				align-items: start;
				gap: 14px;
			}
			.sf-body.detail-open .sf-wo-grid { grid-template-columns: minmax(0, 1fr); }
			.sf-wo-card {
				display: flex; flex-direction: column; min-width: 0;
				border: 1px solid var(--border-color); border-radius: 12px;
				background: var(--card-bg, var(--fg-color)); padding: 16px;
				cursor: pointer; transition: box-shadow 0.12s ease, border-color 0.12s ease, transform 0.12s ease;
				outline: none;
			}
			.sf-wo-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.08); transform: translateY(-1px); }
			[data-theme="dark"] .sf-wo-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.45); }
			/* --primary is a fixed near-black (#171717) that the dark theme never remaps, so a ring
			   drawn with it disappears on dark cards. Light theme keeps the dark ring; dark theme
			   needs an accent colour — a light-gray ring on gray cards is still too subtle. */
			.sf-wo-card.sf-selected { border-color: var(--primary-color, var(--primary)); }
			.sf-wo-card.sf-focused { box-shadow: 0 0 0 1px var(--primary-color, var(--primary)); }
			[data-theme="dark"] .sf-wo-card.sf-selected { border-color: var(--blue-500, #2490ef); }
			[data-theme="dark"] .sf-wo-card.sf-focused {
				box-shadow: 0 0 0 1px var(--blue-500, #2490ef);
				border-color: transparent;
			}
			.sf-wo-top { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
			.sf-wo-image { width: 66px; height: 66px; aspect-ratio: 1 / 1; align-self: center; border-radius: 12px; overflow: hidden; background: var(--bg-color); border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
			.sf-wo-image img { width: 100%; height: 100%; object-fit: cover; }
			.sf-wo-image-fallback { font-size: 18px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }
			.sf-wo-head { flex: 1; min-width: 0; }
			.sf-wo-title { font-size: 17px; font-weight: 600; color: var(--text-color); margin-bottom: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.sf-wo-ws { font-size: 13px; font-weight: 500; color: var(--text-color); margin-bottom: 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.sf-wo-ws-icon { margin-right: 2px; }
			.sf-wo-id { display: flex; align-items: center; gap: 8px; font-size: 12px; min-width: 0; }
			.sf-wo-id a { color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			/* Compact status indicator on the work-order card — the active tab already names the
			   bucket, so a coloured dot (status text in the tooltip) is enough. */
			.sf-wo-status-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; display: inline-block; }
			.sf-wo-status-dot.green { background: var(--green-500, #38a169); }
			.sf-wo-status-dot.orange { background: var(--orange-500, #d97706); }
			.sf-wo-status-dot.yellow { background: var(--yellow-500, #d97706); }
			.sf-wo-status-dot.blue { background: var(--blue-500, #2490ef); }
			.sf-wo-status-dot.red { background: var(--red-500, #e53e3e); }
			.sf-wo-status-dot.purple { background: var(--purple-500, #7c3aed); }
			.sf-wo-status-dot.gray { background: var(--gray-500, #9ca3af); }
			.sf-wo-progress-block { margin-bottom: 12px; }
			.sf-wo-progress-label { display: flex; align-items: center; justify-content: space-between; font-size: 13px; color: var(--text-muted); margin-bottom: 6px; }
			.sf-wo-progress-count { font-weight: 600; color: var(--text-color); font-variant-numeric: tabular-nums; }
			.sf-progress { display: flex; height: 10px; border-radius: 6px; background: var(--gray-200, #d1d5db); overflow: hidden; }
			[data-theme="dark"] .sf-progress { background: var(--gray-700, #374151); }
			.sf-progress-seg { height: 100%; transition: width 0.3s ease; }
			.sf-seg-done { background: var(--green-400, #9ae6b4); }
			.sf-seg-wip { background: var(--orange-400, #fbd38d); }

			.sf-board-more { padding: 16px 0 4px; text-align: center; }
			.sf-board-foot { font-size: 13px; }

			/* Detail pane head */
			.sf-detail-head { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--border-color); position: sticky; top: 0; background: var(--fg-color); z-index: 1; }
			.sf-detail-title { font-weight: 600; flex: 1; }
			.sf-detail-body { padding: 16px; }

			.sf-help-row { display: flex; align-items: center; gap: 14px; padding: 6px 0; }
			.sf-help-row kbd { flex: 0 0 150px; font-family: var(--font-stack-mono, monospace); }

			@media (max-width: 768px) {
				.sf-topbar { flex-wrap: wrap; gap: 10px; }
				.sf-topbar-center { order: 3; flex-basis: 100%; }
				.sf-search, .sf-filters { max-width: none; }
				.sf-body.detail-open .sf-board { display: none; }
				.sf-body.detail-open .sf-detail { flex-basis: 100%; }
				.sf-detail { border-left: none; }
			}
		</style>`;
	}
}

frappe.ui.ShopFloor = ShopFloor;
