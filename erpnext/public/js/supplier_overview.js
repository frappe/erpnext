const COUNT = {
	bills: (n) => (n === 1 ? __("1 bill") : __("{0} bills", [n])),
	quotations: (n) => (n === 1 ? __("1 quotation") : __("{0} quotations", [n])),
	orders: (n) => (n === 1 ? __("1 order") : __("{0} orders", [n])),
	days_late: (n) => (n === 1 ? __("oldest 1 day late") : __("oldest {0} days late", [n])),
	reconcile: (n) =>
		n === 1 ? __("Reconcile with 1 unpaid bill") : __("Reconcile with {0} unpaid bills", [n]),
	unapplied: (n) =>
		n === 1 ? __("Not applied to 1 unpaid bill") : __("Not applied to {0} unpaid bills", [n]),
	days_to_pay: (n) => (n === 1 ? __("1 day to pay") : __("{0} days to pay", [n])),
};

frappe.ui.form.on("Supplier", {
	refresh(frm) {
		if (frm.is_new() || !frm.get_field("overview_html")) return;
		if (!frm.supplier_overview) frm.supplier_overview = new erpnext.SupplierOverview(frm);
		frm.supplier_overview.refresh();
	},
	on_tab_change(frm) {
		frm.supplier_overview?.show();
	},
});

