frappe.pages["stock-valuation-explained"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Stock Valuation Explained"),
		single_column: true,
	});

	frappe.stock_valuation_explained = new erpnext.StockValuationExplained(page);
};

frappe.pages["stock-valuation-explained"].on_page_show = function () {
	const explainer = frappe.stock_valuation_explained;
	const options = frappe.route_options;
	if (!explainer || !options || !options.item_code || !options.warehouse) return;

	frappe.route_options = null;
	explainer.open(options.item_code, options.warehouse, options.entry);
};

erpnext.StockValuationExplained = class StockValuationExplained {
	constructor(page) {
		this.page = page;
		this.body = $(this.page.body);
		this.body.append(`${this.styles()}<div class="sve"></div>`);
		this.container = this.body.find(".sve");
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
		this.fetch(args).then((data) => {
			if (this.key !== key) return;
			this.data = data;
			this.render();
		});
	}

	load_earlier() {
		const first = this.data.entries[0];
		const key = this.key;
		return this.fetch({
			item_code: this.data.item.item_code,
			warehouse: this.data.warehouse,
			before: first.name,
		}).then((data) => {
			if (this.key !== key) return;
			this.data.entries = data.entries.concat(this.data.entries);
			this.data.opening = data.opening;
			this.data.has_earlier = data.has_earlier;
			this.render(first.name);
		});
	}

	fetch(args) {
		return frappe
			.call({
				method: "erpnext.stock.page.stock_valuation_explained.stock_valuation_explained.get_valuation_steps",
				args,
			})
			.then((r) => r.message);
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
			<div class="sve-step">
				<div class="sve-rail">${block("32px", "32px")}</div>
				<div class="sve-step-body">
					${block("50%", "20px")}
					<div class="sve-gap"></div>
					${block("100%", "128px")}
				</div>
			</div>
		`;
		this.container.html(`<div class="sve-card">${block("100%", "176px")}</div>${step.repeat(3)}`);
	}

	render(scroll_to) {
		const data = this.data;
		this.container.empty();
		if (data.item.unsupported) {
			this.container.append(this.unsupported_state());
			return;
		}
		if (!data.entries.length) {
			this.container.append(this.no_entries_state());
			return;
		}
		if (data.repost_pending) {
			this.container.append(this.repost_alert());
		}
		this.container.append(this.summary());
		this.container.append(`<div class="sve-section-title">${__("How we got here, step by step")}</div>`);
		this.container.append(this.timeline());
		this.scroll_to(scroll_to || this.focus);
	}

	unsupported_state() {
		const batch = this.data.item.unsupported === "batch";
		return frappe.ui.empty_state({
			icon: "layers",
			title: batch
				? __("This item is valued batch by batch")
				: __("This item is valued per serial number"),
			description: batch
				? __("Each batch keeps its own rate. A batch by batch explanation is not available yet.")
				: __(
						"Each serial number keeps its own rate. A serial number explanation is not available yet."
				  ),
		});
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
			<div class="sve-card">
				<div class="sve-summary-head">
					<div class="sve-summary-text">
						<div class="sve-item ellipsis">
							${frappe.utils.escape_html(item.item_name || item.item_code)}
							<span class="sve-muted">${frappe.utils.escape_html(item.item_code)}</span>
						</div>
						<div class="sve-lead">${this.summary_sentence()}</div>
					</div>
					${frappe.ui.badge.html({
						label: __("Valued by {0}", [__(item.valuation_method)]),
						theme: "blue",
						size: "lg",
					})}
				</div>
				${this.figures_html()}
				${this.guide_html()}
			</div>
		`);
		card.find(".sve-guide-toggle").on("click", () => card.find(".sve-guide").toggleClass("is-open"));
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
			<div class="sve-figure ${align}">
				<div class="sve-figure-label">${label}</div>
				<div class="sve-figure-value ellipsis">${value}</div>
			</div>
		`;
		return `
			<div class="sve-figures">
				${figure(__("Units in stock"), this.qty(last.qty_after), "")}
				${figure(__("Stock value"), this.money(last.value_after), "text-right")}
				${figure(__("Value per unit"), this.money(last.rate_after), "text-right")}
			</div>
		`;
	}

	guide_html() {
		const method = this.data.item.valuation_method;
		const guide = this.method_guides()[method];
		if (!guide) return "";
		const steps = guide.steps
			.map((step, i) => `<li><span class="sve-step-no">${i + 1}</span><span>${step}</span></li>`)
			.join("");
		return `
			<div class="sve-guide">
				<button class="sve-guide-toggle">
					${frappe.utils.icon("lightbulb", "sm")}
					<span class="sve-guide-title">${__("How {0} works:", [__(method)])}</span>
					<span class="sve-guide-short ellipsis">${guide.short}</span>
					<span class="sve-guide-chevron">${frappe.utils.icon("chevron-down", "sm")}</span>
				</button>
				<ol class="sve-guide-steps">${steps}</ol>
			</div>
		`;
	}

	method_guides() {
		const own_lot = __("Every receipt is kept as its own lot, with its own rate.");
		const lots_left = __("The value per unit is the value of the lots left, divided by the units left.");
		return {
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
		const list = $('<div class="sve-timeline"></div>');
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
			<div class="sve-step">
				<div class="sve-rail">
					<div class="sve-dot is-gray">${frappe.utils.icon("flag", "sm")}</div>
					<div class="sve-line"></div>
				</div>
				<div class="sve-step-body sve-start">
					<div class="sve-start-title">${title}</div>
					<div class="sve-muted">${hint}</div>
				</div>
			</div>
		`);
		if (this.data.has_earlier) step.find(".sve-start").append(this.earlier_button());
		return step;
	}

	earlier_button() {
		return $('<div class="sve-earlier"></div>').append(
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
			<div class="sve-step" data-entry="${frappe.utils.escape_html(entry.name)}">
				<div class="sve-rail">
					${this.dot_html(entry)}
					${is_last ? "" : '<div class="sve-line"></div>'}
				</div>
				<div class="sve-step-body">
					${this.entry_header_html(entry)}
					<div class="sve-card sve-explain${focus ? " is-focus" : ""}">
						${focus ? this.opened_html() : ""}
						<div class="sve-lead">${this.headline(entry)}</div>
						${this.math_html(entry)}
						${this.is_queue() ? this.lots_html(entry) : ""}
						${this.result_html(entry)}
					</div>
				</div>
			</div>
		`);
		const note = this.rate_note(entry);
		if (note) step.find(".sve-explain").append(frappe.ui.alert(note));
		return step;
	}

	opened_html() {
		const icon = frappe.utils.icon("mouse-pointer-click", "xs");
		return `<div class="sve-opened">${icon} ${__("You opened this entry from the Stock Ledger")}</div>`;
	}

	dot_html(entry) {
		const dots = {
			in: ["arrow-down-to-line", "is-in"],
			out: ["arrow-up-from-line", "is-out"],
			reconciliation: ["clipboard-check", "is-gray"],
			revaluation: ["scale", "is-gray"],
		};
		const [icon, css] = dots[entry.kind];
		return `<div class="sve-dot ${css}">${frappe.utils.icon(
			entry.is_return ? "undo-2" : icon,
			"sm"
		)}</div>`;
	}

	entry_header_html(entry) {
		const date = frappe.datetime.str_to_user(entry.posting_date);
		const time = moment(entry.posting_time, "HH:mm:ss").format("HH:mm");
		return `
			<div class="sve-entry-head">
				<span class="sve-date">${date} ${time}</span>
				<span class="sve-voucher ellipsis">${this.voucher_label(entry)}</span>
				<span class="sve-doc ellipsis">${this.doc_link(entry.voucher_type, entry.voucher_no)}</span>
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
		if (this.is_queue()) return `${lead}. ${this.lots_used_note(entry)}`;
		if (this.data.item.valuation_method === "Standard Cost") {
			return __("{0} at the standard cost, {1}.", [lead, rate]);
		}
		if (this.at_original_rate(entry)) return __("{0} at {1}, the rate it came in at.", [lead, rate]);
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
		return `<div class="sve-math">${rows.join("")}</div>`;
	}

	math_row(label, qty, rate, value, type) {
		const change = type === "change";
		const tone = change ? (qty > 0 || (!qty && value > 0) ? "sve-in" : "sve-out") : "";
		const show_rate = change ? qty && rate : qty;
		return `
			<div class="sve-math-row${type === "total" ? " is-total" : ""}">
				<span class="sve-muted">${label}</span>
				<span class="text-right ${tone}">${change ? this.signed_qty(qty) : this.qty(qty)}</span>
				<span class="text-right sve-muted">${show_rate ? `× ${this.money(rate)}` : "—"}</span>
				<span class="text-right ${tone}">${change ? this.signed_money(value) : this.money(value)}</span>
			</div>
		`;
	}

	lots_html(entry) {
		const before = entry.lots_before || [];
		const after = entry.lots_after || [];
		if (!before.length && !after.length) return "";
		return `
			<div class="sve-lots">
				<span class="sve-muted">${__("Lots before")}</span>
				<div class="sve-chips">${this.before_chips(before, entry.used_lots || [])}</div>
				<span class="sve-muted">${__("Lots after")}</span>
				<div class="sve-chips">${this.after_chips(after, entry.added_lots || [])}</div>
			</div>
		`;
	}

	before_chips(lots, used) {
		if (!lots.length) return `<span class="sve-muted">${__("None")}</span>`;
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
		if (!lots.length) return `<span class="sve-muted">${__("None")}</span>`;
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
		const note = extra ? ` <span class="sve-chip-note">(${extra})</span>` : "";
		return `<span class="sve-chip ${css}">${plus}${this.number(qty)} × ${this.money(rate)}${note}</span>`;
	}

	limit_chips(chips) {
		if (chips.length <= 8) return chips.join("");
		const more = `<span class="sve-muted">${__("+{0} more", [chips.length - 8])}</span>`;
		return chips.slice(0, 8).join("") + more;
	}

	result_html(entry) {
		return `
			<div class="sve-result">
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

	last_entry() {
		const entries = this.data.entries;
		return entries[entries.length - 1];
	}

	scroll_to(name) {
		if (!name) return;
		const step = this.container.find(`.sve-step[data-entry="${CSS.escape(name)}"]`);
		if (step.length) step[0].scrollIntoView({ block: "center" });
	}

	is_queue() {
		return ["FIFO", "LIFO"].includes(this.data.item.valuation_method);
	}

	number(value) {
		const rounded = Number(flt(value, 3).toFixed(3));
		const decimals = (String(rounded).split(".")[1] || "").length;
		return format_number(rounded, null, decimals);
	}

	qty(value) {
		return `<span class="sve-nowrap">${this.number(value)} ${__(this.data.item.stock_uom)}</span>`;
	}

	signed_qty(value) {
		if (!flt(value, 3)) return "—";
		return `${value > 0 ? "+ " : "− "}${this.qty(Math.abs(value))}`;
	}

	money(value) {
		return `<span class="sve-nowrap">${this.plain_money(value)}</span>`;
	}

	plain_money(value) {
		return format_currency(value, this.data.currency);
	}

	signed_money(value) {
		if (this.same(value, 0)) return this.money(0);
		return `${value > 0 ? "+ " : "− "}${this.money(Math.abs(value))}`;
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

	doc_link(doctype, name) {
		const url = frappe.utils.get_form_link(doctype, name);
		return `<a href="${url}">${frappe.utils.escape_html(name)}</a>`;
	}

	styles() {
		return `<style>${this.layout_styles()}${this.entry_styles()}</style>`;
	}

	layout_styles() {
		return `
			.sve { display: flex; flex-direction: column; gap: var(--padding-lg); max-width: 940px; margin: 0 auto var(--margin-2xl); }
			.sve-card { background: var(--fg-color); border: 1px solid var(--outline-gray-1); border-radius: var(--radius-5); }
			.sve-muted { color: var(--ink-gray-5); font-weight: 400; }
			.sve-nowrap { white-space: nowrap; }
			.sve .icon { margin: 0; }
			.sve b { color: var(--ink-gray-9); font-weight: 600; }
			.sve-gap { height: var(--margin-sm); }
			.sve-summary-head { display: flex; align-items: flex-start; gap: var(--margin-lg); padding: var(--padding-lg); }
			.sve-summary-text { flex: 1; min-width: 0; }
			.sve-item { font-size: var(--text-xl); font-weight: 600; color: var(--ink-gray-9); }
			.sve-item .sve-muted { font-size: var(--text-sm); margin-left: var(--margin-xs); }
			.sve-lead { margin-top: var(--margin-xs); font-size: var(--text-base); line-height: 1.6; color: var(--ink-gray-7); }
			.sve-figures { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid var(--outline-gray-1); }
			.sve-figure { padding: var(--padding-sm) var(--padding-lg); min-width: 0; }
			.sve-figure + .sve-figure { border-left: 1px solid var(--outline-gray-1); }
			.sve-figure-label { font-size: var(--text-sm); color: var(--ink-gray-5); }
			.sve-figure-value { margin-top: 2px; font-size: var(--text-2xl); font-weight: 600; color: var(--ink-gray-9); font-variant-numeric: tabular-nums; }
			.sve-guide { border-top: 1px solid var(--outline-gray-1); padding: var(--padding-sm) var(--padding-lg); }
			.sve-guide-toggle { display: flex; align-items: center; gap: var(--margin-sm); width: 100%; background: none; border: 0; padding: 0; font-size: var(--text-sm); color: var(--ink-gray-6); text-align: left; }
			.sve-guide-toggle .icon { flex-shrink: 0; stroke: var(--ink-gray-5); }
			.sve-guide-title { font-weight: 500; color: var(--ink-gray-7); white-space: nowrap; }
			.sve-guide-short { min-width: 0; }
			.sve-guide-chevron { margin-left: auto; display: flex; transition: transform 0.15s; }
			.sve-guide.is-open .sve-guide-chevron { transform: rotate(180deg); }
			.sve-guide-steps { display: none; margin: var(--margin-sm) 0 0; padding-left: var(--padding-lg); list-style: none; }
			.sve-guide.is-open .sve-guide-steps { display: flex; flex-direction: column; gap: var(--margin-sm); }
			.sve-guide-steps li { display: flex; gap: var(--margin-sm); font-size: var(--text-sm); line-height: 1.5; color: var(--ink-gray-7); }
			.sve-step-no { flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 50%; background: var(--surface-gray-2); font-size: var(--text-xs); color: var(--ink-gray-6); }
			.sve-section-title { margin-bottom: calc(-1 * var(--margin-xs)); font-size: var(--text-lg); font-weight: 600; color: var(--ink-gray-8); }
			@media (max-width: 767px) {
				.sve-figure-value { font-size: var(--text-lg); }
			}
		`;
	}

	entry_styles() {
		return `
			.sve-step { display: flex; gap: var(--margin-md); }
			.sve-rail { display: flex; flex-direction: column; align-items: center; width: 32px; flex-shrink: 0; }
			.sve-dot { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0; }
			.sve-dot.is-in { background: var(--surface-green-2); color: var(--ink-green-6); }
			.sve-dot.is-out { background: var(--surface-red-2); color: var(--ink-red-5); }
			.sve-dot.is-gray { background: var(--surface-gray-2); color: var(--ink-gray-5); }
			.sve-dot .icon, .sve-chip .icon { stroke: currentColor; }
			.sve-line { flex: 1; width: 1px; background: var(--outline-gray-2); }
			.sve-step-body { flex: 1; min-width: 0; padding-bottom: var(--padding-lg); }
			.sve-start { padding-top: 6px; font-size: var(--text-sm); }
			.sve-start-title { font-size: var(--text-base); color: var(--ink-gray-7); margin-bottom: 2px; }
			.sve-earlier { margin-top: var(--margin-sm); }
			.sve-entry-head { display: flex; align-items: center; gap: var(--margin-sm); height: 32px; min-width: 0; }
			.sve-date { flex-shrink: 0; font-size: var(--text-sm); color: var(--ink-gray-5); font-variant-numeric: tabular-nums; }
			.sve-voucher { flex-shrink: 0; max-width: 40%; font-size: var(--text-base); font-weight: 600; color: var(--ink-gray-8); }
			.sve-doc { min-width: 0; font-size: var(--text-sm); }
			.sve-entry-head .es-badge { margin-left: auto; flex-shrink: 0; }
			.sve-explain { margin-top: var(--margin-sm); padding: var(--padding-md); display: flex; flex-direction: column; gap: var(--margin-md); }
			.sve-explain .sve-lead { margin-top: 0; }
			.sve-explain.is-focus { border-color: var(--outline-gray-4); background: var(--surface-gray-1); box-shadow: var(--shadow-sm); }
			.sve-opened { display: flex; align-items: center; gap: 6px; font-size: var(--text-sm); color: var(--ink-gray-6); }
			.sve-math { width: fit-content; max-width: 100%; overflow-x: auto; background: var(--surface-gray-1); border-radius: var(--radius-4); padding: var(--padding-xs) var(--padding-sm); }
			.sve-explain.is-focus .sve-math { background: var(--surface-gray-2); }
			.sve-math-row { display: grid; grid-template-columns: 64px 120px 120px 140px; gap: var(--margin-sm); align-items: center; height: 32px; font-size: var(--text-sm); color: var(--ink-gray-7); font-variant-numeric: tabular-nums; }
			.sve-math-row.is-total { border-top: 1px solid var(--outline-gray-2); color: var(--ink-gray-9); font-weight: 600; }
			.sve-in { color: var(--ink-green-6); }
			.sve-out { color: var(--ink-red-5); }
			.sve-lots { display: grid; grid-template-columns: 80px minmax(0, 1fr); gap: var(--margin-sm) var(--margin-md); align-items: center; font-size: var(--text-sm); }
			.sve-chips { display: flex; flex-wrap: wrap; gap: 6px; }
			.sve-chip { display: inline-flex; align-items: center; gap: 4px; height: 24px; padding: 0 8px; border: 1px solid var(--outline-gray-2); border-radius: var(--radius-1); color: var(--ink-gray-7); font-variant-numeric: tabular-nums; white-space: nowrap; }
			.sve-chip.is-used { border-color: var(--outline-red-2); background: var(--surface-red-1); color: var(--ink-red-5); text-decoration: line-through; }
			.sve-chip.is-partly { border-color: var(--outline-amber-2); background: var(--surface-amber-1); color: var(--ink-amber-7); }
			.sve-chip.is-added { border-color: var(--outline-green-2); background: var(--surface-green-1); color: var(--ink-green-6); }
			.sve-chip-note { font-size: var(--text-xs); }
			.sve-result { display: flex; align-items: flex-start; gap: var(--margin-sm); font-size: var(--text-sm); line-height: 1.5; color: var(--ink-gray-7); }
			.sve-result .icon { flex-shrink: 0; margin: 2px 0 0; stroke: var(--ink-gray-5); }
			@media (max-width: 767px) {
				.sve-math-row { grid-template-columns: 56px 96px 96px 112px; }
			}
		`;
	}
};
