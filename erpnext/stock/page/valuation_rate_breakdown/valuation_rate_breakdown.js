frappe.pages["valuation-rate-breakdown"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Valuation Rate Breakdown"),
		single_column: true,
	});

	frappe.valuation_rate_breakdown = new erpnext.ValuationRateBreakdown(page);
};

frappe.pages["valuation-rate-breakdown"].on_page_show = function () {
	const explainer = frappe.valuation_rate_breakdown;
	const options = frappe.route_options;
	if (!explainer || !options || !options.item_code || !options.warehouse) return;

	frappe.route_options = null;
	explainer.open(options.item_code, options.warehouse, options.entry);
};

erpnext.ValuationRateBreakdown = class ValuationRateBreakdown {
	constructor(page) {
		this.page = page;
		this.body = $(this.page.body);
		this.body.append(`${this.styles()}<div class="vrb"></div>`);
		this.container = this.body.find(".vrb");
		this.make_fields();
		this.render_blank_state();
	}

	make_fields() {
		const on_change = () => this.on_filter_change();
		this.item_field = this.page.add_field({
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: () => ({ filters: { is_stock_item: 1 } }),
			change: on_change,
		});
		this.warehouse_field = this.page.add_field({
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: () => ({ filters: { is_group: 0 } }),
			change: on_change,
		});
	}

	on_filter_change() {
		if (this.setting_filters) return;
		const item_code = this.item_field.get_value();
		const warehouse = this.warehouse_field.get_value();
		if (item_code && warehouse) {
			this.load({ item_code, warehouse });
		} else {
			this.key = null;
			this.render_blank_state();
		}
	}

	open(item_code, warehouse, entry) {
		this.setting_filters = true;
		Promise.all([this.item_field.set_value(item_code), this.warehouse_field.set_value(warehouse)]).then(
			() => {
				this.setting_filters = false;
				this.load({ item_code, warehouse, upto: entry });
			}
		);
	}

	load(args) {
		const key = `${args.item_code}::${args.warehouse}::${args.upto || ""}`;
		this.key = key;
		this.focus = args.upto || null;
		this.render_skeleton();
		this.fetch(args).then(
			(data) => {
				if (this.key !== key) return;
				this.data = data;
				this.render();
			},
			() => {
				if (this.key === key) this.render_failed(args);
			}
		);
	}

	load_earlier() {
		const first = this.data.entries[0];
		const key = this.key;
		return this.fetch({
			item_code: this.data.item.item_code,
			warehouse: this.data.warehouse,
			before: first.name,
		}).then(
			(data) => {
				if (this.key !== key) return;
				this.data.entries = data.entries.concat(this.data.entries);
				this.data.opening = data.opening;
				this.data.has_earlier = data.has_earlier;
				this.render(first.name);
			},
			() => frappe.show_alert({ message: __("Could not load earlier entries"), indicator: "red" })
		);
	}

	fetch(args) {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: "erpnext.stock.page.valuation_rate_breakdown.valuation_rate_breakdown.get_valuation_steps",
				args,
				callback: (r) => resolve(r.message),
				error: reject,
			});
		});
	}

	render_failed(args) {
		this.container.empty().append(
			frappe.ui.empty_state({
				icon: "circle-alert",
				title: __("Could not load the breakdown"),
				description: __("Something went wrong while working out the rates."),
				actions: [{ label: __("Try again"), icon: "refresh-cw", onclick: () => this.load(args) }],
			})
		);
	}

	render_blank_state() {
		this.container.empty().append(
			frappe.ui.empty_state({
				icon: "calculator",
				title: __("Choose an item and a warehouse"),
				description: __(
					"See how the stock value and the value per unit were worked out, one entry at a time."
				),
			})
		);
	}

	render_skeleton() {
		const block = (width, height) => frappe.ui.skeleton.html({ width, height });
		const step = `
			<div class="vrb-step">
				<div class="vrb-rail">${block("32px", "32px")}</div>
				<div class="vrb-step-body">
					${block("50%", "20px")}
					<div class="vrb-gap"></div>
					${block("100%", "128px")}
				</div>
			</div>
		`;
		this.container.html(`<div class="vrb-card">${block("100%", "176px")}</div>${step.repeat(3)}`);
	}

	render(scroll_to) {
		const data = this.data;
		this.container.empty();
		if (!data.entries.length) {
			this.container.append(this.no_entries_state());
			return;
		}
		if (data.repost_pending) {
			this.container.append(this.repost_alert());
		}
		this.container.append(this.summary());
		const backdated = this.backdated_alert();
		if (backdated) this.container.append(backdated);
		this.container.append(`<div class="vrb-section-title">${__("How we got here, step by step")}</div>`);
		this.container.append(this.timeline());
		this.scroll_to(scroll_to || this.focus);
	}

	no_entries_state() {
		return frappe.ui.empty_state({
			icon: "package-open",
			title: __("No stock movements"),
			description: __("There are no stock entries for {0} in {1}.", [
				this.data.item.item_code,
				this.data.warehouse,
			]),
		});
	}

	repost_alert() {
		return frappe.ui.alert({
			title: __("Stock values are being recalculated"),
			description: __(
				"A backdated entry changed this item's history. The rates below may change once the recalculation finishes."
			),
			theme: "amber",
		});
	}

	summary() {
		const item = this.data.item;
		const card = $(`
			<div class="vrb-card">
				<div class="vrb-summary-head">
					<div class="vrb-summary-text">
						<div class="vrb-item ellipsis">
							${frappe.utils.escape_html(item.item_name || item.item_code)}
							<span class="vrb-muted">${frappe.utils.escape_html(item.item_code)}</span>
						</div>
						<div class="vrb-lead">${this.summary_sentence()}</div>
					</div>
					${frappe.ui.badge.html({ label: this.method_label(), theme: "blue", size: "lg" })}
				</div>
				${this.figures_html()}
				${this.guide_html()}
			</div>
		`);
		card.find(".vrb-guide-toggle").on("click", () => card.find(".vrb-guide").toggleClass("is-open"));
		return card;
	}

	summary_sentence() {
		const last = this.last_entry();
		const date = frappe.datetime.str_to_user(last.posting_date);
		const warehouse = frappe.utils.escape_html(this.data.warehouse);
		if (last.qty_after <= 0) {
			return __("On {0}, {1} has {2} in stock, valued at {3}.", [
				date,
				warehouse,
				this.b(this.qty(last.qty_after)),
				this.b(this.money(last.value_after)),
			]);
		}
		return __("On {0}, {1} holds {2} worth {3}, so each unit is valued at {4}.", [
			date,
			warehouse,
			this.b(this.qty(last.qty_after)),
			this.b(this.money(last.value_after)),
			this.b(this.money(last.rate_after)),
		]);
	}

	figures_html() {
		const last = this.last_entry();
		const figure = (label, value, align) => `
			<div class="vrb-figure ${align}">
				<div class="vrb-figure-label">${label}</div>
				<div class="vrb-figure-value ellipsis">${value}</div>
			</div>
		`;
		return `
			<div class="vrb-figures">
				${figure(__("Units in stock"), this.qty(last.qty_after), "")}
				${figure(__("Stock value"), this.money(last.value_after), "text-right")}
				${figure(__("Value per unit"), this.money(last.rate_after), "text-right")}
			</div>
		`;
	}

	method_label() {
		const labels = {
			batch: __("Valued batch by batch"),
			serial: __("Valued per serial number"),
		};
		return labels[this.data.item.valued_by] || __("Valued by {0}", [__(this.data.item.valuation_method)]);
	}

	guide_html() {
		const item = this.data.item;
		const guide = this.method_guides()[item.valued_by || item.valuation_method];
		if (!guide) return "";
		const steps = guide.steps
			.map((step, i) => `<li><span class="vrb-step-no">${i + 1}</span><span>${step}</span></li>`)
			.join("");
		return `
			<div class="vrb-guide">
				<button class="vrb-guide-toggle">
					${frappe.utils.icon("lightbulb", "sm")}
					<span class="vrb-guide-title">${__("How it works:")}</span>
					<span class="vrb-guide-short ellipsis">${guide.short}</span>
					<span class="vrb-guide-chevron">${frappe.utils.icon("chevron-down", "sm")}</span>
				</button>
				<ol class="vrb-guide-steps">${steps}</ol>
			</div>
		`;
	}

	method_guides() {
		const own_lot = __("Every receipt is kept as its own lot, with its own rate.");
		const lots_left = __("The value per unit is the value of the lots left, divided by the units left.");
		return {
			batch: {
				short: __("Each batch keeps its own average rate."),
				steps: [
					__("When a batch comes in, its value is added to that batch only."),
					__(
						"When stock goes out, each batch leaves at its own average: the batch's value divided by its units."
					),
					__(
						"A batch that does not keep its own rate goes out at the value per unit of the whole warehouse."
					),
				],
			},
			serial: {
				short: __("Each serial number keeps the rate it came in at."),
				steps: [
					__("When a serial number comes in, it keeps its own rate."),
					__("When it goes out, it leaves at that same rate."),
					__(
						"The value per unit of the warehouse is the value of all serial numbers divided by the units."
					),
				],
			},
			"Moving Average": {
				short: __("All units share one average rate."),
				steps: [
					__(
						"When stock comes in, its value is added to what you already have, and the total is divided by the new quantity."
					),
					__("When stock goes out, it leaves at that average, so the average does not move."),
					__("A purchase return goes out at the rate on the receipt it reverses."),
				],
			},
			FIFO: {
				short: __("First in, first out. The oldest lot is used first."),
				steps: [
					own_lot,
					__("When stock goes out, units are taken from the oldest lot first."),
					lots_left,
				],
			},
			LIFO: {
				short: __("Last in, first out. The newest lot is used first."),
				steps: [
					own_lot,
					__("When stock goes out, units are taken from the newest lot first."),
					lots_left,
				],
			},
			"Standard Cost": {
				short: __("Every unit is valued at one fixed standard cost."),
				steps: [
					__(
						"The purchase rate does not change the stock value. Each unit is kept at the standard cost."
					),
					__("When stock goes out, it also leaves at the standard cost."),
					__(
						"The difference from the purchase rate is booked to the Purchase Price Variance account."
					),
				],
			},
		};
	}

	timeline() {
		const list = $('<div class="vrb-timeline"></div>');
		const entries = this.data.entries;
		list.append(this.start_step());
		entries.forEach((entry, i) => list.append(this.entry_step(entry, i === entries.length - 1)));
		return list;
	}

	start_step() {
		const opening = this.data.opening;
		const title = opening.qty
			? __("Start: {0} worth {1}", [this.qty(opening.qty), this.money(opening.value)])
			: __("Start: no stock in this warehouse");
		const hint = this.data.has_earlier
			? __("Earlier entries are hidden. The explanation picks up from here.")
			: __("The explanation starts from the last time stock was zero or was counted.");
		const step = $(`
			<div class="vrb-step">
				<div class="vrb-rail">
					<div class="vrb-dot is-gray">${frappe.utils.icon("flag", "sm")}</div>
					<div class="vrb-line"></div>
				</div>
				<div class="vrb-step-body vrb-start">
					<div class="vrb-start-title">${title}</div>
					<div class="vrb-muted">${hint}</div>
				</div>
			</div>
		`);
		if (this.data.has_earlier) step.find(".vrb-start").append(this.earlier_button());
		return step;
	}

	earlier_button() {
		return $('<div class="vrb-earlier"></div>').append(
			frappe.ui.button({
				label: __("Show earlier entries"),
				variant: "subtle",
				icon: "history",
				onclick: () => this.load_earlier(),
			})
		);
	}

	entry_step(entry, is_last) {
		const focus = entry.name === this.focus;
		const step = $(`
			<div class="vrb-step" data-entry="${frappe.utils.escape_html(entry.name)}">
				<div class="vrb-rail">
					${this.dot_html(entry)}
					${is_last ? "" : '<div class="vrb-line"></div>'}
				</div>
				<div class="vrb-step-body">
					${this.entry_header_html(entry)}
					<div class="vrb-card vrb-explain${focus ? " is-focus" : ""}">
						${focus ? this.opened_html() : ""}
						${this.entered_late_html(entry)}
						<div class="vrb-lead">${this.headline(entry)}</div>
						${this.parts_html(entry)}
						${this.math_html(entry)}
						${this.is_queue() ? this.lots_html(entry) : ""}
						${this.result_html(entry)}
					</div>
				</div>
			</div>
		`);
		for (const note of [this.rate_note(entry), this.changed_note(entry)]) {
			if (note) step.find(".vrb-explain").append(frappe.ui.alert(note));
		}
		return step;
	}

	opened_html() {
		const icon = frappe.utils.icon("mouse-pointer-click", "xs");
		return `<div class="vrb-opened">${icon} ${__("You opened this entry from the Stock Ledger")}</div>`;
	}

	dot_html(entry) {
		const dots = {
			in: ["arrow-down-to-line", "is-in"],
			out: ["arrow-up-from-line", "is-out"],
			reconciliation: ["clipboard-check", "is-gray"],
			revaluation: ["scale", "is-gray"],
		};
		const [icon, css] = dots[entry.kind];
		return `<div class="vrb-dot ${css}">${frappe.utils.icon(
			entry.is_return ? "undo-2" : icon,
			"sm"
		)}</div>`;
	}

	entry_header_html(entry) {
		const date = frappe.datetime.str_to_user(entry.posting_date);
		const time = moment(entry.posting_time, "HH:mm:ss").format("HH:mm");
		return `
			<div class="vrb-entry-head">
				<span class="vrb-date">${date} ${time}</span>
				<span class="vrb-voucher ellipsis">${this.voucher_label(entry)}</span>
				<span class="vrb-doc ellipsis">${this.doc_link(entry.voucher_type, entry.voucher_no)}</span>
				${entry.later_dated_count ? frappe.ui.badge.html({ label: __("Backdated"), theme: "amber" }) : ""}
				${this.qty_badge(entry)}
			</div>
		`;
	}

	voucher_label(entry) {
		if (!entry.is_return) return __(entry.voucher_type);
		const labels = {
			"Purchase Receipt": __("Purchase Return"),
			"Purchase Invoice": __("Purchase Return"),
			"Subcontracting Receipt": __("Subcontracting Return"),
			"Delivery Note": __("Sales Return"),
			"Sales Invoice": __("Sales Return"),
		};
		return labels[entry.voucher_type] || __(entry.voucher_type);
	}

	qty_badge(entry) {
		if (entry.kind === "reconciliation") return frappe.ui.badge.html({ label: __("Stock count") });
		if (entry.kind === "revaluation") return frappe.ui.badge.html({ label: __("Value change") });
		const sign = entry.qty > 0 ? "+" : "−";
		return frappe.ui.badge.html({
			label: `${sign}${this.number(Math.abs(entry.qty))}`,
			theme: entry.qty > 0 ? "green" : "red",
		});
	}

	headline(entry) {
		const headlines = {
			reconciliation: () => this.reconciliation_headline(entry),
			revaluation: () => this.revaluation_headline(entry),
			in: () => this.inward_headline(entry),
			out: () => this.outward_headline(entry),
		};
		return headlines[entry.kind]();
	}

	reconciliation_headline(entry) {
		const text = __("Stock was counted and set to {0} at {1} each.", [
			this.b(this.qty(entry.qty_after)),
			this.b(this.money(entry.rate_after)),
		]);
		return this.is_queue() ? `${text} ${__("Earlier lots are replaced by this one lot.")}` : text;
	}

	revaluation_headline(entry) {
		return __("No units moved, but the stock value changed by {0}.", [
			this.b(this.signed_money(entry.value_change)),
		]);
	}

	inward_headline(entry) {
		const qty = this.b(this.qty(entry.qty));
		const rate = this.b(this.money(entry.rate));
		const lead = entry.is_return
			? __("Received {0} back against {1} at {2}.", [qty, this.return_link(entry), rate])
			: __("Received {0} at {1}.", [qty, rate]);
		const parts = [lead, entry.is_return ? this.return_in_note(entry) : this.inward_reason(entry)];
		if (!entry.rate) parts.push(__("This receipt has a zero rate, so it adds no value."));
		return parts.filter(Boolean).join(" ");
	}

	inward_reason(entry) {
		const own_rate = {
			batch: __("Each batch keeps its own rate. The figures below are for all batches together."),
			serial: __(
				"Each serial number keeps its own rate. The figures below are for all serial numbers together."
			),
		}[this.data.item.valued_by];
		if (own_rate) return own_rate;
		if (this.data.item.valuation_method === "Standard Cost") {
			return __("Stock is kept at the standard cost, {0} per unit.", [this.money(entry.rate_after)]);
		}
		if (entry.qty_before < 0) return __("Stock was below zero, so this first covers the shortage.");
		if (!entry.qty_before) {
			return __("There was no stock before, so the value per unit is simply {0}.", [
				this.money(entry.rate),
			]);
		}
		if (this.is_queue()) return __("It is kept as a new lot.");
		return __("It is blended with the {0} already in stock.", [this.qty(entry.qty_before)]);
	}

	return_in_note(entry) {
		if (entry.original_rate == null) return "";
		if (this.same(entry.rate, entry.original_rate)) return __("That is the same rate it went out at.");
		return __("It went out at {0}.", [this.money(entry.original_rate)]);
	}

	outward_headline(entry) {
		const lead = this.outward_lead(entry);
		const rate = this.b(this.money(entry.rate));
		if (this.data.item.valued_by) return this.own_rate_headline(entry, lead, rate);
		if (this.is_queue()) return `${lead}. ${this.lots_used_note(entry)}`;
		if (this.data.item.valuation_method === "Standard Cost") {
			return __("{0} at the standard cost, {1}.", [lead, rate]);
		}
		if (this.at_original_rate(entry)) return __("{0} at {1}, the rate it came in at.", [lead, rate]);
		return __("{0} at the current value per unit, {1}.", [lead, rate]);
	}

	own_rate_headline(entry, lead, rate) {
		if (this.data.item.valued_by === "serial") {
			return __("{0}. Each serial number goes out at the rate it came in at, {1} on average.", [
				lead,
				rate,
			]);
		}
		if ((entry.parts || []).some((part) => part.own_rate)) {
			return __("{0}. Each batch goes out at its own rate, {1} on average.", [lead, rate]);
		}
		return __("{0} at the current value per unit, {1}.", [lead, rate]);
	}

	outward_lead(entry) {
		const qty = this.b(this.qty(Math.abs(entry.qty)));
		if (entry.is_return) return __("Returned {0} against {1}", [qty, this.return_link(entry)]);
		if (["Delivery Note", "Sales Invoice"].includes(entry.voucher_type)) {
			return __("Delivered {0}", [qty]);
		}
		return __("Issued {0}", [qty]);
	}

	lots_used_note(entry) {
		const used = entry.used_lots || [];
		if (!used.length) {
			return __("There was no stock left to take from, so it goes out at {0}.", [
				this.b(this.money(entry.rate)),
			]);
		}
		const list = used.map(([qty, rate]) => __("{0} at {1}", [this.qty(qty), this.money(rate)]));
		return __("{0}: {1}.", [this.lot_reason(entry, used), this.b(this.join_list(list))]);
	}

	lot_reason(entry, used) {
		const matches_original =
			entry.is_return &&
			entry.original_rate != null &&
			used.every(([, rate]) => this.same(rate, entry.original_rate));
		if (matches_original) return __("A return takes the lot that came in at the same rate");
		return this.data.item.valuation_method === "LIFO"
			? __("Under LIFO the newest lot goes out first")
			: __("Under FIFO the oldest lot goes out first");
	}

	math_html(entry) {
		const change_labels = {
			in: __("In"),
			out: __("Out"),
			reconciliation: __("Count"),
			revaluation: __("Change"),
		};
		const qty_change = entry.qty_after - entry.qty_before;
		const value_change = entry.value_after - entry.value_before;
		const rows = [
			this.math_row(__("Before"), entry.qty_before, entry.rate_before, entry.value_before),
			this.math_row(change_labels[entry.kind], qty_change, entry.rate, value_change, "change"),
			this.math_row(__("After"), entry.qty_after, entry.rate_after, entry.value_after, "total"),
		];
		return `<div class="vrb-math">${rows.join("")}</div>`;
	}

	math_row(label, qty, rate, value, type) {
		const change = type === "change";
		const tone = change ? (qty > 0 || (!qty && value > 0) ? "vrb-in" : "vrb-out") : "";
		const show_rate = change ? qty && rate : qty;
		return `
			<div class="vrb-math-row${type === "total" ? " is-total" : ""}">
				<span class="vrb-muted">${label}</span>
				<span class="text-right ${tone}">${change ? this.signed_qty(qty) : this.qty(qty)}</span>
				<span class="text-right vrb-muted">${show_rate ? `× ${this.money(rate)}` : "—"}</span>
				<span class="text-right ${tone}">${change ? this.signed_money(value) : this.money(value)}</span>
			</div>
		`;
	}

	lots_html(entry) {
		const before = entry.lots_before || [];
		const after = entry.lots_after || [];
		if (!before.length && !after.length) return "";
		return `
			<div class="vrb-lots">
				<span class="vrb-muted">${__("Lots before")}</span>
				<div class="vrb-chips">${this.before_chips(before, entry.used_lots || [])}</div>
				<span class="vrb-muted">${__("Lots after")}</span>
				<div class="vrb-chips">${this.after_chips(after, entry.added_lots || [])}</div>
			</div>
		`;
	}

	before_chips(lots, used) {
		if (!lots.length) return `<span class="vrb-muted">${__("None")}</span>`;
		const left = {};
		for (const [qty, rate] of used) left[rate] = (left[rate] || 0) + qty;
		const chips = lots.map(([qty, rate]) => {
			const taken = Math.min(left[rate] || 0, qty);
			left[rate] = (left[rate] || 0) - taken;
			if (!taken) return this.chip(qty, rate, "");
			if (this.same(taken, qty)) return this.chip(qty, rate, "is-used");
			return this.chip(qty, rate, "is-partly", __("{0} used", [this.number(taken)]));
		});
		return this.limit_chips(chips);
	}

	after_chips(lots, added) {
		if (!lots.length) return `<span class="vrb-muted">${__("None")}</span>`;
		const added_left = {};
		for (const [qty, rate] of added) added_left[rate] = (added_left[rate] || 0) + qty;
		const chips = [...lots].reverse().map(([qty, rate]) => {
			const is_added = (added_left[rate] || 0) > 0;
			if (is_added) added_left[rate] -= qty;
			return this.chip(qty, rate, is_added ? "is-added" : "");
		});
		return this.limit_chips(chips.reverse());
	}

	chip(qty, rate, css, extra) {
		const plus = css === "is-added" ? frappe.utils.icon("plus", "xs") : "";
		const note = extra ? ` <span class="vrb-chip-note">(${extra})</span>` : "";
		return `<span class="vrb-chip ${css}">${plus}${this.number(qty)} × ${this.money(rate)}${note}</span>`;
	}

	limit_chips(chips) {
		if (chips.length <= 8) return chips.join("");
		const more = `<span class="vrb-muted">${__("+{0} more", [chips.length - 8])}</span>`;
		return chips.slice(0, 8).join("") + more;
	}

	result_html(entry) {
		return `
			<div class="vrb-result">
				${frappe.utils.icon("equal", "sm")}
				<span>${this.result_text(entry)}</span>
			</div>
		`;
	}

	result_text(entry) {
		if (entry.qty_after < 0) {
			return __("Stock is now below zero. It is valued at {0} per unit until new stock comes in.", [
				this.b(this.money(entry.rate_after)),
			]);
		}
		if (!entry.qty_after) return __("No stock is left, so the stock value is {0}.", [this.money(0)]);
		const math = __("{0} ÷ {1} = {2}", [
			this.money(entry.value_after),
			this.qty(entry.qty_after),
			this.b(__("{0} per unit", [this.money(entry.rate_after)])),
		]);
		if (entry.qty_before > 0 && this.same(entry.rate_after, entry.rate_before)) {
			return __("{0}. The value per unit did not change.", [math]);
		}
		if (entry.qty_before > 0) return __("{0}, was {1}.", [math, this.money(entry.rate_before)]);
		return `${math}.`;
	}

	rate_note(entry) {
		const ma = this.data.item.valuation_method === "Moving Average";
		if (!ma || entry.kind !== "out" || !entry.is_return || entry.original_rate == null) return null;
		if (this.at_original_rate(entry)) return this.original_rate_note(entry);
		if (this.same(entry.rate, entry.rate_before) && !this.same(entry.rate, entry.original_rate)) {
			return this.average_rate_note(entry);
		}
		return null;
	}

	original_rate_note(entry) {
		return {
			theme: "amber",
			title: __("Why {0} and not the average of {1}?", [
				this.plain_money(entry.rate),
				this.plain_money(entry.rate_before),
			]),
			description: __(
				"A return goes out at the rate on the document it reverses, {0}. Taking out a value different from the average changes the average of the stock left. If stock values are recalculated later, for example after a backdated entry or a Landed Cost Voucher, this return is valued at the average instead.",
				[entry.return_against]
			),
		};
	}

	average_rate_note(entry) {
		return {
			theme: "blue",
			title: __("Why {0} and not the {1} on {2}?", [
				this.plain_money(entry.rate),
				this.plain_money(entry.original_rate),
				entry.return_against,
			]),
			description: __(
				"Stock values were recalculated after this return, so it now goes out at the average. All units here share one average, so the stock left keeps the same average."
			),
		};
	}

	at_original_rate(entry) {
		return (
			entry.is_return &&
			entry.original_rate != null &&
			this.same(entry.rate, entry.original_rate) &&
			!this.same(entry.rate, entry.rate_before)
		);
	}

	parts_html(entry) {
		const parts = entry.parts || [];
		if (!parts.length) return "";
		const rows = parts.slice(0, 8).map((part) => this.part_rows(entry, part));
		const more = parts.length > 8 ? this.part_hint(__("+{0} more", [parts.length - 8])) : "";
		return `<div class="vrb-parts">${rows.join("")}${more}</div>`;
	}

	part_rows(entry, part) {
		const tone = part.qty > 0 ? "vrb-in" : "vrb-out";
		const row = `
			<div class="vrb-part-row">
				<span class="ellipsis">${this.part_label(part)}</span>
				<span class="text-right ${tone}">${this.signed_qty(part.qty)}</span>
				<span class="text-right vrb-muted">× ${this.money(part.rate)}</span>
				<span class="text-right ${tone}">${this.signed_money(part.value)}</span>
			</div>
		`;
		const hint = part.qty < 0 ? this.part_reason(part) : "";
		return row + (hint ? this.part_hint(hint) : "");
	}

	part_label(part) {
		if (part.batch_no) return this.doc_link("Batch", part.batch_no, part.batch_id);
		const labels = part.serial_labels || part.serial_nos;
		const serials = labels.map((serial_no) => frappe.utils.escape_html(serial_no)).join(", ");
		return part.more ? __("{0} and {1} more", [serials, part.more]) : serials;
	}

	part_reason(part) {
		if (part.serial_nos) {
			if (!part.source_voucher_no) return "";
			return __("Came in through {0} {1} on {2}", [
				__(part.source_voucher_type),
				frappe.utils.escape_html(part.source_voucher_no),
				frappe.datetime.str_to_user(part.source_date),
			]);
		}
		if (!part.own_rate)
			return __("This batch does not keep its own rate, so it goes out at the warehouse rate");
		if (!part.qty_before) return __("This batch had no stock left to price from");
		return __("The batch had {0} worth {1}, so {2} per unit", [
			`${this.number(part.qty_before)} ${this.uom()}`,
			this.plain_money(part.value_before),
			this.plain_money(part.value_before / part.qty_before),
		]);
	}

	part_hint(text) {
		return `<div class="vrb-part-hint ellipsis" title="${frappe.utils.escape_html(text)}">${text}</div>`;
	}

	backdated_alert() {
		const entries = this.data.entries;
		const backdated = entries.filter((entry) => entry.later_dated_count).length;
		const changed = entries.filter((entry) => (entry.changed_by || []).length).length;
		if (!backdated && !changed) return null;
		return frappe.ui.alert({
			title: __("Some entries were posted with an earlier date"),
			description: __(
				"{0} entries below were entered after entries with a later date, and {1} entries were recalculated because of that. Look for the Backdated badge and the notes on the recalculated entries.",
				[backdated, changed]
			),
			theme: "blue",
		});
	}

	entered_late_html(entry) {
		if (!entry.later_dated_count) return "";
		const text = __(
			"Entered on {0}, after {1} entries with a later date. Those entries were recalculated.",
			[this.user_datetime(entry.entered_on), entry.later_dated_count]
		);
		return `<div class="vrb-opened">${frappe.utils.icon("history", "xs")} ${text}</div>`;
	}

	changed_note(entry) {
		const changes = entry.changed_by || [];
		if (!changes.length) return null;
		return {
			theme: "amber",
			title: this.changed_title(entry),
			description: __("Entered on {0}. Changed later by: {1}.", [
				this.user_datetime(entry.entered_on),
				this.change_list(changes),
			]),
		};
	}

	changed_title(entry) {
		if (entry.rate_after_when_entered == null) {
			return __("This was recalculated after earlier-dated entries changed");
		}
		if (entry.kind === "out" && !this.same(entry.rate, entry.rate_when_entered)) {
			return __("When this was entered it went out at {0}. It is {1} now.", [
				this.plain_money(entry.rate_when_entered),
				this.plain_money(entry.rate),
			]);
		}
		if (!this.same(entry.rate_after, entry.rate_after_when_entered)) {
			return __("When this was entered the value per unit after it was {0}. It is {1} now.", [
				this.plain_money(entry.rate_after_when_entered),
				this.plain_money(entry.rate_after),
			]);
		}
		return __("Entries with an earlier date were added later, but this rate did not change");
	}

	change_list(changes) {
		const items = changes.slice(0, 5).map((change) => {
			const dated = frappe.datetime.str_to_user(change.posting_date);
			const on = this.user_datetime(change.changed_on);
			return change.kind === "cancelled"
				? __("{0} {1} dated {2}, cancelled on {3}", [
						__(change.voucher_type),
						change.voucher_no,
						dated,
						on,
				  ])
				: __("{0} {1} dated {2}, entered on {3}", [
						__(change.voucher_type),
						change.voucher_no,
						dated,
						on,
				  ]);
		});
		if (changes.length > 5) items.push(__("{0} more", [changes.length - 5]));
		return this.join_list(items);
	}

	last_entry() {
		const entries = this.data.entries;
		return entries[entries.length - 1];
	}

	scroll_to(name) {
		if (!name) return;
		const step = this.container.find(`.vrb-step[data-entry="${CSS.escape(name)}"]`);
		if (step.length) step[0].scrollIntoView({ block: "center" });
	}

	is_queue() {
		return !this.data.item.valued_by && ["FIFO", "LIFO"].includes(this.data.item.valuation_method);
	}

	number(value) {
		const rounded = Number(flt(value, 3).toFixed(3));
		const decimals = (String(rounded).split(".")[1] || "").length;
		return format_number(rounded, null, decimals);
	}

	uom() {
		return frappe.utils.escape_html(__(this.data.item.stock_uom));
	}

	qty(value) {
		return `<span class="vrb-nowrap">${this.number(value)} ${this.uom()}</span>`;
	}

	signed_qty(value) {
		if (!flt(value, 3)) return "—";
		return `${value > 0 ? "+ " : "− "}${this.qty(Math.abs(value))}`;
	}

	money(value) {
		return `<span class="vrb-nowrap">${this.plain_money(value)}</span>`;
	}

	plain_money(value) {
		return format_currency(value, this.data.currency);
	}

	signed_money(value) {
		if (this.same(value, 0)) return this.money(0);
		return `${value > 0 ? "+ " : "− "}${this.money(Math.abs(value))}`;
	}

	user_datetime(value) {
		return frappe.datetime.str_to_user(value).replace(/:\d{2}(\.\d+)?$/, "");
	}

	same(a, b) {
		return Math.abs(flt(a) - flt(b)) < 0.005;
	}

	b(text) {
		return `<b>${text}</b>`;
	}

	join_list(items) {
		if (items.length < 2) return items.join("");
		return __("{0} and {1}", [items.slice(0, -1).join(", "), items[items.length - 1]]);
	}

	return_link(entry) {
		return this.doc_link(entry.voucher_type, entry.return_against);
	}

	doc_link(doctype, name, label) {
		const url = frappe.utils.get_form_link(doctype, name);
		return `<a href="${url}">${frappe.utils.escape_html(label || name)}</a>`;
	}

	styles() {
		return `<style>${this.layout_styles()}${this.entry_styles()}</style>`;
	}

	layout_styles() {
		return `
			.vrb { display: flex; flex-direction: column; gap: var(--padding-lg); max-width: 940px; margin: 0 auto var(--margin-2xl); }
			.vrb-card { background: var(--fg-color); border: 1px solid var(--outline-gray-1); border-radius: var(--radius-5); }
			.vrb-muted { color: var(--ink-gray-5); font-weight: 400; }
			.vrb-nowrap { white-space: nowrap; }
			.vrb .icon { margin: 0; }
			.vrb b { color: var(--ink-gray-9); font-weight: 600; }
			.vrb-gap { height: var(--margin-sm); }
			.vrb-summary-head { display: flex; align-items: flex-start; gap: var(--margin-lg); padding: var(--padding-lg); }
			.vrb-summary-text { flex: 1; min-width: 0; }
			.vrb-item { font-size: var(--text-xl); font-weight: 600; color: var(--ink-gray-9); }
			.vrb-item .vrb-muted { font-size: var(--text-sm); margin-left: var(--margin-xs); }
			.vrb-lead { margin-top: var(--margin-xs); font-size: var(--text-base); line-height: 1.6; color: var(--ink-gray-7); }
			.vrb-figures { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid var(--outline-gray-1); }
			.vrb-figure { padding: var(--padding-sm) var(--padding-lg); min-width: 0; }
			.vrb-figure + .vrb-figure { border-left: 1px solid var(--outline-gray-1); }
			.vrb-figure-label { font-size: var(--text-sm); color: var(--ink-gray-5); }
			.vrb-figure-value { margin-top: 2px; font-size: var(--text-2xl); font-weight: 600; color: var(--ink-gray-9); font-variant-numeric: tabular-nums; }
			.vrb-guide { border-top: 1px solid var(--outline-gray-1); padding: var(--padding-sm) var(--padding-lg); }
			.vrb-guide-toggle { display: flex; align-items: center; gap: var(--margin-sm); width: 100%; background: none; border: 0; padding: 0; font-size: var(--text-sm); color: var(--ink-gray-6); text-align: left; }
			.vrb-guide-toggle .icon { flex-shrink: 0; stroke: var(--ink-gray-5); }
			.vrb-guide-title { font-weight: 500; color: var(--ink-gray-7); white-space: nowrap; }
			.vrb-guide-short { min-width: 0; }
			.vrb-guide-chevron { margin-left: auto; display: flex; transition: transform 0.15s; }
			.vrb-guide.is-open .vrb-guide-chevron { transform: rotate(180deg); }
			.vrb-guide-steps { display: none; margin: var(--margin-sm) 0 0; padding-left: var(--padding-lg); list-style: none; }
			.vrb-guide.is-open .vrb-guide-steps { display: flex; flex-direction: column; gap: var(--margin-sm); }
			.vrb-guide-steps li { display: flex; gap: var(--margin-sm); font-size: var(--text-sm); line-height: 1.5; color: var(--ink-gray-7); }
			.vrb-step-no { flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 50%; background: var(--surface-gray-2); font-size: var(--text-xs); color: var(--ink-gray-6); }
			.vrb-section-title { margin-bottom: calc(-1 * var(--margin-xs)); font-size: var(--text-lg); font-weight: 600; color: var(--ink-gray-8); }
			@media (max-width: 767px) {
				.vrb-figure-value { font-size: var(--text-lg); }
			}
		`;
	}

	entry_styles() {
		return `
			.vrb-step { display: flex; gap: var(--margin-md); }
			.vrb-rail { display: flex; flex-direction: column; align-items: center; width: 32px; flex-shrink: 0; }
			.vrb-dot { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0; }
			.vrb-dot.is-in { background: var(--surface-green-2); color: var(--ink-green-6); }
			.vrb-dot.is-out { background: var(--surface-red-2); color: var(--ink-red-5); }
			.vrb-dot.is-gray { background: var(--surface-gray-2); color: var(--ink-gray-5); }
			.vrb-dot .icon, .vrb-chip .icon { stroke: currentColor; }
			.vrb-line { flex: 1; width: 1px; background: var(--outline-gray-2); }
			.vrb-step-body { flex: 1; min-width: 0; padding-bottom: var(--padding-lg); }
			.vrb-start { padding-top: 6px; font-size: var(--text-sm); }
			.vrb-start-title { font-size: var(--text-base); color: var(--ink-gray-7); margin-bottom: 2px; }
			.vrb-earlier { margin-top: var(--margin-sm); }
			.vrb-entry-head { display: flex; align-items: center; gap: var(--margin-sm); height: 32px; min-width: 0; }
			.vrb-date { flex-shrink: 0; font-size: var(--text-sm); color: var(--ink-gray-5); font-variant-numeric: tabular-nums; }
			.vrb-voucher { flex-shrink: 0; max-width: 40%; font-size: var(--text-base); font-weight: 600; color: var(--ink-gray-8); }
			.vrb-doc { min-width: 0; font-size: var(--text-sm); }
			.vrb-entry-head .es-badge { margin-left: auto; flex-shrink: 0; }
			.vrb-entry-head .es-badge ~ .es-badge { margin-left: 0; }
			.vrb-explain { margin-top: var(--margin-sm); padding: var(--padding-md); display: flex; flex-direction: column; gap: var(--margin-md); }
			.vrb-explain .vrb-lead { margin-top: 0; }
			.vrb-explain.is-focus { border-color: var(--outline-gray-4); background: var(--surface-gray-1); box-shadow: var(--shadow-sm); }
			.vrb-opened { display: flex; align-items: center; gap: 6px; font-size: var(--text-sm); color: var(--ink-gray-6); }
			.vrb-math { width: fit-content; max-width: 100%; overflow-x: auto; background: var(--surface-gray-1); border-radius: var(--radius-4); padding: var(--padding-xs) var(--padding-sm); }
			.vrb-explain.is-focus .vrb-math { background: var(--surface-gray-2); }
			.vrb-math-row { display: grid; grid-template-columns: 64px 120px 120px 140px; gap: var(--margin-sm); align-items: center; height: 32px; font-size: var(--text-sm); color: var(--ink-gray-7); font-variant-numeric: tabular-nums; }
			.vrb-math-row.is-total { border-top: 1px solid var(--outline-gray-2); color: var(--ink-gray-9); font-weight: 600; }
			.vrb-in { color: var(--ink-green-6); }
			.vrb-out { color: var(--ink-red-5); }
			.vrb-lots { display: grid; grid-template-columns: 80px minmax(0, 1fr); gap: var(--margin-sm) var(--margin-md); align-items: center; font-size: var(--text-sm); }
			.vrb-chips { display: flex; flex-wrap: wrap; gap: 6px; }
			.vrb-chip { display: inline-flex; align-items: center; gap: 4px; height: 24px; padding: 0 8px; border: 1px solid var(--outline-gray-2); border-radius: var(--radius-1); color: var(--ink-gray-7); font-variant-numeric: tabular-nums; white-space: nowrap; }
			.vrb-chip.is-used { border-color: var(--outline-red-2); background: var(--surface-red-1); color: var(--ink-red-5); text-decoration: line-through; }
			.vrb-chip.is-partly { border-color: var(--outline-amber-2); background: var(--surface-amber-1); color: var(--ink-amber-7); }
			.vrb-chip.is-added { border-color: var(--outline-green-2); background: var(--surface-green-1); color: var(--ink-green-6); }
			.vrb-chip-note { font-size: var(--text-xs); }
			.vrb-parts { display: flex; flex-direction: column; border: 1px solid var(--outline-gray-1); border-radius: var(--radius-4); padding: var(--padding-xs) var(--padding-sm); }
			.vrb-part-row { display: grid; grid-template-columns: minmax(0, 1fr) 120px 120px 140px; gap: var(--margin-sm); align-items: center; height: 32px; font-size: var(--text-sm); color: var(--ink-gray-7); font-variant-numeric: tabular-nums; }
			.vrb-part-hint { height: 24px; line-height: 24px; margin-top: -6px; font-size: var(--text-xs); color: var(--ink-gray-5); }
			.vrb-result { display: flex; align-items: flex-start; gap: var(--margin-sm); font-size: var(--text-sm); line-height: 1.5; color: var(--ink-gray-7); }
			.vrb-result .icon { flex-shrink: 0; margin: 2px 0 0; stroke: var(--ink-gray-5); }
			@media (max-width: 767px) {
				.vrb-math-row { grid-template-columns: 56px 96px 96px 112px; }
				.vrb-part-row { grid-template-columns: minmax(0, 1fr) 80px 96px 104px; }
			}
		`;
	}
};
