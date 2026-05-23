// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors

frappe.provide("erpnext.party_import");

frappe.pages["party-import-wizard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Party Import"),
		single_column: true,
	});
	const wizard = new erpnext.party_import.Wizard(page);
	wizard.render();
	wrapper.wizard = wizard;
};

frappe.pages["party-import-wizard"].on_page_show = function (wrapper) {
	// Pageview.js auto-registers a Custom breadcrumb with `route: frappe.get_route_str()`,
	// which is just the bare slug ("party-import-wizard") — a relative href. When the
	// URL has a trailing segment like /app/party-import-wizard/PIL-0001, clicking the
	// breadcrumb resolves the relative href against /app/party-import-wizard/ and gives
	// /app/party-import-wizard/party-import-wizard. Override with an absolute route.
	frappe.breadcrumbs.add({
		type: "Custom",
		label: __("Party Import"),
		route: "/app/party-import-wizard",
	});

	const route = frappe.get_route();
	if (!wrapper.wizard) return;
	if (route.length > 1 && wrapper.wizard.state.import_name !== route[1]) {
		wrapper.wizard.resume(route[1]);
	}
};

const STEPS = [
	{ key: "start", label: __("Start") },
	{ key: "upload", label: __("Upload") },
	{ key: "map", label: __("Map") },
	{ key: "resolve", label: __("Resolve") },
	{ key: "review", label: __("Review") },
	{ key: "progress", label: __("Import") },
	{ key: "result", label: __("Done") },
];

// ============================================================================
// Wizard — orchestrator: state, routing, stepper, shared API + data loading
// ============================================================================

erpnext.party_import.Wizard = class Wizard {
	constructor(page) {
		this.page = page;
		this.$body = $(page.body).addClass("pi-page");
		this._reset_fields();
	}

	_reset_fields() {
		this.state = {
			step: "start",
			party_type: null,
			source_format: "Generic",
			mapping_template_name: null,
			file_url: null,
			file_name: null,
			file_size: null,
			uploading_file_name: null,
			uploading_file_size: null,
			upload_error: null,
			import_name: null,
			columns: [],
			sample_rows: [],
			target_fields: [],
			parse_warnings: [],
			mappings: {},
			dependencies: {},
			resolutions: {},
			dep_expanded: {},
			summary: null,
			progress: null,
		};
	}

	render() {
		this.$body.html(`
			<div class="pi-container">
				<div class="pi-stepper-wrap"></div>
				<div class="pi-stage"></div>
			</div>
		`);
		this.$stepper = this.$body.find(".pi-stepper-wrap");
		this.$stage = this.$body.find(".pi-stage");
		this.update();
	}

	go(step) {
		this.state.step = step;
		this.update();
	}

	update() {
		this.render_stepper();
		this._current_step().render();
	}

	_current_step() {
		const map = {
			start: StartStep,
			upload: UploadStep,
			map: MapStep,
			resolve: ResolveStep,
			review: ReviewStep,
			fix: FixStep,
			progress: ProgressStep,
			result: ResultStep,
		};
		return new (map[this.state.step] || StartStep)(this);
	}

	render_stepper() {
		// Fix is a remedial detour off the Review step — keep the visible stepper on Review.
		const effective_step = this.state.step === "fix" ? "review" : this.state.step;
		const current = STEPS.findIndex((s) => s.key === effective_step);
		const html = STEPS.map((s, i) => {
			let cls = "pi-step";
			if (i === current) cls += " active";
			else if (i < current) cls += " completed";
			const inner = i < current ? "✓" : i + 1;
			return `
				<div class="${cls}">
					<div class="pi-step-circle">${inner}</div>
					<div class="pi-step-label">${s.label}</div>
				</div>
			`;
		}).join("");
		this.$stepper.html(`<div class="pi-stepper">${html}</div>`);
	}

	// ---- State management ----

	reset_state() {
		this.stop_progress_polling();
		this._reset_fields();
	}

	sync_route() {
		// Use pushState directly — frappe.set_route() triggers a navigation cycle
		// that resets breadcrumbs even when the page is already active.
		const route = frappe.get_route();
		const current = route.length > 1 ? route[1] : null;
		if (this.state.import_name && this.state.import_name !== current) {
			window.history.pushState(
				null,
				null,
				"/app/party-import-wizard/" + encodeURIComponent(this.state.import_name)
			);
		} else if (!this.state.import_name && current) {
			window.history.pushState(null, null, "/app/party-import-wizard");
		}
	}

	stop_progress_polling() {
		if (this.poll_timer) {
			clearInterval(this.poll_timer);
			this.poll_timer = null;
		}
		if (this._realtime_handlers) {
			frappe.realtime.off("party_import_progress", this._realtime_handlers.progress);
			frappe.realtime.off("party_import_complete", this._realtime_handlers.complete);
			this._realtime_handlers = null;
		}
	}

	// ---- Shared helpers ----

	async load_party_perms() {
		if (this.party_perms) return this.party_perms;
		const r = await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.get_party_type_permissions",
		});
		this.party_perms = r.message || { Customer: false, Supplier: false };
		return this.party_perms;
	}

	get_csrf_token() {
		if (typeof frappe !== "undefined" && frappe.csrf_token) return frappe.csrf_token;
		if (typeof frappe !== "undefined" && frappe.boot && frappe.boot.csrf_token) {
			return frappe.boot.csrf_token;
		}
		const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
		return m ? decodeURIComponent(m[1]) : "";
	}

	// ---- Resume ----

	async resume(import_name) {
		try {
			const doc = await frappe.db.get_doc("Party Import Log", import_name);
			this.state.import_name = doc.name;
			this.state.party_type = doc.party_type;
			this.state.source_format = doc.source_format || "Generic";
			this.state.file_url = doc.import_file;
			this.state.mappings = doc.column_mappings ? JSON.parse(doc.column_mappings) : {};
			this.state.resolutions = doc.dependency_resolutions ? JSON.parse(doc.dependency_resolutions) : {};
			this.sync_route();
			const step = this._step_for_status(doc.status);
			await this._preload_for_step(step);
			this.go(step);
		} catch (e) {
			frappe.msgprint(__("Could not load import: {0}", [e.message]));
		}
	}

	_step_for_status(status) {
		const map = {
			Draft: "upload",
			Mapping: "map",
			Resolving: "resolve",
			Reviewing: "review",
			Importing: "progress",
			Completed: "result",
			Failed: "result",
			Cancelled: "result",
		};
		return map[status] || "start";
	}

	async _preload_for_step(step) {
		const needs_file = ["map", "resolve", "review"].includes(step);
		const needs_deps = ["resolve", "review"].includes(step);
		if (needs_file) await this.load_file_data();
		if (needs_deps) await this.load_dependencies();
		if (step === "review") await this.load_summary();
		if (["progress", "result"].includes(step)) {
			await this.load_progress();
			if (step === "progress" && this.state.progress?.status === "Importing") {
				this.start_progress_polling();
			}
		}
	}

	// ---- Progress polling ----

	start_progress_polling() {
		this.stop_progress_polling();
		const on_progress = (data) => {
			if (data.import_name !== this.state.import_name) return;
			this.state.progress = { ...this.state.progress, ...data, status: "Importing" };
			if (this.state.step === "progress") this._current_step().render();
		};
		const on_complete = async (data) => {
			if (data.import_name !== this.state.import_name) return;
			this.stop_progress_polling();
			await this.load_progress();
			this.go("result");
		};
		frappe.realtime.on("party_import_progress", on_progress);
		frappe.realtime.on("party_import_complete", on_complete);
		this._realtime_handlers = { progress: on_progress, complete: on_complete };
		this.poll_timer = setInterval(async () => {
			await this.load_progress();
			if (this.state.progress?.status === "Completed") {
				this.stop_progress_polling();
				this.go("result");
			} else if (this.state.step === "progress") {
				this._current_step().render();
			}
		}, 5000);
	}

	// ---- Data loading ----

	async load_file_data() {
		const r = await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.parse_file",
			args: { import_name: this.state.import_name },
		});
		const m = r.message;
		this.state.columns = m.columns;
		this.state.sample_rows = m.sample_rows;
		this.state.target_fields = m.target_fields;
		this.state.parse_warnings = m.warnings || [];
	}

	async auto_map() {
		const r = await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.auto_map_columns",
			args: { import_name: this.state.import_name },
		});
		this.state.mappings = r.message || {};
	}

	async apply_mapping_template(name) {
		const r = await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.load_mapping_template",
			args: { name },
		});
		const loaded = r.message || {};
		this.state.columns.forEach((col) => {
			if (loaded[col]) this.state.mappings[col] = loaded[col];
		});
	}

	async load_dependencies() {
		const r = await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.analyze_dependencies",
			args: { import_name: this.state.import_name },
		});
		this.state.dependencies = r.message || {};
		if (!Object.keys(this.state.resolutions).length) {
			this._init_resolutions();
		}
	}

	_init_resolutions() {
		const out = {};
		for (const [master, payload] of Object.entries(this.state.dependencies)) {
			out[master] = {
				master,
				is_tree: payload.is_tree,
				creatable: payload.creatable,
				values: payload.values.map((v) => ({
					value: v.value,
					count: v.count,
					action: v.exists ? "use" : v.suggestion ? "map" : payload.creatable ? "create" : "skip",
					map_to: v.suggestion || null,
				})),
			};
		}
		this.state.resolutions = out;
	}

	async load_summary() {
		const r = await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.dry_run",
			args: { import_name: this.state.import_name },
		});
		this.state.summary = r.message;
	}

	async load_progress() {
		const r = await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.get_progress",
			args: { import_name: this.state.import_name },
		});
		this.state.progress = r.message;
	}
};

