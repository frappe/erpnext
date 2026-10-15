frappe.provide("erpnext");

erpnext.PartyOverview = class PartyOverview {
	static PERIODS = ["Current Fiscal Year", "Last 12 Months", "This Quarter", "Last Fiscal Year"];
	static RECENT_LIMIT = 10;
	static STATUS_THEME = {
		Paid: "green",
		Completed: "green",
		Submitted: "blue",
		"To Bill": "blue",
		Unpaid: "orange",
		"Partly Paid": "orange",
		"Partly Billed": "orange",
		"To Deliver": "orange",
		"To Deliver and Bill": "orange",
		"To Receive": "orange",
		"To Receive and Bill": "orange",
		"To Pay": "orange",
		Overdue: "red",
		Return: "gray",
		Closed: "gray",
	};

	constructor(frm, config) {
		this.frm = frm;
		Object.assign(this, config);
		this.party_key = frappe.scrub(this.party_type);
		this.accounts = frappe.model.can_read(this.invoice_doctype) && frappe.model.can_read("GL Entry");
		this.seq = { overview: 0, balances: 0 };
	}

	pref(key) {
		try {
			return localStorage.getItem(`${this.party_key}-overview:${key}`);
		} catch (e) {
			return null;
		}
	}
	set_pref(key, value) {
		try {
			localStorage.setItem(`${this.party_key}-overview:${key}`, value);
		} catch (e) {
			return;
		}
	}

	refresh() {
		this.needs_refresh = true;
		this.show();
	}

	async show() {
		if (this.frm.get_active_tab()?.df.fieldname !== "overview_tab") return;
		if (!this.needs_refresh) return;
		await frappe.require(["desk_charts.bundle.js", "desk_charts.bundle.css"]);
		if (this.frm.get_active_tab()?.df.fieldname !== "overview_tab" || !this.needs_refresh) return;
		this.needs_refresh = false;
		if (this.party !== this.frm.doc.name) this.build();
		else this.load_companies();
	}

	build() {
		this.reset();
		this.wrapper = this.frm.get_field("overview_html").$wrapper;
		this.wrapper.empty();
		this.$root = $('<div class="party-overview">').appendTo(this.wrapper);
		this.build_header();
		this.build_sections();

		this.load_companies();
	}

	reset() {
		const { PERIODS } = erpnext.PartyOverview;
		this.seq.overview++;
		this.seq.balances++;
		this.overview = null;
		this.balances = null;
		this.party = this.frm.doc.name;
		this.state = {
			company: this.pref("company") || frappe.defaults.get_user_default("Company"),
			period: PERIODS.includes(this.pref("period")) ? this.pref("period") : PERIODS[0],
			doc_type: "All",
		};
		this.companies_ready = false;
		this.list = null;
		this.destroy_trend();
		this.clear_charts();
	}

	build_header() {
		this.$header = $('<div class="co-header">').appendTo(this.$root);
		this.$controls = $('<div class="co-header-controls">').appendTo(this.$header);
		this.$period = $('<div class="co-period">').toggle(!!this.accounts).appendTo(this.$header);

		this.company_field = this.make_select(
			this.$controls,
			__("Company"),
			[this.state.company],
			(value) => {
				if (!this.companies_ready || value === this.state.company) return;
				this.state.company = value;
				this.set_pref("company", value);
				this.load();
				this.refresh_list();
			}
		);
		const single_company = Object.keys(locals[":Company"] || {}).length === 1;
		if (single_company) this.company_field.$wrapper.parent().hide();
		this.period_field = this.make_select(
			this.$controls,
			this.period_label,
			erpnext.PartyOverview.PERIODS,
			(value) => {
				if (value === this.state.period) return;
				this.state.period = value;
				this.set_pref("period", value);
				this.load({ balances: false });
			}
		);
		this.period_field.set_value(this.state.period);
		this.period_field.$wrapper.parent().toggle(!!this.accounts);
		this.has_controls = !single_company || this.accounts;
		this.$header.toggle(this.has_controls);
	}

	build_sections() {
		this.$body = $('<div class="co-body">').appendTo(this.$root);
		this.$position = $('<div class="co-section co-kpis">').appendTo(this.$body);
		this.$trend = $('<div class="co-section">').appendTo(this.$body);
		this.$charts = $('<div class="co-section co-two-col">').appendTo(this.$body);
		this.$pipeline = $('<div class="co-section">').appendTo(this.$body);
		this.$recent = $('<div class="co-section">').appendTo(this.$body);
		this.$empty = $('<div class="co-section">').hide().appendTo(this.$root);

		this.build_recent();
		const party = this.party;
		frappe
			.require("embedded_list.bundle.js")
			.then(() => party === this.party && this.build_list())
			.catch((e) => console.error("Party Overview: failed to load embedded_list.bundle.js", e));
	}

	load_companies() {
		const party = this.party;
		const token = (this.company_seq = (this.company_seq || 0) + 1);
		this.companies_ready = false;
		return frappe
			.xcall(`${this.method_path}.get_${this.party_key}_companies`, { [this.party_key]: party })
			.then((companies) => {
				if (party !== this.party || token !== this.company_seq) return;
				if (!companies.length) {
					this.render_no_activity();
					return;
				}
				this.$empty.hide();
				this.$body.show();
				this.$header.toggle(this.has_controls);
				this.company_field.df.options = companies.join("\n");
				this.company_field.refresh();
				const known = companies.includes(this.state.company);
				if (!known) this.state.company = companies[0];
				this.company_field.set_value(this.state.company);
				this.companies_ready = true;
				this.load();
				this.refresh_list();
			});
	}

	refresh_list() {
		if (this.list && this.companies_ready) this.list.refresh();
	}

	make_select($parent, label, options, onchange) {
		const control = frappe.ui.form.make_control({
			parent: $('<div class="co-filter">').appendTo($parent),
			df: { fieldtype: "Select", fieldname: frappe.scrub(label), label, options: options.join("\n") },
			render_input: true,
			only_input: true,
		});
		control.refresh();
		control.$input.on("change", function () {
			onchange(this.value);
		});
		return control;
	}

	load({ balances = true } = {}) {
		if (!this.companies_ready || !this.state.company) return;
		this.fetch("overview", `get_${this.party_key}_overview`, { period: this.state.period });
		if (balances && this.accounts) this.fetch("balances", this.balances_method);
	}

	fetch(key, method, args = {}) {
		const token = ++this.seq[key];
		this[key] = { loading: true };
		this.render(key);
		frappe
			.xcall(`${this.method_path}.${method}`, {
				[this.party_key]: this.party,
				company: this.state.company,
				...args,
			})
			.then((data) => (data ? { data } : { none: true }))
			.catch(() => ({ error: true }))
			.then((result) => {
				if (token !== this.seq[key]) return;
				this[key] = result;
				if (result.data) this.currency = result.data.currency;
				this.render(key);
			});
	}

	render(key) {
		this.render_position();
		if (key === "overview") {
			this.$period.text(this.period_text());
			this.render_trend();
			this.render_pipeline();
		}
		this.render_charts(key);
	}

	render_no_activity() {
		this.$body.hide();
		this.$header.hide();
		const actions = this.empty_doctypes
			.filter((doctype) => frappe.model.can_create(doctype) && this.frm.make_methods?.[doctype])
			.map((doctype) => ({
				label: __("New {0}", [__(doctype)]),
				icon: "plus",
				onclick: () => this.frm.make_methods[doctype](),
			}));
		this.$empty
			.empty()
			.append(
				frappe.ui.empty_state({
					icon: "inbox",
					title: __("No activity yet"),
					description: this.empty_description,
					actions,
				})
			)
			.show();
	}

	money(value) {
		return format_currency(flt(value), this.currency);
	}
	money0(value) {
		return format_currency(flt(value), this.currency, 0);
	}
	short_money(v) {
		const format = window.get_number_format(this.currency) || "";
		const country = format.includes(",##,") ? "India" : null;
		const n = flt(v);
		const short = frappe.utils.shorten_number(Math.abs(n), country, 4, 1);
		return (n < 0 ? "-" : "") + window.get_currency_symbol(this.currency) + (short || "0");
	}

	period_text() {
		const range = this.overview?.data?.period_range;
		if (!range) return "";
		const from = moment(range.from_date);
		const to = moment(range.to_date);
		const from_fmt = from.year() === to.year() ? "D MMM" : "D MMM YYYY";
		return from.format(from_fmt) + " – " + to.format("D MMM YYYY");
	}

	render_position() {
		if (!this.accounts) {
			this.$position.hide();
			return;
		}
		const items = this.position_cards().filter(Boolean);
		this.$position.empty().append(frappe.ui.stat_cards({ items }));
	}

	delta_opts(card, suffix) {
		if (card.delta === null || card.delta === undefined) return null;
		return {
			value: card.delta,
			positive_is_good: card.delta_positive_is_good,
			suffix,
		};
	}

	destroy_trend() {
		if (this.trend_chart) this.trend_chart.destroy();
		this.trend_chart = null;
		this.trend_target = null;
		this.$trend_notes = null;
	}

	render_trend() {
		const spec = this.accounts && this.trend_spec();
		this.$trend.toggle(!!spec);
		if (!spec) {
			this.destroy_trend();
			this.$trend.empty();
			return;
		}

		if (this.trend_chart && this.overview?.loading) {
			this.$trend.addClass("co-loading").attr("aria-busy", "true");
			return;
		}
		this.$trend.removeClass("co-loading").removeAttr("aria-busy");

		if (this.trend_chart && spec.data) {
			this.trend_target = spec.data;
			this.trend_chart.update(spec.data);
			this.set_trend_notes(spec.notes);
			return;
		}

		this.destroy_trend();
		this.$trend.empty();
		const $panel = this.panel(this.$trend, spec);
		if (this.show_state($panel, this.overview, 220, this.overview_error, "trend")) return;
		if (!spec.data) {
			this.$trend.empty().hide();
			return;
		}

		this.trend_target = spec.data;
		this.trend_chart = this.draw_trend($('<div class="co-chart">').appendTo($panel)[0], spec);
		this.$trend_notes = $('<div class="co-note">').appendTo($panel);
		this.set_trend_notes(spec.notes);
	}

	draw_trend(el, spec) {
		const style = getComputedStyle(el);
		return new frappe.Chart(el, {
			type: spec.type,
			height: spec.height || 220,
			colors: spec.colors.map((token) => style.getPropertyValue(token).trim()),
			data: spec.data,
			lineOptions: { regionFill: 1, hideDots: 1 },
			axisOptions: {
				xIsSeries: 1,
				xAxisMode: "none",
				shortenYAxisNumbers: 1,
				numberFormatter: (v) => this.short_money(v),
			},
			tooltipOptions: {
				formatTooltipX: (label, index) => this.trend_target?.titles?.[index] || label,
				formatTooltipY: (v) => this.money0(v),
			},
			animate: 1,
			disableEntryAnimation: 1,
		});
	}

	draw_donut($parent, { segments, center, format }) {
		const $chart = $('<div class="co-chart">').appendTo($parent);
		this.charts.push(
			new frappe.Chart($chart[0], {
				type: "donut",
				height: 320,
				data: {
					labels: segments.map((s) => s.label),
					datasets: [{ values: segments.map((s) => Math.max(flt(s.value), 0)) }],
				},
				colors: segments.map((s) => s.color),
				center,
				tooltipOptions: format && { formatTooltipY: format },
			})
		);
		return $chart;
	}

	clear_charts() {
		(this.charts || []).forEach((chart) => chart.destroy());
		this.charts = [];
		return this.$charts ? this.$charts.empty() : $();
	}

	set_trend_notes(notes) {
		if (!this.$trend_notes) return;
		this.$trend_notes.text(notes.join(" · ")).toggle(!!notes.length);
	}

	render_ageing({ title, subtitle, note }) {
		const $panel = this.panel(this.$charts, {
			title,
			subtitle,
			right: this.report_link(__(this.ledger_report), () => this.open_ledger()),
		});
		if (this.show_state($panel, this.balances, 180, this.balances_error)) return;
		const a = this.balances.data.ageing;
		if (flt(a.total) <= 0) {
			$panel.remove();
			return;
		}

		const $chart = $('<div class="co-age-chart">').appendTo($panel);
		this.charts.push(
			new frappe.Chart($chart[0], {
				type: "bar",
				barOptions: { horizontal: 1 },
				data: {
					labels: a.buckets.map((b) => b.label),
					datasets: [{ name: __("Outstanding"), values: a.buckets.map((b) => flt(b.value)) }],
				},
				colors: ["var(--co-series-1)"],
				axisOptions: { numberFormatter: (v) => this.short_money(v) },
				tooltipOptions: { formatTooltipY: (v) => this.money0(v) },
			})
		);

		$('<div class="co-note">')
			.text(flt(a.overdue) > 0 ? note(a) : __("Nothing overdue"))
			.appendTo($panel);
	}

	render_pipeline() {
		this.$pipeline.empty();
		this.section_head(this.$pipeline, { title: __("Open Pipeline") });
		if (this.overview.loading) {
			const items = this.pipeline_specs({}).map((s) => ({ label: s.label, loading: true }));
			frappe.ui.stat_cards({ items }).appendTo(this.$pipeline);
			return;
		}
		const pl = this.overview.data?.pipeline || {};
		const specs = this.pipeline_specs(pl).filter((s) => s.data);
		if (!specs.length) {
			this.empty_note(this.$pipeline, this.overview_error, 0).addClass("co-error");
			return;
		}

		const items = specs.map((s) => ({
			label: s.label,
			value: this.money0(s.data.value),
			caption: s.data.count ? s.caption(s.data) : s.empty || __("None open"),
			onclick: () => this.list_route(s.route[0], s.route[1]),
		}));
		frappe.ui.stat_cards({ items }).appendTo(this.$pipeline);

		const note = this.pipeline_note(pl);
		if (note) $('<div class="co-note">').text(note).appendTo(this.$pipeline);
	}

	show_state($panel, source, height, error_text, section) {
		if (!source || source.loading) {
			$panel.attr("aria-busy", "true");
			$('<div class="co-placeholder">')
				.css("height", height)
				.append(frappe.ui.skeleton({ width: "100%", height: "100%" }))
				.appendTo($panel);
			return true;
		}
		if (source.none) {
			this.empty_note($panel, __("Not available"), height);
			return true;
		}
		if (source.error || source.data?.errors?.[section]) {
			this.empty_note($panel, error_text, height).addClass("co-error");
			return true;
		}
		return false;
	}

	empty_note($panel, text, height) {
		return $('<div class="co-empty">').css("min-height", height).text(text).appendTo($panel);
	}

	build_recent() {
		this.section_head(this.$recent, {
			title: __("Recent Transactions"),
			right: this.build_type_filter(),
		});
		this.$list = $('<div class="co-list">').appendTo(this.$recent);
	}

	build_type_filter() {
		const types = ["All", ...this.transaction_types];
		const $holder = $('<div class="co-filter">');
		const control = frappe.ui.form.make_control({
			parent: $holder,
			df: {
				fieldtype: "Select",
				fieldname: "doc_type",
				options: types.map((t) => (t === "All" ? "All Document Types" : t)).join("\n"),
			},
			render_input: true,
			only_input: true,
		});
		control.refresh();
		control.set_value("All Document Types");
		control.$input.on("change", () => {
			const idx = control.$input.prop("selectedIndex");
			this.state.doc_type = types[idx] || "All";
			this.list && this.list.refresh();
		});
		return $holder;
	}

	build_list() {
		const me = this;
		const { RECENT_LIMIT, STATUS_THEME } = erpnext.PartyOverview;
		this.list = new frappe.ui.EmbeddedList({
			wrapper: this.$list,
			show_search: false,
			page_size: RECENT_LIMIT,
			empty_message: __("No transactions yet"),
			empty_icon: "list",
			columns: [
				{
					label: __("Document"),
					fieldname: "name",
					type: "link",
					route: (row) => ["Form", row.doctype, row.name],
				},
				{ label: __("Type"), fieldname: "type_label" },
				{ label: __("Date"), render: (row) => frappe.datetime.str_to_user(row.date) },
				{
					label: __("Status"),
					fieldname: "status",
					type: "badge",
					color: (row) => STATUS_THEME[row.status] || "gray",
				},
				{
					label: __("Amount"),
					render: (row) => `<div class="text-right">${me.money(row.amount)}</div>`,
				},
				{ label: this.outstanding_label, render: (row) => me.outstanding_cell(row) },
			],
			get_data() {
				if (!me.state.company) return Promise.resolve([]);
				return frappe.xcall(`${me.method_path}.get_${me.party_key}_transactions`, {
					[me.party_key]: me.frm.doc.name,
					company: me.state.company,
					doc_type: me.state.doc_type,
					limit: RECENT_LIMIT,
				});
			},
		});
		this.refresh_list();
	}

	outstanding_cell(row) {
		if (row.outstanding == null || flt(row.outstanding) <= 0)
			return '<div class="text-right text-ink-gray-4">—</div>';
		const cls = row.status === "Overdue" ? "text-ink-red-7" : "";
		return `<div class="text-right ${cls}">${this.money(row.outstanding)}</div>`;
	}

	section_head($parent, { title, subtitle, right } = {}) {
		const $head = $('<div class="co-head">').appendTo($parent);
		const $top = $('<div class="co-head-top">').appendTo($head);
		$('<div class="co-title">').text(title).appendTo($top);
		if (right) $('<div class="co-head-action">').append(right).appendTo($top);
		if (subtitle) $('<div class="co-subtitle">').text(subtitle).appendTo($head);
		return $head;
	}

	panel($parent, opts = {}) {
		const $panel = $('<div class="co-panel">').appendTo($parent);
		if (opts.title) this.section_head($panel, opts);
		return $panel;
	}

	report_link(text, on_click) {
		return frappe.ui.button({
			label: text,
			variant: "ghost",
			size: "sm",
			icon_right: "arrow-up-right",
			onclick: on_click,
		});
	}

	open_ledger() {
		frappe.route_options = {
			party_type: this.party_type,
			party: this.frm.doc.name,
			company: this.state.company,
		};
		frappe.set_route("query-report", this.ledger_report);
	}
	open_reconciliation() {
		frappe.route_options = {
			company: this.state.company,
			party_type: this.party_type,
			party: this.frm.doc.name,
		};
		frappe.set_route("Form", "Payment Reconciliation");
	}
	list_route(doctype, filters) {
		frappe.route_options = filters;
		frappe.set_route("List", doctype);
	}
};
