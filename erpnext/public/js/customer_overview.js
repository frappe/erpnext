frappe.provide("erpnext");

const OVERVIEW_METHOD = "erpnext.selling.doctype.customer.customer_overview";
const PERIODS = ["Current Fiscal Year", "Last 12 Months", "This Quarter", "Last Fiscal Year"];
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
const CLOSED_ORDER_STATUS = ["Closed", "Completed", "On Hold"];
const RECENT_LIMIT = 10;
const COUNT = {
	invoices: (n) => (n === 1 ? __("1 invoice") : __("{0} invoices", [n])),
	quotations: (n) => (n === 1 ? __("1 quotation") : __("{0} quotations", [n])),
	orders: (n) => (n === 1 ? __("1 order") : __("{0} orders", [n])),
	reconcile: (n) =>
		n === 1 ? __("Reconcile with 1 unpaid invoice") : __("Reconcile with {0} unpaid invoices", [n]),
	unapplied: (n) =>
		n === 1 ? __("Not applied to 1 unpaid invoice") : __("Not applied to {0} unpaid invoices", [n]),
	days_to_pay: (n) => (n === 1 ? __("1 day to pay") : __("{0} days to pay", [n])),
};

frappe.ui.form.on("Customer", {
	refresh(frm) {
		if (frm.is_new() || !frm.get_field("overview_html")) return;
		if (!frm.customer_overview) frm.customer_overview = new erpnext.CustomerOverview(frm);
		frm.customer_overview.refresh();
	},
	on_tab_change(frm) {
		frm.customer_overview?.show();
	},
});