// ============================================================================
// Step 1 — Start
// ============================================================================

class StartStep {
	constructor(wizard) {
		this.wizard = wizard;
	}

	async render() {
		if (this._handle_prefill()) return;
		await this.wizard.load_party_perms();
		this._render_html();
		this._bind_events();
		this._load_drafts();
	}

	_handle_prefill() {
		const prefill = window.localStorage.getItem("party_import_prefill");
		if (!prefill || (prefill !== "Customer" && prefill !== "Supplier")) return false;
		window.localStorage.removeItem("party_import_prefill");
		this.wizard.state.party_type = prefill;
		this.wizard.go("upload");
		return true;
	}

	_render_html() {
		const perms = this.wizard.party_perms || {};
		this.wizard.$stage.html(`
			<div class="pi-card">
				<div class="pi-card-header">
					<h2 class="pi-card-title">${__("Import what?")}</h2>
					<p class="pi-card-subtitle">${__("Pick the type of party you're importing.")}</p>
				</div>
				<div class="pi-pick-grid">
					${this._card_html("Customer", "👥", __("Customers"), __("Companies or people you sell to."), perms)}
					${this._card_html("Supplier", "📦", __("Suppliers"), __("Vendors you buy goods or services from."), perms)}
				</div>
				<div class="pi-resume"></div>
			</div>
		`);
	}

	_card_html(type, icon, title, desc, perms) {
		const allowed = !!perms[type];
		const note = allowed
			? ""
			: `<div class="pi-pick-note">${__("Requires permission to create {0}", [type + "s"])}</div>`;
		return `
			<div class="pi-pick-card ${allowed ? "" : "disabled"}" data-type="${type}">
				<div class="pi-pick-icon">${icon}</div>
				<h3>${title}</h3>
				<p>${desc}</p>
				${note}
			</div>
		`;
	}

	_bind_events() {
		this.wizard.$stage.find(".pi-pick-card").on("click", (e) => {
			const $card = $(e.currentTarget);
			if ($card.hasClass("disabled")) return;
			this.wizard.reset_state();
			this.wizard.state.party_type = $card.data("type");
			window.history.pushState(null, null, "/app/party-import-wizard");
			this.wizard.go("upload");
		});
	}

	async _load_drafts() {
		const allowed = Object.keys(this.wizard.party_perms).filter((pt) => this.wizard.party_perms[pt]);
		if (!allowed.length) return;
		const drafts = await frappe.db.get_list("Party Import Log", {
			filters: {
				status: ["in", ["Draft", "Mapping", "Resolving", "Reviewing"]],
				party_type: ["in", allowed],
			},
			fields: ["name", "party_type", "status", "modified", "total_rows"],
			order_by: "modified desc",
			limit: 5,
		});
		if (!drafts.length) return;
		this._render_drafts(drafts);
	}

	_render_drafts(drafts) {
		const items = drafts
			.map(
				(d) => `
			<a class="pi-draft-item" href="/app/party-import-wizard/${frappe.utils.escape_html(
				d.name
			)}" data-name="${frappe.utils.escape_html(d.name)}">
				<div class="pi-draft-name">
					<div class="pi-draft-title">${frappe.utils.escape_html(d.name)}</div>
					<div class="pi-draft-meta">${frappe.utils.escape_html(d.party_type)} · ${d.total_rows || 0} ${__(
					"rows"
				)}</div>
				</div>
				<div class="pi-draft-status">${frappe.utils.escape_html(d.status)} · ${frappe.datetime.prettyDate(
					d.modified
				)}</div>
				<span class="pi-draft-arrow">→</span>
			</a>
		`
			)
			.join("");
		this.wizard.$stage.find(".pi-resume").html(`
			<h3 class="pi-section-heading">${__("Resume a draft")}</h3>
			<div class="pi-draft-list">${items}</div>
		`);
		this.wizard.$stage.find(".pi-draft-item").on("click", (e) => {
			e.preventDefault();
			const name = $(e.currentTarget).data("name");
			if (!name) return;
			this.wizard.resume(name);
		});
	}
}

