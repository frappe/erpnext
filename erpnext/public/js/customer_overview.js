const CLOSED_ORDER_STATUS = ["Closed", "Completed", "On Hold"];
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

erpnext.CustomerOverview = class CustomerOverview extends erpnext.PartyOverview {
	constructor(frm) {
		super(frm, {
			party_type: "Customer",
			method_path: "erpnext.selling.doctype.customer.customer_overview",
			invoice_doctype: "Sales Invoice",
			balances_method: "get_customer_receivables",
			ledger_report: "Accounts Receivable",
			period_label: __("Sales Period"),
			transaction_types: ["Sales Invoice", "Sales Order", "Payment Entry"],
			outstanding_label: __("Receivable"),
			overview_error: __("Could not load sales"),
			balances_error: __("Could not load receivables"),
			empty_doctypes: ["Quotation", "Sales Order"],
			empty_description: __(
				"Quotations, orders, invoices and payments for this customer will show up here."
			),
		});
	}

	position_cards() {
		return [this.net_sales_card(), ...this.receivable_cards()];
	}

	net_sales_card() {
		const card = { label: __("Net Sales") };
		const sales = this.overview || { loading: true };
		if (sales.loading) return { ...card, loading: true };
		const p = sales.data && sales.data.position && sales.data.position.net_sales;
		if (sales.error || sales.data?.errors?.position)
			return { ...card, value: "—", caption: this.overview_error };
		if (!p) return { ...card, value: null };
		return {
			...card,
			value: this.money0(p.value),
			delta: this.delta_opts(p, __("since last year")),
			caption: p.count ? COUNT.invoices(p.count) : __("No invoices in this period"),
			onclick: () => this.open_analytics(),
		};
	}

	receivable_cards() {
		const ar = this.balances || { loading: true };
		const labels = [__("Receivable"), __("Overdue"), __("Advances")];
		if (ar.loading) return labels.map((label) => ({ label, loading: true }));
		if (ar.none) return [];
		if (ar.error) return labels.map((label) => ({ label, value: "—", caption: this.balances_error }));
		if (!ar.data) return labels.map((label) => ({ label, value: null }));
		const { outstanding, overdue, advances } = ar.data;
		return [
			{
				label: labels[0],
				value: this.money0(outstanding.value),
				caption: this.outstanding_sub(outstanding) || __("Nothing unpaid"),
				onclick: () => this.open_ledger(),
			},
			{
				label: labels[1],
				value: this.money0(overdue.value),
				delta: this.delta_opts(overdue, __("since last month")),
				caption: flt(overdue.value) ? null : __("Nothing overdue"),
				onclick: () => this.open_ledger(),
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
				onclick: () => this.open_ledger(),
			};
		const card = { label, value: this.money0(advances.value), onclick: () => this.open_ledger() };
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

	trend_spec() {
		const t = this.overview?.data?.trend;
		const notes = [];
		if (t?.average) notes.push(__("Avg {0}", [this.money0(t.average)]));
		if (t?.has_mtd) notes.push(__("{0} is month to date", [t.points[t.points.length - 1].label]));
		return {
			title: __("Monthly Sales Trend"),
			subtitle: __("Monthly, net of returns"),
			right: this.report_link(__("Sales Analytics"), () => this.open_analytics()),
			type: "line",
			colors: ["--blue-600"],
			empty_text: __("No sales in this period"),
			notes,
			data: t?.points.some((p) => flt(p.value)) && {
				labels: t.points.map((p) => p.label),
				titles: t.points.map((p) => p.title),
				datasets: [{ name: __("Net Sales"), values: t.points.map((p) => flt(p.value)) }],
			},
		};
	}

	render_charts(key) {
		if (key !== "balances") return;
		this.$charts.empty().toggle(!!this.accounts && !this.balances?.none);
		if (!this.accounts || this.balances?.none) return;
		this.render_ageing({
			title: __("Receivables Ageing"),
			subtitle: __("Unpaid invoices by due date"),
			note: (a) =>
				__("Overdue {0} · {1}% of unpaid invoices", [this.money0(a.overdue), flt(a.overdue_pct, 1)]),
		});
		this.render_credit();
	}

	render_credit() {
		const data = this.balances.data;
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
		if (this.show_state($panel, this.balances, 280, this.balances_error)) return;
		if (data.credit.used == null) {
			this.empty_note($panel, __("Credit usage is unavailable with your permissions."), 180);
			return;
		}
		if (!limit) {
			this.credit_empty(can_edit).appendTo($panel);
			return;
		}
		this.credit_donut($panel, data, limit, used);
	}

	credit_donut($panel, data, limit, used) {
		const receivable = Math.min(Math.max(flt(data.outstanding.value), 0), used);
		const overdue = Math.min(Math.max(flt(data.overdue.value), 0), receivable);
		const $chart = this.draw_donut($panel, {
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
		if (used > limit) {
			$('<div class="text-ink-red-7">')
				.text(__("Over credit limit by {0}", [this.money0(used - limit)]))
				.appendTo($chart);
		}
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
					empty: __("Nothing to deliver"),
					route: [
						"Sales Order",
						{ ...open_orders, per_delivered: ["<", 100], skip_delivery_note: 0 },
					],
				},
				{
					label: __("Pending Billing"),
					data: pl.billing,
					caption: (d) => COUNT.orders(d.count) + " · " + __("not fully billed"),
					empty: __("Nothing to bill"),
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
				empty: __("Nothing unpaid"),
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

	pipeline_note(pl) {
		if (pl.delivery && pl.billing && pl.delivery.count && pl.billing.count)
			return __("The same order can appear under both Pending Delivery and Pending Billing.");
	}

	open_analytics() {
		const range = this.overview?.data?.period_range || {};
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
};
