frappe.provide("erpnext");

const OVERVIEW_METHOD = "erpnext.selling.doctype.customer.customer_overview";
const PERIODS = ["This fiscal year", "Last 12 months", "This quarter", "Last fiscal year"];
const TXN_TYPES = ["All", "Sales Invoice", "Sales Order", "Payment Entry"];
const STATUS_THEME = {
	Paid: "green",
	Completed: "green",
	Submitted: "blue",
	"To Bill": "blue",
	Unpaid: "orange",
	"Partly Paid": "orange",
	"To Deliver": "orange",
	"To Deliver and Bill": "orange",
	Overdue: "red",
	Return: "gray",
	Closed: "gray",
};
const CHART_BLUE = "#095895";

frappe.ui.form.on("Customer", {
	refresh(frm) {
		if (frm.is_new() || !frm.get_field("overview_html")) return;
		if (!frm.customer_overview) frm.customer_overview = new erpnext.CustomerOverview(frm);
		frm.customer_overview.refresh();
	},
});

erpnext.CustomerOverview = class CustomerOverview {
	constructor(frm) {
		this.frm = frm;
		this.wrapper = frm.get_field("overview_html").$wrapper;
		this.state = {
			company: this.pref("company") || frappe.defaults.get_user_default("Company"),
			period: this.pref("period") || PERIODS[0],
			doc_type: "All",
		};
		this.seq = 0;
	}

	pref(key) {
		try {
			return localStorage.getItem("customer-overview:" + key);
		} catch (e) {
			return null;
		}
	}
	set_pref(key, value) {
		try {
			localStorage.setItem("customer-overview:" + key, value);
		} catch (e) {
			return;
		}
	}

	refresh() {
		if (this.built) {
			this.load();
			return;
		}
		this.build();
	}

	build() {
		this.wrapper.empty();
		this.$root = $('<div class="customer-overview">').appendTo(this.wrapper);

		const $header = $('<div class="co-header">').appendTo(this.$root);
		const $left = $('<div class="co-header-left">').appendTo($header);
		$('<div class="co-htitle">').text(__("Overview")).appendTo($left);
		this.$context = $('<div class="co-hsub text-muted">').appendTo($left);
		const $controls = $('<div class="co-header-controls">').appendTo($header);

		this.company_field = this.make_select($controls, __("Company"), [this.state.company], (value) => {
			this.state.company = value;
			this.set_pref("company", value);
			this.load();
			this.refresh_list();
		});
		this.period_field = this.make_select($controls, __("Period"), PERIODS, (value) => {
			this.state.period = value;
			this.set_pref("period", value);
			this.load();
		});
		this.period_field.set_value(this.state.period);

		this.$position = $('<div class="co-section co-kpis">').appendTo(this.$root);
		this.$charts = $('<div class="co-section co-two-col">').appendTo(this.$root);
		this.$pipeline = $('<div class="co-section">').appendTo(this.$root);
		this.$recent = $('<div class="co-section">').appendTo(this.$root);

		this.build_recent();

		frappe
			.require("embedded_list.bundle.js")
			.then(() => this.build_list())
			.catch((e) => console.error("Customer Overview: failed to load embedded_list.bundle.js", e));

		frappe
			.xcall(OVERVIEW_METHOD + ".get_customer_companies", { customer: this.frm.doc.name })
			.then((companies) => {
				const list = (companies && companies.length ? companies : [this.state.company]).filter(
					Boolean
				);
				if (!list.length) return;
				if (!list.includes(this.state.company)) this.state.company = list[0];
				this.company_field.df.options = list.join("\n");
				this.company_field.refresh();
				this.company_field.set_value(this.state.company);
				this.built = true;
				this.companies_ready = true;
				this.load();
				this.refresh_list();
			});
	}

	refresh_list() {
		if (this.list && this.state.company) this.list.refresh();
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

	load() {
		const token = ++this.seq;
		frappe
			.xcall(OVERVIEW_METHOD + ".get_customer_overview", {
				customer: this.frm.doc.name,
				company: this.state.company,
				period: this.state.period,
			})
			.then((data) => {
				if (token !== this.seq) return;
				this.data = data;
				this.currency = data.currency;
				this.render_position();
				this.render_charts();
				this.render_pipeline();
			});
	}

	money(value) {
		return format_currency(flt(value), this.currency);
	}
	money0(value) {
		return format_currency(flt(value), this.currency, 0);
	}
	short_money(v) {
		const n = Math.abs(flt(v));
		let x = n,
			suf = "";
		if (n >= 1e9) {
			x = n / 1e9;
			suf = "B";
		} else if (n >= 1e6) {
			x = n / 1e6;
			suf = "M";
		} else if (n >= 1e3) {
			x = n / 1e3;
			suf = "K";
		}
		const num = suf ? Math.round(x * 10) / 10 : Math.round(x);
		return (flt(v) < 0 ? "-" : "") + window.get_currency_symbol(this.currency) + num + suf;
	}
	date_range() {
		const from = moment(this.data.period_range.from_date);
		const to = moment(this.data.period_range.to_date);
		const from_fmt = from.year() === to.year() ? "D MMM" : "D MMM YYYY";
		return from.format(from_fmt) + " – " + to.format("D MMM YYYY");
	}

	render_position() {
		const p = this.data.position || {};
		this.$context.text(this.date_range());
		this.$position.empty();
		const items = [];
		if (p.net_sales)
			items.push({
				label: __("Net Sales"),
				value: this.money0(p.net_sales.value),
				delta: this.delta_opts(p.net_sales, __("since last year")),
				caption: (p.net_sales.count || 0) + " " + __("invoices"),
				onclick: () => this.open_analytics(),
			});
		if (p.outstanding)
			items.push({
				label: __("Receivable"),
				value: this.money0(p.outstanding.value),
				caption: this.outstanding_sub(p.outstanding),
				onclick: () => this.open_ar(),
			});
		if (p.overdue)
			items.push({
				label: __("Overdue"),
				value: this.money0(p.overdue.value),
				delta: this.delta_opts(p.overdue, __("since last month"), "red"),
				onclick: () => this.open_ar(),
			});
		if (p.advances)
			items.push({
				label: __("Advances"),
				value: this.money0(p.advances.value),
				caption: __("Not yet applied to invoices"),
				onclick: () => this.open_ar(),
			});
		if (p.credit) items.push(this.credit_opts(p.credit));
		frappe.ui.stat_cards({ items }).appendTo(this.$position);
	}

	outstanding_sub(o) {
		const parts = [];
		if (o.unpaid_count) parts.push(o.unpaid_count + " " + __("unpaid"));
		if (o.days_to_pay) parts.push(o.days_to_pay + " " + __("days to pay"));
		return parts.join(" · ");
	}

	credit_opts(credit) {
		if (!credit.limit) {
			return {
				label: __("Credit limit used"),
				value: $('<span class="text-muted">').text("—"),
				caption: __("Set a credit limit"),
				onclick: () => this.edit_credit_limit(),
			};
		}
		const pct = flt(credit.used_pct, 1);
		const color = pct >= 90 ? "var(--ink-red-5)" : pct >= 70 ? "var(--ink-amber-5)" : "rgb(40, 158, 96)";
		const left = flt(credit.limit) * (1 - pct / 100);
		const $caption = $("<div>");
		$("<div>")
			.text(__("{0} of {1} left", [this.short_money(left), this.short_money(credit.limit)]))
			.appendTo($caption);
		const $bar = $(
			'<div class="es-progress"><div class="es-progress__track" data-size="lg"><div class="es-progress__fill"></div></div></div>'
		).css("margin-top", "6px");
		$bar.find(".es-progress__fill").css({ width: Math.min(pct, 100) + "%", background: color });
		$bar.appendTo($caption);
		return {
			label: __("Credit limit used"),
			value: pct + "%",
			caption: $caption,
			onclick: () => this.edit_credit_limit(),
		};
	}

	edit_credit_limit() {
		if (this.frm.is_new()) return;
		const company = this.state.company;
		const credit = (this.data.position && this.data.position.credit) || {};
		frappe.prompt(
			[
				{
					fieldname: "credit_limit",
					fieldtype: "Currency",
					label: __("Credit Limit"),
					default: flt(credit.limit),
					description: __("Applies to {0}", [company]),
				},
			],
			(values) => this.save_credit_limit(company, flt(values.credit_limit)),
			__("Set Credit Limit"),
			__("Save")
		);
	}

	save_credit_limit(company, limit) {
		const frm = this.frm;
		let row = (frm.doc.credit_limits || []).find((r) => r.company === company);
		if (!row) row = frm.add_child("credit_limits", { company });
		row.credit_limit = limit;
		frm.dirty();
		frm.save().then(() => {
			frappe.show_alert({ message: __("Credit limit updated"), indicator: "green" });
			this.load();
		});
	}

	delta_opts(card, suffix, force) {
		if (card.delta === null || card.delta === undefined) return null;
		return {
			value: card.delta,
			positive_is_good: card.delta_positive_is_good,
			negative: force === "red",
			suffix,
		};
	}

	render_charts() {
		this.$charts.empty();
		const t = this.data.trend;
		const a = this.data.ageing;
		const has_trend = t && t.points && t.points.some((p) => flt(p.value) > 0);
		const has_ageing = a && flt(a.total) > 0;
		if (has_trend) this.render_trend();
		if (has_ageing) this.render_ageing();
		this.$charts.toggle(!!(has_trend || has_ageing));
	}

	render_trend() {
		const t = this.data.trend;
		const $panel = this.panel(this.$charts, {
			title: __("Monthly sales trend"),
			subtitle: __("Monthly, net of returns"),
			right: this.report_link(__("Sales Analytics"), () => this.open_analytics()),
		});
		const $chart = $('<div class="co-chart">').appendTo($panel);

		const notes = [];
		if (t.average) notes.push(__("avg") + " " + this.money0(t.average));
		if (t.has_mtd && t.points.length)
			notes.push(t.points[t.points.length - 1].label + " " + __("is month to date"));
		if (notes.length) $('<div class="co-note text-muted">').text(notes.join(" · ")).appendTo($panel);

		if (!t.points.length) return;
		new frappe.Chart($chart[0], {
			type: "line",
			height: 220,
			colors: [CHART_BLUE],
			data: {
				labels: t.points.map((p) => p.label),
				datasets: [{ name: __("Net Sales"), values: t.points.map((p) => flt(p.value)) }],
			},
			lineOptions: { regionFill: 1, hideDots: 1 },
			axisOptions: { xIsSeries: 1, shortenYAxisNumbers: 1 },
			tooltipOptions: { formatTooltipY: (v) => this.money(v) },
		});
	}

	render_ageing() {
		const a = this.data.ageing;
		const $panel = this.panel(this.$charts, {
			title: __("Receivables ageing"),
			subtitle: __("Outstanding by due date, net of credit notes"),
			right: this.report_link(__("Accounts Receivable"), () => this.open_ar()),
		});
		frappe.ui
			.bar_list({
				items: a.buckets.map((b) => ({
					label: b.label,
					value: flt(b.value),
					formatted: this.short_money(b.value),
				})),
				format: (v) => this.short_money(v),
				color: CHART_BLUE,
				on_click: () => this.open_ar(),
			})
			.appendTo($('<div class="co-age-chart">').appendTo($panel));
		$('<div class="co-note text-muted">')
			.append($("<span>").text(__("Overdue") + " "))
			.append($('<span class="text-danger">').text(this.money0(a.overdue)))
			.append(" · " + flt(a.overdue_pct, 1) + "% " + __("of outstanding"))
			.appendTo($panel);
	}

	render_pipeline() {
		const pl = this.data.pipeline;
		this.$pipeline.empty();
		const any =
			pl &&
			["quotations", "delivery", "billing", "invoices"].some(
				(k) => pl[k] && (pl[k].count || flt(pl[k].value))
			);
		this.$pipeline.toggle(!!any);
		if (!any) return;
		this.section_head(this.$pipeline, { title: __("Open pipeline") });
		const name = this.frm.doc.name;
		const company = this.state.company;

		const specs = [
			pl.quotations && {
				dot: "var(--gray-500)",
				label: __("Open Quotations"),
				data: pl.quotations,
				caption: pl.quotations.count + " " + __("quotations"),
				route: ["Quotation", { quotation_to: "Customer", party_name: name, status: "Open" }],
			},
			pl.delivery && {
				dot: "var(--orange-500)",
				label: __("Pending Delivery"),
				data: pl.delivery,
				caption: [
					pl.delivery.count + " " + __("orders"),
					pl.delivery.past_due && pl.delivery.past_due + " " + __("past promised date"),
				]
					.filter(Boolean)
					.join(" · "),
				route: ["Sales Order", { customer: name, company, status: "To Deliver and Bill" }],
			},
			pl.billing && {
				dot: "var(--blue-500)",
				label: __("Pending Billing"),
				data: pl.billing,
				caption: pl.billing.count + " " + __("orders") + " · " + __("delivered, not invoiced"),
				route: ["Sales Order", { customer: name, company, status: "To Bill" }],
			},
			pl.invoices && {
				dot: "var(--red-500)",
				label: __("Unpaid Invoices"),
				data: pl.invoices,
				caption: [
					pl.invoices.count + " " + __("invoices"),
					pl.invoices.overdue && pl.invoices.overdue + " " + __("overdue"),
				]
					.filter(Boolean)
					.join(" · "),
				route: ["Sales Invoice", { customer: name, company, status: "Unpaid" }],
			},
		].filter(Boolean);

		const items = specs.map((s) => ({
			dot: s.dot,
			label: s.label,
			value: this.money0(s.data.value),
			caption: s.caption,
			onclick: () => this.list_route(s.route[0], s.route[1]),
		}));
		frappe.ui.stat_cards({ items }).appendTo(this.$pipeline);

		$('<div class="co-note text-muted">')
			.text(__("The same order can appear under both Pending Delivery and Pending Billing."))
			.appendTo(this.$pipeline);
	}

	build_recent() {
		this.section_head(this.$recent, {
			title: __("Recent transactions"),
			right: this.build_type_filter(),
		});
		this.$list = $('<div class="co-list">').appendTo(this.$recent);
	}

	build_type_filter() {
		const $holder = $('<div class="co-filter">');
		const control = frappe.ui.form.make_control({
			parent: $holder,
			df: {
				fieldtype: "Select",
				fieldname: "doc_type",
				options: TXN_TYPES.map((t) => (t === "All" ? "All document types" : t)).join("\n"),
			},
			render_input: true,
			only_input: true,
		});
		control.refresh();
		control.set_value("All document types");
		control.$input.on("change", () => {
			const idx = control.$input.prop("selectedIndex");
			this.state.doc_type = TXN_TYPES[idx] || "All";
			this.list && this.list.refresh();
		});
		return $holder;
	}

	build_list() {
		const me = this;
		this.list = new frappe.ui.EmbeddedList({
			wrapper: this.$list,
			show_search: false,
			page_size: 7,
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
				{ label: __("Receivable"), render: (row) => me.outstanding_cell(row) },
			],
			get_data() {
				if (!me.state.company) return Promise.resolve([]);
				return frappe.xcall(OVERVIEW_METHOD + ".get_customer_transactions", {
					customer: me.frm.doc.name,
					company: me.state.company,
					doc_type: me.state.doc_type,
					limit: 7,
				});
			},
		});
		if (this.companies_ready) this.refresh_list();
	}

	outstanding_cell(row) {
		if (flt(row.outstanding) <= 0) return '<div class="text-right text-extra-muted">—</div>';
		const cls = row.status === "Overdue" ? "text-danger" : "";
		return `<div class="text-right ${cls}">${this.money(row.outstanding)}</div>`;
	}

	section_head($parent, { title, subtitle, right } = {}) {
		const $head = $('<div class="co-head">').appendTo($parent);
		const $top = $('<div class="co-head-top">').appendTo($head);
		$('<div class="co-title">').text(title).appendTo($top);
		if (right) $top.append(right);
		if (subtitle) $('<div class="co-subtitle text-muted">').text(subtitle).appendTo($head);
		return $head;
	}

	panel($parent, opts = {}) {
		const $panel = $('<div class="widget border co-panel">').appendTo($parent);
		if (opts.title) this.section_head($panel, opts);
		return $panel;
	}

	report_link(text, on_click) {
		return $("<a>")
			.attr("href", "#")
			.addClass("co-report-link")
			.text(text)
			.on("click", (e) => {
				e.preventDefault();
				on_click();
			});
	}

	open_ar() {
		frappe.route_options = {
			party_type: "Customer",
			party: this.frm.doc.name,
			company: this.state.company,
		};
		frappe.set_route("query-report", "Accounts Receivable");
	}
	open_analytics() {
		frappe.route_options = {
			tree_type: "Customer",
			doc_type: "Sales Invoice",
			company: this.state.company,
			from_date: this.data.period_range.from_date,
			to_date: this.data.period_range.to_date,
			value_quantity: "Value",
		};
		frappe.set_route("query-report", "Sales Analytics");
	}
	list_route(doctype, filters) {
		frappe.route_options = filters;
		frappe.set_route("List", doctype);
	}
};