// ============================================================================
// Step 2 — Upload
// ============================================================================

class UploadStep {
	constructor(wizard) {
		this.wizard = wizard;
	}

	render() {
		const { file_url, uploading_file_name, upload_error, party_type } = this.wizard.state;
		const has_file = !!file_url;
		const uploading = !!uploading_file_name;
		const zone = has_file
			? this._file_card_html()
			: uploading
			? this._uploading_card_html()
			: this._dropzone_html();
		const error = upload_error
			? `<div class="pi-banner pi-banner-error pi-mt-12">${__(
					"Upload failed"
			  )}: ${frappe.utils.escape_html(upload_error)}</div>`
			: "";
		const templates = !has_file && !uploading ? this._templates_html() : "";
		const source = !has_file && !uploading ? this._source_format_html() : "";

		this.wizard.$stage.html(`
			<div class="pi-card">
				<div class="pi-card-header">
					<h2 class="pi-card-title">${__("Upload your {0} file", [party_type.toLowerCase()])}</h2>
				</div>
				${source}${zone}${error}${templates}
				<div class="pi-actions">
					<button class="pi-btn pi-btn-ghost pi-back">← ${__("Back")}</button>
					<button class="pi-btn pi-btn-primary pi-continue" ${has_file ? "" : "disabled"}>${__("Continue →")}</button>
				</div>
			</div>
		`);
		this._bind_events();
		this._append_user_templates();
	}

	_source_format_html() {
		const current = this.wizard.state.source_format || "Generic";
		const options = [
			{ value: "Generic", label: __("Generic CSV / Excel") },
			{ value: "Tally", label: __("Tally (ledger export)") },
			{ value: "QuickBooks", label: __("QuickBooks (customer / vendor export)") },
			{ value: "Zoho", label: __("Zoho (Books / CRM contact export)") },
			{ value: "HubSpot", label: __("HubSpot (companies / contacts export)") },
			{ value: "Salesforce", label: __("Salesforce (account / contact export)") },
		]
			.map(
				(o) =>
					`<option value="${o.value}" ${current === o.value ? "selected" : ""}>${o.label}</option>`
			)
			.join("");
		return `
			<div class="pi-source-format">
				<label for="pi-source-select">${__("Source system")}</label>
				<select id="pi-source-select" class="pi-source-select">${options}</select>
				<p class="pi-source-hint">${__("Pre-fills column mapping for files exported from a known system.")}</p>
			</div>
		`;
	}

	_dropzone_html() {
		return `
			<div class="pi-dropzone" tabindex="0">
				<div class="pi-dropzone-icon">⬆</div>
				<p><strong>${__("Drop a CSV or Excel file here")}</strong></p>
				<p>${__("or")} <span class="pi-browse-link">${__("browse files")}</span></p>
				<p class="pi-dropzone-hint">${__("Up to 10 MB · 10,000 rows")}</p>
				<input type="file" accept=".csv,.xlsx,.xls" style="display:none" />
			</div>
		`;
	}

	_uploading_card_html() {
		const { uploading_file_name, uploading_file_size } = this.wizard.state;
		const size = this._format_size(uploading_file_size);
		return `
			<div class="pi-file-card pi-file-card-uploading">
				<div class="pi-file-icon"><span class="pi-loading"></span></div>
				<div class="pi-file-info">
					<div class="pi-file-name">${frappe.utils.escape_html(uploading_file_name)}</div>
					<div class="pi-file-meta">${__("Uploading…")}${size ? " · " + size : ""}</div>
				</div>
			</div>
		`;
	}

	_file_card_html() {
		const { file_name, file_url, file_size } = this.wizard.state;
		const name = file_name || (file_url || "").split("/").pop();
		const size = this._format_size(file_size);
		return `
			<div class="pi-file-card">
				<div class="pi-file-icon">📄</div>
				<div class="pi-file-info">
					<div class="pi-file-name">${frappe.utils.escape_html(name)}</div>
					<div class="pi-file-meta">${size || __("Ready to import")}</div>
				</div>
				<button class="pi-file-remove" type="button" title="${__("Remove file")}" aria-label="${__(
			"Remove file"
		)}">×</button>
			</div>
		`;
	}

	_templates_html() {
		return `
			<p class="pi-template-help">
				${__("Don't have a file? Download a")}
				<a class="pi-link" data-template="sample">${__("sample template")}</a>
				${__("or an")}
				<a class="pi-link" data-template="empty">${__("empty template")}</a>.
			</p>
		`;
	}