erpnext.SupplierOverview = class SupplierOverview extends erpnext.PartyOverview {
	constructor(frm) {
		super(frm, {
			party_type: "Supplier",
			method_path: "erpnext.buying.doctype.supplier.supplier_overview",
			invoice_doctype: "Purchase Invoice",
			balances_method: "get_supplier_payables",
			ledger_report: "Accounts Payable",
			period_label: __("Purchase Period"),
			transaction_types: ["Purchase Invoice", "Purchase Order", "Purchase Receipt", "Payment Entry"],
			outstanding_label: __("Payable"),
			overview_error: __("Could not load purchases"),
			balances_error: __("Could not load payables"),
			empty_doctypes: ["Request for Quotation", "Purchase Order"],
			empty_description: __(
				"Quotations, orders, bills and payments for this supplier will show up here."
			),
		});
	}

	position_cards() {
		return [this.net_purchases_card(), ...this.payable_cards()];
	}

	net_purchases_card() {
		const card = { label: __("Net Purchases") };
		const overview = this.overview || { loading: true };
		if (overview.loading) return { ...card, loading: true };
		const p = overview.data?.position?.net_purchases;
		if (overview.error || overview.data?.errors?.position)
			return { ...card, value: "—", caption: this.overview_error };
		if (!p) return { ...card, value: null };
		return {
			...card,
			value: this.money0(p.value),
			delta: this.delta_opts(p, __("since last year")),
			caption: p.count ? COUNT.bills(p.count) : __("No bills in this period"),
			onclick: () => this.open_analytics(),
		};
	}

	payable_cards() {
		const ap = this.balances || { loading: true };
		const labels = [__("Payable"), __("Overdue"), __("Advances Paid")];
		if (ap.loading) return labels.map((label) => ({ label, loading: true }));
		if (ap.none) return [];
		if (ap.error) return labels.map((label) => ({ label, value: "—", caption: this.balances_error }));
		const { outstanding, overdue, advances } = ap.data;
		return [
			{
				label: labels[0],
				value: this.money0(outstanding.value),
				caption:
					[
						outstanding.unpaid_count && __("{0} unpaid", [outstanding.unpaid_count]),
						outstanding.days_to_pay && COUNT.days_to_pay(outstanding.days_to_pay),
					]
						.filter(Boolean)
						.join(" · ") || __("Nothing unpaid"),
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
			return { label, value: "—", caption: __("Not available with your permissions") };
		const card = { label, value: this.money0(advances.value), onclick: () => this.open_ledger() };
		if (!flt(advances.value)) return { ...card, caption: __("No unapplied payments") };
		if (!unpaid_count) return { ...card, caption: __("Debit balance, no bills to apply it to") };
		if (!frappe.model.can_write("Payment Reconciliation"))
			return { ...card, caption: COUNT.unapplied(unpaid_count) };
		return {
			...card,
			caption: COUNT.reconcile(unpaid_count),
			onclick: () => this.open_reconciliation(),
		};
	}

	trend_spec() {
		const t = this.overview?.data?.trend;
		const notes =
			t?.purchased > 0
				? [
						__("Paid {0} of {1} invoiced · {2}%", [
							this.short_money(t.paid),
							this.short_money(t.purchased),
							Math.round((t.paid / t.purchased) * 100),
						]),
				  ]
				: [];
		return {
			title: __("Purchases vs Payments"),
			subtitle: __("Invoiced and paid each month"),
			right: this.report_link(__("Purchase Analytics"), () => this.open_analytics()),
			type: "bar",
			height: 280,
			colors: ["--co-series-1", "--co-series-2"],
			notes,
			data: t?.points.some((p) => flt(p.purchased) || flt(p.paid)) && {
				labels: t.points.map((p) => p.label),
				titles: t.points.map((p) => p.title),
				datasets: [
					{ name: __("Purchased"), values: t.points.map((p) => flt(p.purchased)) },
					{ name: __("Paid"), values: t.points.map((p) => flt(p.paid)) },
				],
			},
		};
	}

	render_charts(key) {
		if (key !== "overview") {
			this.remove_panel(this.$age_panel);
			this.$age_panel =
				this.accounts && !this.balances?.none
					? this.render_ageing({
							title: __("Payables Ageing"),
							subtitle: __("Unpaid bills by due date"),
							note: (a) =>
								__("Overdue {0} · {1}% of unpaid bills", [
									this.money0(a.overdue),
									flt(a.overdue_pct, 1),
								]),
					  })
					: null;
			this.$age_panel?.prependTo(this.$charts);
		}
		if (key !== "balances") {
			this.remove_panel(this.$delivery_panel);
			this.$delivery_panel =
				this.overview && this.overview.data?.delivery !== null ? this.render_delivery() : null;
		}
		this.$charts.toggle(this.$charts.children().length > 0);
	}

	render_delivery() {
		const d = this.overview.data?.delivery;
		const $panel = this.panel(this.$charts, {
			title: __("Delivery Performance"),
			subtitle: d?.lines
				? d.orders === 1
					? __("Across 1 purchase order")
					: __("Across {0} purchase orders", [d.orders])
				: __("Order lines received by their due date"),
			right:
				d?.scorecard &&
				this.report_link(__("Scorecard"), () =>
					frappe.set_route("Form", "Supplier Scorecard", this.frm.doc.name)
				),
		});
		if (this.show_state($panel, this.overview, 280, this.overview_error, "delivery")) return $panel;
		if (!d.lines) {
			$panel.remove();
			return null;
		}
		this.draw_donut($panel, {
			segments: [
				{ label: __("On time"), value: d.on_time, color: "var(--green-600)" },
				{ label: __("Received late"), value: d.late, color: "var(--blue-400)" },
				{ label: __("Overdue"), value: d.overdue, color: "var(--blue-600)" },
			],
			center: { value: d.lines, label: d.lines === 1 ? __("delivery") : __("deliveries") },
		});
		$('<div class="co-note">')
			.text(__("{0}% delivered on time", [Math.round(d.on_time_rate)]))
			.appendTo($panel);
		return $panel;
	}

	pipeline_specs(pl) {
		const name = this.frm.doc.name;
		const company = this.state.company;
		const specs = [];
		if (frappe.model.can_read("Supplier Quotation"))
			specs.push({
				label: __("Open Supplier Quotations"),
				data: pl.quotations,
				caption: (d) =>
					[COUNT.quotations(d.count), d.expiring && __("{0} expiring this week", [d.expiring])]
						.filter(Boolean)
						.join(" · "),
				route: [
					"Supplier Quotation",
					{
						supplier: name,
						company,
						docstatus: 1,
						status: ["in", ["Submitted", "Partially Ordered"]],
					},
				],
			});
		if (frappe.model.can_read("Purchase Order"))
			specs.push(
				{
					label: __("Pending Receipt"),
					data: pl.receipt,
					caption: (d) =>
						[
							COUNT.orders(d.count),
							d.next_due && __("next due {0}", [moment(d.next_due).format("D MMM")]),
						]
							.filter(Boolean)
							.join(" · "),
					empty: __("Nothing to receive"),
					route: ["Purchase Order", { company, name: ["in", pl.receipt?.orders || []] }],
				},
				{
					label: __("Pending Billing"),
					data: pl.billing,
					caption: (d) => COUNT.orders(d.count) + " · " + __("received, not billed"),
					empty: __("Nothing to bill"),
					route: ["Purchase Order", { company, name: ["in", pl.billing?.orders || []] }],
				},
				{
					label: __("Overdue Deliveries"),
					data: pl.late,
					caption: (d) =>
						[COUNT.orders(d.count), d.days_late && COUNT.days_late(d.days_late)]
							.filter(Boolean)
							.join(" · "),
					empty: __("Nothing overdue"),
					route: ["Purchase Order", { company, name: ["in", pl.late?.orders || []] }],
				}
			);
		return specs;
	}

	pipeline_note(pl) {
		if (pl.receipt?.count && (pl.billing?.count || pl.late?.count))
			return __(
				"The same order can appear under Pending Receipt, Pending Billing and Overdue Deliveries."
			);
	}

	open_analytics() {
		const range = this.overview?.data?.period_range || {};
		frappe.route_options = {
			tree_type: "Supplier",
			entity: [this.frm.doc.name],
			doc_type: "Purchase Invoice",
			company: this.state.company,
			from_date: range.from_date,
			to_date: range.to_date,
			value_quantity: "Value",
		};
		frappe.set_route("query-report", "Purchase Analytics");
	}
};