erpnext.CustomerOverview = class CustomerOverview {
	constructor(frm) {
		this.frm = frm;
		this.accounts = frappe.model.can_read("Sales Invoice") && frappe.model.can_read("GL Entry");
		this.seq = { sales: 0, ar: 0 };
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
		this.needs_refresh = true;
		this.show();
	}

	async show() {
		if (this.frm.get_active_tab()?.df.fieldname !== "overview_tab") return;
		if (!this.needs_refresh) return;
		await frappe.require(["desk_charts.bundle.js", "desk_charts.bundle.css"]);
		if (this.frm.get_active_tab()?.df.fieldname !== "overview_tab" || !this.needs_refresh) return;
		this.needs_refresh = false;
		if (this.customer !== this.frm.doc.name) this.build();
		else this.load_companies();
	}

	build() {
		this.reset();
		this.wrapper = this.frm.get_field("overview_html").$wrapper;
		this.wrapper.empty();
		this.$root = $('<div class="customer-overview">').appendTo(this.wrapper);
		this.build_header();
		this.build_sections();

		this.load_companies();
	}

	reset() {
		this.seq.sales++;
		this.seq.ar++;
		this.sales = null;
		this.ar = null;
		this.customer = this.frm.doc.name;
		this.state = {
			company: this.pref("company") || frappe.defaults.get_user_default("Company"),
			period: PERIODS.includes(this.pref("period")) ? this.pref("period") : PERIODS[0],
			doc_type: "All",
		};
		this.companies_ready = false;
		this.list = null;
		this.destroy_trend();
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
		this.period_field = this.make_select(this.$controls, __("Sales Period"), PERIODS, (value) => {
			if (value === this.state.period) return;
			this.state.period = value;
			this.set_pref("period", value);
			this.load({ receivables: false });
		});
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
		const customer = this.customer;
		frappe
			.require("embedded_list.bundle.js")
			.then(() => customer === this.customer && this.build_list())
			.catch((e) => console.error("Customer Overview: failed to load embedded_list.bundle.js", e));
	}

	load_companies() {
		const customer = this.customer;
		const token = (this.company_seq = (this.company_seq || 0) + 1);
		this.companies_ready = false;
		return frappe.xcall(OVERVIEW_METHOD + ".get_customer_companies", { customer }).then((companies) => {
			if (customer !== this.customer || token !== this.company_seq) return;
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

	load({ receivables = true } = {}) {
		if (!this.companies_ready || !this.state.company) return;
		this.fetch("sales", "get_customer_overview", { period: this.state.period });
		if (receivables && this.accounts) this.fetch("ar", "get_customer_receivables");
	}

	fetch(key, method, args = {}) {
		const token = ++this.seq[key];
		this[key] = { loading: true };
		this.render(key);
		frappe
			.xcall(OVERVIEW_METHOD + "." + method, {
				customer: this.customer,
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
		if (key === "sales") {
			this.$period.text(this.period_text());
			this.render_trend();
			this.render_pipeline();
		} else {
			this.render_receivables();
		}
	}

	render_no_activity() {
		this.$body.hide();
		this.$header.hide();
		const actions = ["Quotation", "Sales Order"]
			.filter((doctype) => frappe.model.can_create(doctype))
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
					description: __(
						"Quotations, orders, invoices and payments for this customer will show up here."
					),
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
		const range = this.sales && this.sales.data && this.sales.data.period_range;
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
		const items = [this.net_sales_card(), ...this.receivable_cards()].filter(Boolean);
		this.$position.empty().append(frappe.ui.stat_cards({ items }));
	}

	net_sales_card() {
		const card = { label: __("Net Sales") };
		const sales = this.sales || { loading: true };
		if (sales.loading) return { ...card, loading: true };
		const p = sales.data && sales.data.position && sales.data.position.net_sales;
		if (sales.error || sales.data?.errors?.position)
			return { ...card, value: "—", caption: __("Could not load sales") };
		if (!p) return { ...card, value: null };
		return {
			...card,
			value: this.money0(p.value),
			delta: this.delta_opts(p, __("since last year")),
			caption: COUNT.invoices(p.count || 0),
			onclick: () => this.open_analytics(),
		};
	}

	receivable_cards() {
		const ar = this.ar || { loading: true };
		const labels = [__("Receivable"), __("Overdue"), __("Advances")];
		if (ar.loading) return labels.map((label) => ({ label, loading: true }));
		if (ar.none) return [];
		if (ar.error)
			return labels.map((label) => ({ label, value: "—", caption: __("Could not load receivables") }));
		if (!ar.data) return labels.map((label) => ({ label, value: null }));
		const { outstanding, overdue, advances } = ar.data;
		return [
			{
				label: labels[0],
				value: this.money0(outstanding.value),
				caption: this.outstanding_sub(outstanding),
				onclick: () => this.open_ar(),
			},
			{
				label: labels[1],
				value: this.money0(overdue.value),
				delta: this.delta_opts(overdue, __("since last month")),
				onclick: () => this.open_ar(),
			},
			this.advances_card(labels[2], advances, outstanding.unpaid_count),
		];
	}

	advances_card(label, advances, unpaid_count) {
		if (advances.value == null)
			return {
				label,
				value: "—",
				caption: __("Not available in Accounts Receivable Summary"),
				onclick: () => this.open_ar(),
			};
		const card = { label, value: this.money0(advances.value), onclick: () => this.open_ar() };
		if (!flt(advances.value)) return { ...card, caption: __("No unapplied payments") };
		if (!unpaid_count) return { ...card, caption: __("Credit balance, no invoices to apply it to") };
		if (!frappe.model.can_write("Payment Reconciliation"))
			return { ...card, caption: COUNT.unapplied(unpaid_count) };
		return {
			...card,
			caption: COUNT.reconcile(unpaid_count),
			onclick: () => this.open_reconciliation(),
		};
	}

	outstanding_sub(o) {
		const parts = [];
		if (o.unpaid_count) parts.push(__("{0} unpaid", [o.unpaid_count]));
		if (o.days_to_pay) parts.push(COUNT.days_to_pay(o.days_to_pay));
		return parts.join(" · ");
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
		this.$trend.toggle(!!this.accounts);
		if (!this.accounts) {
			this.destroy_trend();
			this.$trend.empty();
			return;
		}

		if (this.trend_chart && this.sales && this.sales.loading) {
			this.$trend.addClass("co-loading").attr("aria-busy", "true");
			return;
		}
		this.$trend.removeClass("co-loading").removeAttr("aria-busy");

		const t = this.sales.data && this.sales.data.trend;
		const data = t &&
			t.points.some((p) => flt(p.value)) && {
				labels: t.points.map((p) => p.label),
				datasets: [{ name: __("Net Sales"), values: t.points.map((p) => flt(p.value)) }],
			};

		if (this.trend_chart && data) {
			this.trend_target = data;
			this.trend_chart.update(data);
			this.trend_notes(t);
			return;
		}

		this.destroy_trend();
		this.$trend.empty();
		const $panel = this.panel(this.$trend, {
			title: __("Monthly Sales Trend"),
			subtitle: __("Monthly, net of returns"),
			right: this.report_link(__("Sales Analytics"), () => this.open_analytics()),
		});
		if (this.show_state($panel, this.sales, 220, __("Could not load sales"), "trend")) return;
		if (!data) {
			this.empty_note($panel, __("No sales in this period"), 220);
			return;
		}

		this.trend_target = data;
		this.trend_chart = this.draw_trend($('<div class="co-chart">').appendTo($panel)[0], data);
		this.$trend_notes = $('<div class="co-note">').appendTo($panel);
		this.trend_notes(t);
	}

	draw_trend(el, data) {
		const chart = new frappe.Chart(el, {
			type: "line",
			height: 220,
			colors: [getComputedStyle(document.documentElement).getPropertyValue("--blue-600").trim()],
			data: {
				labels: data.labels,
				datasets: data.datasets.map((d) => ({ name: d.name, values: d.values.map(() => 0) })),
			},
			lineOptions: { regionFill: 1, hideDots: 1 },
			axisOptions: { xIsSeries: 1, shortenYAxisNumbers: 1 },
			tooltipOptions: { formatTooltipY: (v) => this.money(v) },
			animate: 1,
			disableEntryAnimation: 1,
		});
		requestAnimationFrame(() => {
			if (this.trend_chart === chart) chart.update(this.trend_target);
		});
		return chart;
	}

	trend_notes(t) {
		if (!this.$trend_notes) return;
		const notes = [];
		if (t.average) notes.push(__("Avg {0}", [this.money0(t.average)]));
		if (t.has_mtd) notes.push(__("{0} is month to date", [t.points[t.points.length - 1].label]));
		this.$trend_notes.text(notes.join(" · ")).toggle(!!notes.length);
	}

	render_receivables() {
		this.$charts.empty().toggle(!!this.accounts && !this.ar?.none);
		if (!this.accounts || this.ar?.none) return;
		this.render_ageing();
		this.render_credit();
	}

	render_ageing() {
		const $panel = this.panel(this.$charts, {
			title: __("Receivables Ageing"),
			subtitle: __("Unpaid invoices by due date"),
			right: this.report_link(__("Accounts Receivable"), () => this.open_ar()),
		});
		if (this.show_state($panel, this.ar, 180, __("Could not load receivables"))) return;
		const a = this.ar.data.ageing;
		if (flt(a.total) <= 0) {
			this.empty_note($panel, __("Nothing outstanding"), 180);
			return;
		}

		frappe.ui
			.bar_list({
				items: a.buckets.map((b) => ({
					label: b.label,
					value: flt(b.value),
					formatted: this.short_money(b.value),
				})),
				format: (v) => this.short_money(v),
			})
			.appendTo($('<div class="co-age-chart">').appendTo($panel));

		$('<div class="co-note">')
			.text(
				flt(a.overdue) > 0
					? __("Overdue {0} · {1}% of unpaid invoices", [
							this.money0(a.overdue),
							flt(a.overdue_pct, 1),
					  ])
					: __("Nothing overdue")
			)
			.appendTo($panel);
	}

	render_credit() {
		const data = this.ar.data;
		const limit = flt(data && data.credit.limit);
		const used = Math.max(flt(data && data.credit.used), 0);
		const can_edit = this.frm.has_perm("write");
		const $panel = this.panel(this.$charts, {
			title: __("Credit Limit"),
			subtitle:
				limit &&
				data?.credit.used != null &&
				__("{0} of {1} used", [this.short_money(used), this.short_money(limit)]),
			right:
				limit &&
				can_edit &&
				frappe.ui.button({
					icon: "pencil",
					variant: "ghost",
					tooltip: __("Edit credit limit"),
					onclick: () => this.edit_credit_limit(),
				}),
		});
		if (this.show_state($panel, this.ar, 280, __("Could not load receivables"))) return;
		if (data.credit.used == null) {
			this.empty_note($panel, __("Credit usage is unavailable with your permissions."), 180);
			return;
		}
		const $body = limit ? this.credit_donut(data, limit, used) : this.credit_empty(can_edit);
		$body.appendTo($panel);
	}

	credit_donut(data, limit, used) {
		const receivable = Math.min(Math.max(flt(data.outstanding.value), 0), used);
		const overdue = Math.min(Math.max(flt(data.overdue.value), 0), receivable);
		const donut = frappe.ui.donut({
			segments: [
				{ label: __("Overdue"), value: overdue, color: "var(--blue-600)" },
				{ label: __("Not due"), value: receivable - overdue, color: "var(--blue-400)" },
				{ label: __("Unbilled orders"), value: used - receivable, color: "var(--green-400)" },
				{ label: __("Available"), value: Math.max(limit - used, 0), color: "var(--green-600)" },
			],
			center: {
				value: flt((used / limit) * 100, 1) + "%",
				label: __("used"),
			},
			format: (v) => this.short_money(v),
		});
		const $chart = $('<div class="co-chart">').append(donut);
		if (used > limit) {
			$('<div class="text-ink-red-7">')
				.text(__("Over credit limit by {0}", [this.money0(used - limit)]))
				.appendTo($chart);
		}
		return $chart;
	}

	credit_empty(can_edit) {
		return $('<div class="co-empty-state">').append(
			frappe.ui.empty_state({
				icon: "gauge",
				title: __("No credit limit"),
				description: __("Set one for {0} to check new orders and invoices against it.", [
					this.state.company,
				]),
				actions: can_edit
					? [{ label: __("Set Credit Limit"), onclick: () => this.edit_credit_limit() }]
					: [],
			})
		);
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

	edit_credit_limit() {
		if (this.frm.is_dirty()) {
			frappe.msgprint(__("Save or discard your other changes to this customer first."));
			return;
		}
		const company = this.state.company;
		const row = (this.frm.doc.credit_limits || []).find((r) => r.company === company);
		frappe.prompt(
			[
				{
					fieldname: "credit_limit",
					fieldtype: "Currency",
					label: __("Credit Limit"),
					default: flt(row?.credit_limit),
					description: __(
						"Applies to {0}. Set to 0 to use the Customer Group or Company credit limit, if set.",
						[company]
					),
				},
			],
			(values) => this.save_credit_limit(company, flt(values.credit_limit)),
			__("Set Credit Limit"),
			__("Save")
		);
	}

	save_credit_limit(company, limit) {
		const frm = this.frm;
		if (frm.is_dirty()) {
			frappe.msgprint(__("Save or discard your other changes to this customer first."));
			return;
		}
		let row = (frm.doc.credit_limits || []).find((r) => r.company === company);
		const previous = row?.credit_limit;
		const added = !row;
		if (!row) row = frm.add_child("credit_limits", { company });
		row.credit_limit = limit;
		frm.dirty();
		return frm.save(
			"Save",
			(response) => {
				if (!response.exc && !frm.is_dirty())
					frappe.show_alert({ message: __("Credit limit updated"), indicator: "green" });
			},
			null,
			() => {
				if (added) {
					frappe.model.clear_doc(row.doctype, row.name);
					frm.doc.credit_limits = frm.doc.credit_limits.filter((item) => item !== row);
				} else row.credit_limit = previous;
				frm.doc.__unsaved = 0;
				frm.refresh();
			}
		);
	}

	render_pipeline() {
		this.$pipeline.empty();
		this.section_head(this.$pipeline, { title: __("Open Pipeline") });
		if (this.sales.loading) {
			const items = this.pipeline_specs({}).map((s) => ({ label: s.label, loading: true }));
			frappe.ui.stat_cards({ items }).appendTo(this.$pipeline);
			return;
		}
		const pl = (this.sales.data && this.sales.data.pipeline) || {};
		const specs = this.pipeline_specs(pl).filter((s) => s.data);
		if (!specs.length) {
			this.empty_note(this.$pipeline, __("Could not load sales"), 0).addClass("co-error");
			return;
		}

		const items = specs.map((s) => ({
			label: s.label,
			value: this.money0(s.data.value),
			caption: s.data.count ? s.caption(s.data) : __("None open"),
			onclick: () => this.list_route(s.route[0], s.route[1]),
		}));
		frappe.ui.stat_cards({ items }).appendTo(this.$pipeline);

		if (pl.delivery && pl.billing && pl.delivery.count && pl.billing.count) {
			$('<div class="co-note">')
				.text(__("The same order can appear under both Pending Delivery and Pending Billing."))
				.appendTo(this.$pipeline);
		}
	}

	pipeline_specs(pl) {
		const name = this.frm.doc.name;
		const company = this.state.company;
		const open_orders = {
			customer: name,
			company,
			docstatus: 1,
			status: ["not in", CLOSED_ORDER_STATUS],
		};
		const specs = [];
		if (frappe.model.can_read("Quotation"))
			specs.push({
				label: __("Open Quotations"),
				data: pl.quotations,
				caption: (d) => COUNT.quotations(d.count),
				route: ["Quotation", { quotation_to: "Customer", party_name: name, company, status: "Open" }],
			});
		if (frappe.model.can_read("Sales Order"))
			specs.push(
				{
					label: __("Pending Delivery"),
					data: pl.delivery,
					caption: (d) =>
						[COUNT.orders(d.count), d.past_due && __("{0} past promised date", [d.past_due])]
							.filter(Boolean)
							.join(" · "),
					route: [
						"Sales Order",
						{ ...open_orders, per_delivered: ["<", 100], skip_delivery_note: 0 },
					],
				},
				{
					label: __("Pending Billing"),
					data: pl.billing,
					caption: (d) => COUNT.orders(d.count) + " · " + __("not fully billed"),
					route: ["Sales Order", { ...open_orders, per_billed: ["<", 100] }],
				}
			);
		if (this.accounts)
			specs.push({
				label: __("Unpaid Invoices"),
				data: pl.invoices,
				caption: (d) =>
					[COUNT.invoices(d.count), d.overdue && __("{0} overdue", [d.overdue])]
						.filter(Boolean)
						.join(" · "),
				route: [
					"Sales Invoice",
					{
						customer: name,
						company,
						docstatus: 1,
						is_return: 0,
						outstanding_amount: [">", 0],
					},
				],
			});
		return specs;
	}

	build_recent() {
		this.section_head(this.$recent, {
			title: __("Recent Transactions"),
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
				options: TXN_TYPES.map((t) => (t === "All" ? "All Document Types" : t)).join("\n"),
			},
			render_input: true,
			only_input: true,
		});
		control.refresh();
		control.set_value("All Document Types");
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
				{ label: __("Receivable"), render: (row) => me.outstanding_cell(row) },
			],
			get_data() {
				if (!me.state.company) return Promise.resolve([]);
				return frappe.xcall(OVERVIEW_METHOD + ".get_customer_transactions", {
					customer: me.frm.doc.name,
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

	open_ar() {
		frappe.route_options = {
			party_type: "Customer",
			party: this.frm.doc.name,
			company: this.state.company,
		};
		frappe.set_route("query-report", "Accounts Receivable");
	}
	open_reconciliation() {
		frappe.route_options = {
			company: this.state.company,
			party_type: "Customer",
			party: this.frm.doc.name,
		};
		frappe.set_route("Form", "Payment Reconciliation");
	}
	open_analytics() {
		const range = (this.sales.data && this.sales.data.period_range) || {};
		frappe.route_options = {
			tree_type: "Customer",
			entity: [this.frm.doc.name],
			doc_type: "Sales Invoice",
			company: this.state.company,
			from_date: range.from_date,
			to_date: range.to_date,
			value_quantity: "Value",
		};
		frappe.set_route("query-report", "Sales Analytics");
	}
	list_route(doctype, filters) {
		frappe.route_options = filters;
		frappe.set_route("List", doctype);
	}
};