	_format_size(bytes) {
		if (!bytes) return "";
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	_bind_events() {
		this._bind_source_format();
		this._bind_dropzone();
		this._bind_file_card();
		this._bind_templates();
		this._bind_navigation();
	}

	_bind_source_format() {
		this.wizard.$stage.find(".pi-source-select").on("change", (e) => {
			const val = e.target.value;
			if (val.startsWith("__template__::")) {
				this.wizard.state.mapping_template_name = val.slice("__template__::".length);
				this.wizard.state.source_format = "Generic";
			} else {
				this.wizard.state.source_format = val;
				this.wizard.state.mapping_template_name = null;
			}
		});
	}

	async _append_user_templates() {
		const r = await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.list_mapping_templates",
			args: { party_type: this.wizard.state.party_type },
		});
		const templates = r.message || [];
		const $select = this.wizard.$stage.find(".pi-source-select");
		if (!$select.length || !templates.length) return;
		const opts = templates
			.map(
				(t) =>
					`<option value="__template__::${frappe.utils.escape_html(
						t.name
					)}">${frappe.utils.escape_html(t.template_name)}</option>`
			)
			.join("");
		$select.append(`<optgroup label="${__("My Templates")}">${opts}</optgroup>`);
		if (this.wizard.state.mapping_template_name) {
			$select.val(`__template__::${this.wizard.state.mapping_template_name}`);
		}
	}

	_bind_dropzone() {
		const $dz = this.wizard.$stage.find(".pi-dropzone");
		if (!$dz.length) return;
		const $input = $dz.find('input[type="file"]');
		$dz.on("click", (e) => {
			if (e.target !== $input[0]) $input[0].click();
		});
		$dz.on("keydown", (e) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				$input[0].click();
			}
		});
		$dz.on("dragover", (e) => {
			e.preventDefault();
			$dz.addClass("dragover");
		});
		$dz.on("dragleave drop", () => $dz.removeClass("dragover"));
		$dz.on("drop", (e) => {
			e.preventDefault();
			const f = e.originalEvent.dataTransfer.files[0];
			if (f) this._upload_file(f);
		});
		$input.on("change", (e) => {
			const f = e.target.files[0];
			if (f) this._upload_file(f);
		});
	}

	_bind_file_card() {
		this.wizard.$stage.find(".pi-file-remove").on("click", () => {
			const s = this.wizard.state;
			s.file_url = null;
			s.file_name = null;
			s.file_size = null;
			s.import_name = null;
			s.upload_error = null;
			this.render();
		});
	}

	_bind_templates() {
		this.wizard.$stage.find("[data-template]").on("click", (e) => {
			const which = $(e.currentTarget).data("template");
			const params = new URLSearchParams({
				party_type: this.wizard.state.party_type,
				with_sample: which === "sample" ? "1" : "0",
				source_format: this.wizard.state.source_format || "Generic",
			});
			window.open(
				`/api/method/erpnext.selling.doctype.party_import_log.party_import_log.download_template?${params}`,
				"_blank"
			);
		});
	}

	_bind_navigation() {
		this.wizard.$stage.find(".pi-back").on("click", () => this.wizard.go("start"));
		this.wizard.$stage.find(".pi-continue").on("click", () => this._on_continue());
	}

	async _on_continue() {
		if (!this.wizard.state.file_url) return;
		try {
			if (!this.wizard.state.import_name) {
				const r = await frappe.call({
					method: "erpnext.selling.doctype.party_import_log.party_import_log.create_from_file",
					args: {
						file_url: this.wizard.state.file_url,
						party_type: this.wizard.state.party_type,
						source_format: this.wizard.state.source_format || "Generic",
					},
				});
				this.wizard.state.import_name = r.message;
				this.wizard.sync_route();
			}
			await this.wizard.load_file_data();
			await this.wizard.auto_map();
			if (this.wizard.state.mapping_template_name) {
				await this.wizard.apply_mapping_template(this.wizard.state.mapping_template_name);
			}
			this.wizard.go("map");
		} catch (e) {
			const msg = (e && e.message) || (e && e._server_messages) || __("Failed to parse file");
			this.wizard.state.upload_error = typeof msg === "string" ? msg : __("Failed to parse file");
			this.render();
		}
	}

	async _upload_file(file) {
		const MAX_BYTES = 10 * 1024 * 1024;
		if (file.size > MAX_BYTES) {
			this.wizard.state.upload_error = __("File is too large ({0}). Maximum is 10 MB.", [
				this._format_size(file.size),
			]);
			this.render();
			return;
		}
		const allowed_exts = [".csv", ".xlsx", ".xls"];
		if (!allowed_exts.some((ext) => file.name.toLowerCase().endsWith(ext))) {
			this.wizard.state.upload_error = __(
				"Unsupported file type. Use CSV or Excel (.csv, .xlsx, .xls)."
			);
			this.render();
			return;
		}

		this.wizard.state.uploading_file_name = file.name;
		this.wizard.state.uploading_file_size = file.size;
		this.wizard.state.upload_error = null;
		this.render();

		const form = new FormData();
		form.append("file", file, file.name);
		form.append("is_private", 1);
		form.append("folder", "Home/Attachments");
		const token = this.wizard.get_csrf_token();
		const headers = token ? { "X-Frappe-CSRF-Token": token } : {};

		try {
			const r = await fetch("/api/method/upload_file", { method: "POST", headers, body: form });
			if (!r.ok) throw new Error(await r.text());
			const data = await r.json();
			this.wizard.state.file_url = data.message.file_url;
			this.wizard.state.file_name = file.name;
			this.wizard.state.file_size = file.size;
			this.wizard.state.uploading_file_name = null;
			this.wizard.state.uploading_file_size = null;
		} catch (e) {
			this.wizard.state.uploading_file_name = null;
			this.wizard.state.uploading_file_size = null;
			this.wizard.state.upload_error = e.message || String(e);
		}
		this.render();
	}
}

// ============================================================================
// Step 3 — Map
// ============================================================================

class MapStep {
	constructor(wizard) {
		this.wizard = wizard;
	}

	render() {
		const { columns, mappings, target_fields, sample_rows, parse_warnings, party_type } =
			this.wizard.state;
		const matched = Object.values(mappings).filter(Boolean).length;
		const name_field = party_type === "Customer" ? "customer_name" : "supplier_name";
		const warnings_html = (parse_warnings || [])
			.map((w) => `<div class="pi-banner pi-banner-warning">${w}</div>`)
			.join("");

		this.wizard.$stage.html(`
			<div class="pi-card">
				<div class="pi-card-header">
					<h2 class="pi-card-title">${__("Map your columns")}</h2>
					<p class="pi-card-subtitle">${columns.length} ${__("columns")} · ${matched} ${__("auto-matched")}</p>
				</div>
				${warnings_html}
				<div class="pi-required-banner pi-banner pi-banner-warning" style="display:none">
					${__("Required field missing: {0}", ['<span class="pi-required-name"></span>'])}
				</div>
				<table class="pi-map-table">
					<thead><tr><th>${__("Your column")}</th><th>${__("Maps to")}</th></tr></thead>
					<tbody>${this._rows_html(columns, mappings, target_fields, sample_rows)}</tbody>
				</table>
				<div class="pi-actions">
					<button class="pi-btn pi-btn-ghost pi-back">← ${__("Back")}</button>
					<div class="pi-actions-right">
						<button class="pi-btn pi-btn-secondary pi-save-template">${__("Save as template")}</button>
						<button class="pi-btn pi-btn-primary pi-continue">${__("Continue →")}</button>
					</div>
				</div>
			</div>
		`);
		this._apply_mappings();
		this._bind_events(name_field);
	}

	async _save_template() {
		frappe.prompt(
			{ fieldname: "template_name", fieldtype: "Data", label: __("Template Name"), reqd: 1 },
			async ({ template_name }) => {
				await frappe.call({
					method: "erpnext.selling.doctype.party_import_log.party_import_log.save_mapping_template",
					args: {
						template_name,
						party_type: this.wizard.state.party_type,
						mappings: JSON.stringify(this.wizard.state.mappings),
					},
				});
				frappe.show_alert({
					message: __('Template "{0}" saved', [template_name]),
					indicator: "green",
				});
			},
			__("Save Mapping Template"),
			__("Save")
		);
	}

	_options_html(target_fields) {
		const grouped = {};
		target_fields.forEach(([field, label, group, required]) => {
			grouped[group] = grouped[group] || [];
			grouped[group].push({ field, label, required });
		});
		return Object.entries(grouped)
			.map(
				([g, fields]) => `
			<optgroup label="${frappe.utils.escape_html(g)}">
				${fields
					.map(
						(f) =>
							`<option value="${frappe.utils.escape_html(f.field)}">${frappe.utils.escape_html(
								f.label
							)}${f.required ? " *" : ""}</option>`
					)
					.join("")}
			</optgroup>
		`
			)
			.join("");
	}

	_rows_html(columns, mappings, target_fields, sample_rows) {
		const options = this._options_html(target_fields);
		return columns
			.map((col) => {
				const sample = sample_rows
					.map((r) => r[col])
					.filter((v) => v != null && v !== "")
					.slice(0, 3)
					.map((v) => frappe.utils.escape_html(String(v).substring(0, 40)))
					.join(" · ");
				const mapped = mappings[col] || "";
				return `
				<tr>
					<td>
						<div class="pi-map-source">${frappe.utils.escape_html(col)}</div>
						<div class="pi-map-sample">${sample || __("(empty)")}</div>
					</td>
					<td class="pi-map-col-target">
						<select class="pi-map-select${mapped ? "" : " pi-map-skip"}" data-source="${frappe.utils.escape_html(col)}">
							<option value="">${__("Skip this column")}</option>
							${options}
						</select>
					</td>
				</tr>
			`;
			})
			.join("");
	}

	_apply_mappings() {
		this.wizard.$stage.find(".pi-map-select").each((_, el) => {
			const src = $(el).data("source");
			if (this.wizard.state.mappings[src]) $(el).val(this.wizard.state.mappings[src]);
		});
	}

	_bind_events(name_field) {
		this.wizard.$stage.find(".pi-map-select").on("change", (e) => {
			const $el = $(e.currentTarget);
			this.wizard.state.mappings[$el.data("source")] = $el.val();
			$el.toggleClass("pi-map-skip", !$el.val());
		});
		this.wizard.$stage.find(".pi-save-template").on("click", () => this._save_template());
		this.wizard.$stage.find(".pi-back").on("click", () => this.wizard.go("upload"));
		this.wizard.$stage.find(".pi-continue").on("click", () => this._on_continue(name_field));
	}

	async _on_continue(name_field) {
		const mapped_targets = Object.values(this.wizard.state.mappings).filter(Boolean);
		if (!mapped_targets.includes(name_field)) {
			const $b = this.wizard.$stage.find(".pi-required-banner");
			$b.find(".pi-required-name").text(name_field);
			$b.show();
			return;
		}
		await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.set_column_mappings",
			args: {
				import_name: this.wizard.state.import_name,
				mappings: JSON.stringify(this.wizard.state.mappings),
			},
		});
		await this.wizard.load_dependencies();
		this.wizard.go("resolve");
	}
}

// ============================================================================
// Step 4 — Resolve dependencies
// ============================================================================

class ResolveStep {
	constructor(wizard) {
		this.wizard = wizard;
	}

	render() {
		const groups = Object.entries(this.wizard.state.dependencies);
		if (!groups.length) {
			this._skip_to_review();
			return;
		}
		const sections = groups.map(([master, payload]) => this._dep_group_html(master, payload)).join("");
		this.wizard.$stage.html(`
			<div class="pi-card">
				<div class="pi-card-header">
					<h2 class="pi-card-title">${__("Resolve referenced data")}</h2>
					<p class="pi-card-subtitle">${__("Your file references master records. Decide what to do with each.")}</p>
				</div>
				${sections}
				<div class="pi-actions">
					<button class="pi-btn pi-btn-ghost pi-back">← ${__("Back")}</button>
					<button class="pi-btn pi-btn-primary pi-continue">${__("Continue →")}</button>
				</div>
			</div>
		`);
		this._bind_events();
	}

	_skip_to_review() {
		this.wizard.$stage.html(`
			<div class="pi-card"><div class="pi-empty"><p>${__(
				"No dependent master records detected. Continuing…"
			)}</p></div></div>
		`);
		setTimeout(async () => {
			await frappe.call({
				method: "erpnext.selling.doctype.party_import_log.party_import_log.set_dependency_resolutions",
				args: {
					import_name: this.wizard.state.import_name,
					resolutions: JSON.stringify(this.wizard.state.resolutions),
				},
			});
			await this.wizard.load_summary();
			this.wizard.go("review");
		}, 600);
	}

	_dep_group_html(master, payload) {
		const resolution = this.wizard.state.resolutions[master] || { values: [] };
		const file_values = (this.wizard.state.dependencies[master] || { values: [] }).values;
		const all_rows = resolution.values.map((v, i) => ({ ...v, _idx: i }));
		const needs_action = all_rows.filter((v) => !file_values.find((x) => x.value === v.value)?.exists);
		const resolved_rows = all_rows.filter((v) => !!file_values.find((x) => x.value === v.value)?.exists);

		if (!this.wizard.state.dep_expanded) this.wizard.state.dep_expanded = {};
		if (this.wizard.state.dep_expanded[master] === undefined) {
			this.wizard.state.dep_expanded[master] = needs_action.length > 0;
		}
		const is_expanded = this.wizard.state.dep_expanded[master];

		let body_html = "";
		if (is_expanded) {
			const unresolved = needs_action
				.map((v) => this._action_row_html(master, v, v._idx, payload))
				.join("");
			const resolved = resolved_rows.map((v) => this._resolved_row_html(v)).join("");
			body_html = `<div class="pi-dep-body">${unresolved}${resolved}</div>`;
		}
		return `
			<div class="pi-dep-group" data-master="${frappe.utils.escape_html(master)}">
				<div class="pi-dep-header" data-master="${frappe.utils.escape_html(master)}">
					<h3><span class="pi-dep-chevron">${is_expanded ? "▾" : "▸"}</span> ${frappe.utils.escape_html(master)}</h3>
					<span class="pi-dep-status ${needs_action.length > 0 ? "unresolved" : ""}">${this._status_text(
			needs_action.length,
			resolved_rows.length
		)}</span>
				</div>
				${body_html}
			</div>
		`;
	}

	_status_text(need, resolved) {
		if (need === 0) return __("{0} resolved", [resolved]);
		if (resolved > 0) return __("{0} need action · {1} resolved", [need, resolved]);
		return __("{0} need action", [need]);
	}

	_resolved_row_html(v) {
		return `
			<div class="pi-dep-row pi-dep-row-resolved">
				<div>
					<div class="pi-dep-value">${frappe.utils.escape_html(v.value)}</div>
					<div class="pi-dep-count">${v.count} ${__("rows")}</div>
				</div>
				<div class="pi-dep-resolved-tag"><span class="pi-dep-check">✓</span> ${__("Already exists")}</div>
			</div>
		`;
	}

	_action_row_html(master, v, idx, payload) {
		const file_entry =
			this.wizard.state.dependencies[master].values.find((x) => x.value === v.value) || {};
		const actions = [
			{ key: "use", label: __("Use existing"), enabled: file_entry.exists },
			{ key: "map", label: __("Map to existing"), enabled: true },
			{ key: "create", label: __("Create new"), enabled: payload.creatable },
			{ key: "skip", label: __("Skip these rows"), enabled: true },
		];
		const opts = actions
			.filter((a) => a.enabled)
			.map(
				(a) => `<option value="${a.key}" ${v.action === a.key ? "selected" : ""}>${a.label}</option>`
			)
			.join("");

		const map_input =
			v.action === "map"
				? `<input type="text" class="pi-dep-input pi-map-target" data-master="${frappe.utils.escape_html(
						master
				  )}" data-idx="${idx}" value="${frappe.utils.escape_html(v.map_to || "")}" placeholder="${__(
						"Existing record name"
				  )}" />`
				: v.action === "create"
				? `<div class="pi-dep-hint">${
						payload.is_tree ? __("Will create (tree-aware)") : __("Will be created")
				  }</div>`
				: "";

		const hint =
			file_entry.suggestion && v.action !== "map"
				? `<div class="pi-dep-hint">${__("Looks similar to")} <strong>${frappe.utils.escape_html(
						file_entry.suggestion
				  )}</strong></div>`
				: !payload.creatable
				? `<div class="pi-dep-hint pi-dep-hint-warning">${__(
						"Cannot be created — pick an existing record or skip"
				  )}</div>`
				: "";

		return `
			<div class="pi-dep-row">
				<div>
					<div class="pi-dep-value">${frappe.utils.escape_html(v.value)}</div>
					<div class="pi-dep-count">${v.count} ${__("rows")}</div>
				</div>
				<div>
					<select class="pi-dep-input pi-dep-action" data-master="${frappe.utils.escape_html(
						master
					)}" data-idx="${idx}">${opts}</select>
				</div>
				<div>${map_input}${hint}</div>
			</div>
		`;
	}

	_bind_events() {
		this.wizard.$stage.find(".pi-dep-header").on("click", (e) => {
			const master = $(e.currentTarget).data("master");
			if (!master) return;
			this.wizard.state.dep_expanded[master] = !this.wizard.state.dep_expanded[master];
			this.render();
		});
		this.wizard.$stage.find(".pi-dep-action").on("change", (e) => {
			const $el = $(e.currentTarget);
			const master = $el.data("master");
			const idx = parseInt($el.data("idx"));
			this.wizard.state.resolutions[master].values[idx].action = $el.val();
			if ($el.val() === "map" && !this.wizard.state.resolutions[master].values[idx].map_to) {
				const val = this.wizard.state.resolutions[master].values[idx].value;
				const fileEntry = this.wizard.state.dependencies[master].values.find((x) => x.value === val);
				if (fileEntry?.suggestion)
					this.wizard.state.resolutions[master].values[idx].map_to = fileEntry.suggestion;
			}
			this.render();
		});
		this.wizard.$stage.find(".pi-map-target").on("input", (e) => {
			const $el = $(e.currentTarget);
			this.wizard.state.resolutions[$el.data("master")].values[parseInt($el.data("idx"))].map_to =
				$el.val();
		});
		this.wizard.$stage.find(".pi-back").on("click", () => this.wizard.go("map"));
		this.wizard.$stage.find(".pi-continue").on("click", () => this._on_continue());
	}

	async _on_continue() {
		for (const [master, payload] of Object.entries(this.wizard.state.resolutions)) {
			for (const v of payload.values) {
				if (v.action === "map" && !v.map_to) {
					frappe.show_alert({
						message: __("Pick a target for {0} → {1}", [master, v.value]),
						indicator: "orange",
					});
					return;
				}
			}
		}
		await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.set_dependency_resolutions",
			args: {
				import_name: this.wizard.state.import_name,
				resolutions: JSON.stringify(this.wizard.state.resolutions),
			},
		});
		await this.wizard.load_summary();
		this.wizard.go("review");
	}
}

// ============================================================================
// Step 5 — Review
// ============================================================================

class ReviewStep {
	constructor(wizard) {
		this.wizard = wizard;
	}

	render() {
		const s = this.wizard.state.summary || {};
		const party_type = this.wizard.state.party_type;
		this.wizard.$stage.html(`
			<div class="pi-card">
				<div class="pi-card-header">
					<h2 class="pi-card-title">${__("Review before import")}</h2>
				</div>
				${this._summary_html(s, party_type)}
				${this._conflict_html(party_type)}
				${this._errors_html(s)}
				<div class="pi-banner pi-banner-info pi-mt-16">
					${__(
						"Once you continue, master records will be created and the import will run in the background. Master record creation cannot be automatically undone."
					)}
				</div>
				<div class="pi-actions">
					<button class="pi-btn pi-btn-ghost pi-back">← ${__("Back")}</button>
					<button class="pi-btn pi-btn-primary pi-continue">✓ ${__("Start Import")} (${
			(s.to_create || 0) + (s.to_update || 0)
		})</button>
				</div>
			</div>
		`);
		this._bind_events();
	}

	_summary_html(s, party_type) {
		const side_effects = Object.entries(s.masters_to_create || {})
			.map(
				([dt, vals]) =>
					`<li>${vals.length} ${frappe.utils.escape_html(dt)}: ${vals
						.slice(0, 3)
						.map(frappe.utils.escape_html)
						.join(", ")}${vals.length > 3 ? "…" : ""}</li>`
			)
			.join("");
		return `
			<div class="pi-summary">
				<div class="pi-summary-row"><span>${__("Rows in file")}</span><span class="pi-num">${
			s.total_rows || 0
		}</span></div>
				<div class="pi-summary-row"><span>${__("New {0}", [party_type + "s"])}</span><span class="pi-num">${
			s.to_create || 0
		}</span></div>
				<div class="pi-summary-row"><span>${__("Existing {0}", [party_type + "s"])}</span><span class="pi-num">${
			s.to_update || 0
		}</span></div>
				<div class="pi-summary-row"><span>${__("Skipped")}</span><span class="pi-num">${s.to_skip || 0}</span></div>
				${
					s.error_count
						? `<div class="pi-summary-row"><span>${__(
								"With errors"
						  )}</span><span class="pi-num">${s.error_count}</span></div>`
						: ""
				}
				${
					side_effects
						? `<div class="pi-side-effects"><strong>${__(
								"Also will be created:"
						  )}</strong><ul>${side_effects}</ul></div>`
						: ""
				}
			</div>
		`;
	}

	_conflict_html(party_type) {
		const party = (party_type || "Customer").toLowerCase();
		const options = [
			{ value: "Skip", title: __("Skip the row") },
			{ value: "Update Empty Fields Only", title: __("Update only empty fields") },
			{ value: "Update All Fields", title: __("Overwrite all fields") },
		];
		const items = options
			.map(
				(opt) => `
			<label class="pi-conflict-option">
				<input type="radio" name="pi-conflict" value="${opt.value}" ${opt.value === "Skip" ? "checked" : ""}>
				<span class="pi-conflict-option-title">${opt.title}</span>
			</label>
		`
			)
			.join("");
		return `
			<div class="pi-conflict-card">
				<h3 class="pi-conflict-title">${__("If a {0} already exists", [party])}</h3>
				<p class="pi-conflict-hint">${__(
					"We match rows by name. Pick what to do when a {0} with the same name is already in your system.",
					[party]
				)}</p>
				<div class="pi-conflict-options">${items}</div>
			</div>
		`;
	}

	_errors_html(s) {
		if (!s.error_count) return "";
		const items = (s.errors || [])
			.slice(0, 8)
			.map((e) => `<li>${__("Row {0}", [e.row])}: ${frappe.utils.escape_html(e.message)}</li>`)
			.join("");
		const cap = s.inline_edit_limit || 50;
		const cta = s.editable
			? `<button class="pi-btn pi-btn-secondary pi-fix-errors pi-mt-12">${__("Fix errors")} (${
					s.error_count
			  }) →</button>`
			: `<p class="pi-mt-12">${__(
					"Too many errors to fix in the wizard ({0}+). Fix them in your source file and re-upload.",
					[cap]
			  )}</p>`;
		return `
			<div class="pi-banner pi-banner-warning pi-mt-16">
				<strong>${s.error_count} ${__("rows with errors")}</strong>
				<ul class="pi-error-list">${items}</ul>
				${cta}
			</div>
		`;
	}

	_bind_events() {
		this.wizard.$stage.find(".pi-back").on("click", () => this.wizard.go("resolve"));
		this.wizard.$stage.find(".pi-continue").on("click", () => this._on_continue());
		this.wizard.$stage.find(".pi-fix-errors").on("click", () => this.wizard.go("fix"));
	}

	async _on_continue() {
		const policy = this.wizard.$stage.find("input[name='pi-conflict']:checked").val();
		await frappe.db.set_value(
			"Party Import Log",
			this.wizard.state.import_name,
			"conflict_policy",
			policy
		);
		await frappe.call({
			method: "erpnext.selling.doctype.party_import_log.party_import_log.start_import",
			args: { import_name: this.wizard.state.import_name },
		});
		this.wizard.start_progress_polling();
		this.wizard.go("progress");
	}
}

// ============================================================================
// Step 5b — Fix errors (remedial detour off Review; not in the stepper)
// ============================================================================

class FixStep {
	constructor(wizard) {
		this.wizard = wizard;
		this._has_saved = false;
	}

	render() {
		const s = this.wizard.state.summary || {};
		const target_fields = this.wizard.state.target_fields || [];
		const labels = Object.fromEntries(target_fields.map((f) => [f[0], f[1]]));
		const errors = s.errors || [];
		const has_errors = errors.length > 0;
		const body = has_errors
			? `<div class="pi-errors-list">${errors
					.map((e, i) => this._row_html(e, i, target_fields, labels))
					.join("")}</div>`
			: `<div class="pi-empty pi-empty--success">
				<div class="pi-empty-icon">✓</div>
				<p>${__("All errors fixed. Ready to re-check.")}</p>
			</div>`;
		const subtitle = has_errors
			? __("Edit the value(s) on each row, then save.")
			: __("Re-check will re-validate your data from the Resolve step.");
		this.wizard.$stage.html(`
			<div class="pi-card">
				<div class="pi-card-header">
					<h2 class="pi-card-title">${__("Fix errors")}</h2>
					<p class="pi-card-subtitle">${subtitle}</p>
				</div>
				${body}
				<div class="pi-actions">
					<button class="pi-btn pi-btn-ghost pi-back">← ${__("Back to Review")}</button>
					${
						!has_errors || this._has_saved
							? `<button class="pi-btn pi-btn-primary pi-done">${__("Re-check")} →</button>`
							: ""
					}
				</div>
			</div>
		`);
		this._bind_events();
	}

	_row_html(err, idx, target_fields, labels) {
		const message = frappe.utils.escape_html(err.message || "");
		const inputs = target_fields
			.filter((f) => Object.prototype.hasOwnProperty.call(err.values || {}, f[0]))
			.map((f) => this._field_html(err, f, labels))
			.join("");
		return `
			<div class="pi-error-row" data-row="${err.row}" data-idx="${idx}">
				<div class="pi-error-row-head">
					<div class="pi-error-row-meta">
						<span class="pi-error-row-num">${__("Row {0}", [err.row])}</span>
						<span class="pi-error-row-msg">${message}</span>
					</div>
					<button class="pi-error-row-toggle" type="button">${__("Edit")}</button>
				</div>
				<div class="pi-error-row-body" hidden>
					<div class="pi-error-fields">${inputs}</div>
					<div class="pi-error-row-actions">
						<button class="pi-btn pi-btn-ghost pi-error-cancel" type="button">${__("Cancel")}</button>
						<button class="pi-btn pi-btn-primary pi-error-save" type="button">${__("Save")}</button>
					</div>
				</div>
			</div>
		`;
	}

	_field_html(err, field, labels) {
		const [fieldname] = field;
		const label = labels[fieldname] || fieldname;
		const value = err.values[fieldname];
		const safe = value == null ? "" : String(value);
		return `
			<label class="pi-error-field">
				<span class="pi-error-field-label">${frappe.utils.escape_html(label)}</span>
				<input type="text" class="pi-error-field-input" data-target="${fieldname}" value="${frappe.utils.escape_html(
			safe
		)}" />
			</label>
		`;
	}

	_bind_events() {
		this.wizard.$stage.find(".pi-back").on("click", () => this.wizard.go("review"));
		this.wizard.$stage.find(".pi-done").on("click", () => this._on_done());
		this.wizard.$stage.find(".pi-error-row-toggle").on("click", (e) => {
			const $row = $(e.currentTarget).closest(".pi-error-row");
			const $body = $row.find(".pi-error-row-body");
			const open = !$body.is("[hidden]");
			$body.attr("hidden", open ? "" : null);
			$(e.currentTarget).text(open ? __("Edit") : __("Close"));
		});
		this.wizard.$stage.find(".pi-error-cancel").on("click", (e) => {
			const $row = $(e.currentTarget).closest(".pi-error-row");
			$row.find(".pi-error-row-body").attr("hidden", "");
			$row.find(".pi-error-row-toggle").text(__("Edit"));
		});
		this.wizard.$stage
			.find(".pi-error-save")
			.on("click", (e) => this._save_row($(e.currentTarget).closest(".pi-error-row")));
	}

	async _save_row($row) {
		const row_number = parseInt($row.data("row"), 10);
		const idx = parseInt($row.data("idx"), 10);
		const overrides = {};
		$row.find(".pi-error-field-input").each((_, input) => {
			overrides[$(input).data("target")] = $(input).val();
		});
		try {
			const r = await frappe.call({
				method: "erpnext.selling.doctype.party_import_log.party_import_log.save_row_override",
				args: {
					import_name: this.wizard.state.import_name,
					row: row_number,
					overrides: JSON.stringify(overrides),
				},
			});
			this._apply_save(idx, r.message || {});
		} catch (e) {
			frappe.msgprint({
				message: __("Could not save: {0}", [(e && e.message) || e]),
				indicator: "red",
			});
		}
	}

	_apply_save(idx, result) {
		const s = this.wizard.state.summary;
		if (result.action === "error") {
			s.errors[idx] = { row: result.row, message: result.message, values: result.values };
		} else {
			s.errors.splice(idx, 1);
			s.error_count = Math.max(0, (s.error_count || 0) - 1);
		}
		this._has_saved = true;
		this.render();
	}

	async _on_done() {
		// User asked: after editing, go back to Resolve and let dry_run re-run from there.
		// Resolve's continue path already calls load_summary → review, which picks up overrides.
		this.wizard.go("resolve");
	}
}

// ============================================================================
// Step 6 — Progress
// ============================================================================

class ProgressStep {
	constructor(wizard) {
		this.wizard = wizard;
	}

	render() {
		const p = this.wizard.state.progress || {
			imported: 0,
			total: this.wizard.state.summary?.total_rows || 0,
			created: 0,
			updated: 0,
			skipped: 0,
			errors: 0,
			status: "Importing",
		};
		const pct = p.total ? Math.round((p.imported / p.total) * 100) : 0;
		const stats = ["created", "updated", "skipped", "errors"]
			.map(
				(k) => `
			<div class="pi-progress-stat">
				<div class="pi-progress-stat-num">${p[k] || 0}</div>
				<div class="pi-progress-stat-label">${__(k.charAt(0).toUpperCase() + k.slice(1))}</div>
			</div>
		`
			)
			.join("");
		this.wizard.$stage.html(`
			<div class="pi-card pi-progress-card">
				<h2 class="pi-card-title">${p.status === "Completed" ? "✓ " + __("Import complete") : __("Importing…")}</h2>
				<p class="pi-card-subtitle">${frappe.utils.escape_html(this.wizard.state.import_name || "")}</p>
				<div class="pi-progress-bar"><div class="pi-progress-fill" style="width:${pct}%"></div></div>
				<p>${p.imported} / ${p.total} ${__("rows")} (${pct}%)</p>
				<div class="pi-progress-meta">${stats}</div>
				<div class="pi-banner pi-banner-info pi-mt-24">
					${__("You can leave this page — the import will continue in the background.")}
				</div>
			</div>
		`);
	}
}

// ============================================================================
// Step 7 — Result
// ============================================================================

class ResultStep {
	constructor(wizard) {
		this.wizard = wizard;
	}

	render() {
		this.wizard.stop_progress_polling();
		const p = this.wizard.state.progress || {};
		const party_type = this.wizard.state.party_type;
		this.wizard.$stage.html(`
			<div class="pi-card">
				<div class="pi-card-header">
					<h2 class="pi-card-title">${__("Import complete")}</h2>
					<p class="pi-card-subtitle">${frappe.utils.escape_html(this.wizard.state.import_name || "")}</p>
				</div>
				<div class="pi-summary">
					<div class="pi-summary-row"><span>${__("{0} created", [party_type + "s"])}</span><span class="pi-num">${
			p.created || 0
		}</span></div>
					<div class="pi-summary-row"><span>${__("{0} updated", [party_type + "s"])}</span><span class="pi-num">${
			p.updated || 0
		}</span></div>
					<div class="pi-summary-row"><span>${__("Rows skipped")}</span><span class="pi-num">${
			p.skipped || 0
		}</span></div>
					${
						p.errors
							? `<div class="pi-summary-row"><span>${__(
									"Rows failed"
							  )}</span><span class="pi-num">${p.errors}</span></div>`
							: ""
					}
				</div>
				${this._recent_errors_html(p)}
				<h3 class="pi-subheading">${__("What next?")}</h3>
				<div class="pi-actions">
					<div class="pi-actions-right">
						<button class="pi-btn pi-btn-ghost pi-open-record">${__("Open import record")}</button>
						<button class="pi-btn pi-btn-ghost pi-new-import">${__("Run another import")}</button>
						<button class="pi-btn pi-btn-primary pi-go-list">${__("Open {0} list", [party_type])} →</button>
					</div>
				</div>
			</div>
		`);
		this._bind_events();
	}

	_recent_errors_html(p) {
		if (!p.recent_errors?.length) return "";
		const items = p.recent_errors
			.map(
				(e) =>
					`<li>${e.row ? __("Row {0}: ", [e.row]) : ""}${frappe.utils.escape_html(e.message)}</li>`
			)
			.join("");
		return `
			<div class="pi-banner pi-banner-warning">
				<strong>${__("Recent errors")}</strong>
				<ul class="pi-error-list">${items}</ul>
			</div>
		`;
	}

	_bind_events() {
		this.wizard.$stage
			.find(".pi-go-list")
			.on("click", () => frappe.set_route("List", this.wizard.state.party_type));
		this.wizard.$stage.find(".pi-new-import").on("click", () => {
			this.wizard.reset_state();
			window.history.pushState(null, null, "/app/party-import-wizard");
			this.wizard.go("start");
		});
		this.wizard.$stage.find(".pi-open-record").on("click", () => {
			frappe.set_route("Form", "Party Import Log", this.wizard.state.import_name);
		});
	}
}
