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
					"See how the stock value and the rate per unit were worked out, one entry at a time."
				),
			})
		);
	}

	render_skeleton() {
		const line = (height) => frappe.ui.skeleton.html({ width: "100%", height });
		this.container.html(`
			<div class="sve-panel">${line("64px")}</div>
			<div class="sve-panel">${line("280px")}</div>
		`);
	}

	render(scroll_to) {
		const data = this.data;
		this.container.empty();
		this.container.append(this.header_html());
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
		this.container.append(this.summary_html());
		this.container.append(this.ledger());
		this.scroll_to(scroll_to || this.focus);
	}

	header_html() {
		const data = this.data;
		const item = data.item;
		const name =
			item.item_name && item.item_name !== item.item_code
				? `${item.item_code}: ${item.item_name}`
				: item.item_code;
		const method = frappe.ui.badge.html({
			label: __("Valued by {0}", [__(item.valuation_method)]),
			theme: "gray",
		});
		const intro = item.unsupported ? "" : `<div class="sve-intro">${this.method_intro()}</div>`;
		return `
			<div class="sve-panel">
				<div class="sve-head">
					<div class="sve-title ellipsis" title="${frappe.utils.escape_html(name)}">
						${frappe.utils.escape_html(name)}
						<span class="sve-muted">· ${frappe.utils.escape_html(data.warehouse)}</span>
					</div>
					${method}
				</div>
				${intro}
			</div>
		`;
	}

	method_intro() {
		const intros = {
			"Moving Average": __(
				"All units of this item in this warehouse share one average rate. Each receipt changes the average. Issues go out at the average, so they do not change it."
			),
			FIFO: __(
				"Stock is kept as lots, each at the rate it came in at. Issues use the oldest lot first (First In, First Out)."
			),
			LIFO: __(
				"Stock is kept as lots, each at the rate it came in at. Issues use the newest lot first (Last In, First Out)."
			),
			"Standard Cost": __(
				"Every unit is valued at the item's standard cost, whatever was paid for it."
			),
		};
		return intros[this.data.item.valuation_method] || "";
	}

	unsupported_state() {
		const batch = this.data.item.unsupported === "batch";
		return frappe.ui.empty_state({
			icon: "layers",
			title: batch ? __("This item uses batches") : __("This item is valued per serial number"),
			description: __(
				"Explanations for batch items and serial number wise valuation are not available yet. The Stock Ledger shows the rate of each entry."
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
				"A stock repost is running for this company. The numbers below may change when it finishes."
			),
			theme: "amber",
		});
	}

	summary_html() {
		const entries = this.data.entries;
		const last = entries[entries.length - 1];
		const tile = (label, value) => `
			<div class="sve-tile">
				<div class="sve-tile-label">${label}</div>
				<div class="sve-tile-value">${value}</div>
			</div>
		`;
		return `
			<div class="sve-tiles">
				${tile(__("Stock on {0}", [frappe.datetime.str_to_user(last.posting_date)]), this.qty(last.qty_after))}
				${tile(__("Stock value"), this.money(last.value_after))}
				${tile(__("Value per unit"), this.money(last.rate_after))}
				${tile(__("Entries shown"), format_number(entries.length, null, 0))}
			</div>
		`;
	}

	ledger() {
		const ledger = $(`
			<div class="sve-panel sve-ledger">
				<div class="sve-scroll"><div class="sve-table">
					<div class="sve-grid sve-columns">
						<div>${__("Date")}</div>
						<div>${__("Document")}</div>
						<div class="text-right">${__("In / Out")}</div>
						<div class="text-right">${__("Rate used")}</div>
						<div class="text-right">${__("Units after")}</div>
						<div class="text-right">${__("Value after")}</div>
						<div class="text-right">${__("Rate after")}</div>
					</div>
				</div></div>
			</div>
		`);
		const table = ledger.find(".sve-table");
		if (this.data.has_earlier) table.append(this.earlier_button());
		table.append(this.opening_html());
		for (const entry of this.data.entries) table.append(this.entry_html(entry));
		return ledger;
	}

	earlier_button() {
		return $('<div class="sve-earlier"></div>').append(
			frappe.ui.button({
				label: __("Show earlier entries"),
				variant: "ghost",
				icon: "arrow-up",
				onclick: () => this.load_earlier(),
			})
		);
	}

	opening_html() {
		const opening = this.data.opening;
		const lots = this.is_queue() && opening.lots.length ? this.lots_html(opening.lots, [], []) : "";
		return `
			<div class="sve-entry sve-opening">
				<div class="sve-grid sve-row">
					<div></div>
					<div class="ellipsis">${__("Opening balance")}</div>
					<div></div>
					<div></div>
					<div class="text-right">${this.qty(opening.qty)}</div>
					<div class="text-right">${this.money(opening.value)}</div>
					<div class="text-right">${this.money(opening.rate)}</div>
				</div>
				${lots}
			</div>
		`;
	}

	entry_html(entry) {
		const focus = entry.name === this.focus ? " is-focus" : "";
		const lots = this.is_queue() ? this.entry_lots_html(entry) : "";
		return `
			<div class="sve-entry${focus}" data-entry="${entry.name}">
				<div class="sve-grid sve-row">
					<div class="ellipsis" title="${entry.posting_date} ${entry.posting_time}">
						${frappe.datetime.str_to_user(entry.posting_date)}
					</div>
					<div class="ellipsis">${this.document_html(entry)}</div>
					<div class="text-right ${this.qty_class(entry)}">${this.signed_qty(entry)}</div>
					<div class="text-right">${entry.qty ? this.money(entry.rate) : ""}</div>
					<div class="text-right">${this.qty(entry.qty_after)}</div>
					<div class="text-right">${this.money(entry.value_after)}</div>
					<div class="text-right">${this.money(entry.rate_after)}</div>
				</div>
				${lots}
				<div class="sve-say">${this.explain(entry)}</div>
			</div>
		`;
	}

	document_html(entry) {
		const link = this.doc_link(entry.voucher_type, entry.voucher_no);
		const kind = `<span class="sve-muted">${__(entry.voucher_type)}</span>`;
		return `${link} ${kind}`;
	}

	entry_lots_html(entry) {
		if (entry.kind === "revaluation") return "";
		const lots = entry.lots_after || [];
		if (!lots.length && !(entry.used_lots || []).length) return "";
		return this.lots_html(lots, entry.used_lots || [], entry.added_lots || []);
	}

	lots_html(lots, used, added) {
		const added_rates = new Set(added.map(([, rate]) => rate));
		const chip = ([qty, rate], css) =>
			`<span class="sve-lot ${css}">${this.qty(qty)} × ${this.money(rate)}</span>`;
		const chips = used
			.map((lot) => chip(lot, "is-used"))
			.concat(lots.map((lot) => chip(lot, added_rates.has(lot[1]) ? "is-added" : "")));
		const shown = chips.slice(0, 8).join("");
		const more =
			chips.length > 8 ? `<span class="sve-muted">${__("+{0} more", [chips.length - 8])}</span>` : "";
		return `<div class="sve-lots"><span class="sve-muted">${__("Lots")}</span>${shown}${more}</div>`;
	}

	explain(entry) {
		const explainers = {
			reconciliation: () => this.explain_reconciliation(entry),
			revaluation: () => this.explain_revaluation(entry),
			in: () => this.explain_in(entry),
			out: () => this.explain_out(entry),
		};
		const text = explainers[entry.kind]();
		return entry.qty_after < 0 ? `${text} ${this.negative_note(entry)}` : text;
	}

	explain_reconciliation(entry) {
		let text = __(
			"Stock was counted and set to {0} at {1} each, so the stock value is {0} × {1} = {2}.",
			[
				this.b(this.qty(entry.qty_after)),
				this.b(this.money(entry.rate_after)),
				this.b(this.money(entry.value_after)),
			]
		);
		if (entry.qty_before) {
			text +=
				" " +
				__("Before the count there were {0} worth {1}.", [
					this.qty(entry.qty_before),
					this.money(entry.value_before),
				]);
		}
		if (this.is_queue()) text += " " + __("Earlier lots are replaced by this one lot.");
		return text;
	}

	explain_revaluation(entry) {
		let text = __("No units moved, but the stock value changed by {0}, from {1} to {2}.", [
			this.b(this.money(entry.value_change)),
			this.money(entry.value_before),
			this.money(entry.value_after),
		]);
		if (entry.qty_after > 0) {
			text += " " + this.per_unit(entry);
		}
		return text;
	}

	explain_in(entry) {
		const lead = entry.is_return
			? __("Received {0} back against {1} at {2}.", [
					this.b(this.qty(entry.qty)),
					this.doc_link(entry.voucher_type, entry.return_against),
					this.b(this.money(entry.rate)),
			  ])
			: __("Received {0} at {1}.", [this.b(this.qty(entry.qty)), this.b(this.money(entry.rate))]);
		const parts = [lead];
		if (!entry.rate) parts.push(__("This receipt has a zero rate, so it adds no value."));
		if (entry.is_return) parts.push(this.return_in_note(entry));
		parts.push(this.inward_math(entry));
		return parts.filter(Boolean).join(" ");
	}

	inward_math(entry) {
		const method = this.data.item.valuation_method;
		if (method === "Standard Cost") return this.standard_cost_note(entry);
		if (method !== "Moving Average") {
			const lead =
				entry.qty_before < 0
					? __("Stock was below zero, so this first covers the shortage.")
					: __("It is kept as a new lot.");
			return `${lead} ${this.balance_note(entry)}`;
		}
		if (entry.qty_before === 0) {
			return __("There was no stock before this, so the average is the receipt rate, {0}.", [
				this.b(this.money(entry.rate_after)),
			]);
		}
		if (entry.qty_before < 0) {
			return __("Stock was below zero before this, so the average restarts at {0}.", [
				this.b(this.money(entry.rate_after)),
			]);
		}
		return this.average_math(entry, "+");
	}

	explain_out(entry) {
		const qty = this.b(this.qty(Math.abs(entry.qty)));
		const lead = entry.is_return
			? __("Returned {0} against {1}.", [qty, this.doc_link(entry.voucher_type, entry.return_against)])
			: __("Issued {0}.", [qty]);
		const method = this.data.item.valuation_method;
		if (method === "Standard Cost") {
			return `${lead} ${this.standard_cost_note(entry)}`;
		}
		if (method !== "Moving Average") {
			return `${lead} ${this.lots_used_note(entry)} ${this.balance_note(entry)}`;
		}
		return [lead, this.outward_rate_note(entry), this.average_math(entry, "−")].join(" ");
	}

	outward_rate_note(entry) {
		const rate = this.b(this.money(entry.rate));
		const at_average = this.same(entry.rate, entry.rate_before);
		if (entry.is_return && entry.original_rate != null) {
			const doc = this.doc_link(entry.voucher_type, entry.return_against);
			if (at_average && !this.same(entry.rate, entry.original_rate)) {
				return __(
					"It goes out at the current average, {0}, not the {1} paid on {2}. All units here share one average, so the stock left keeps the same average.",
					[rate, this.b(this.money(entry.original_rate)), doc]
				);
			}
			if (this.same(entry.rate, entry.original_rate) && !at_average) {
				return __(
					"It goes out at {0}, the rate paid on {1}, not the current average of {2}. Taking out a value different from the average changes the average of the stock left.",
					[rate, doc, this.money(entry.rate_before)]
				);
			}
		}
		return at_average
			? __("It goes out at the current average, {0}.", [rate])
			: __("It goes out at {0}.", [rate]);
	}

	average_math(entry, sign) {
		const text = __("Stock value: {0} {1} {2} = {3} for {4}.", [
			this.money(entry.value_before),
			sign,
			this.money(Math.abs(entry.value_change)),
			this.b(this.money(entry.value_after)),
			this.qty(entry.qty_after),
		]);
		if (entry.qty_after <= 0) return text;
		if (sign === "−" && this.same(entry.rate_after, entry.rate_before)) {
			return `${text} ${__("The average stays at {0}.", [this.b(this.money(entry.rate_after))])}`;
		}
		return `${text} ${__("New average: {0} ÷ {1} = {2}.", [
			this.money(entry.value_after),
			this.qty(entry.qty_after),
			this.b(this.money(entry.rate_after)),
		])}`;
	}

	return_in_note(entry) {
		if (entry.original_rate == null) return "";
		const doc = this.doc_link(entry.voucher_type, entry.return_against);
		if (this.same(entry.rate, entry.original_rate)) {
			return __("That is the same rate it went out at on {0}.", [doc]);
		}
		if (
			this.data.item.valuation_method === "Moving Average" &&
			this.same(entry.rate, entry.rate_before)
		) {
			return __(
				"Under Moving Average it comes back at the current average, not the {0} it went out at on {1}.",
				[this.b(this.money(entry.original_rate)), doc]
			);
		}
		return __("It went out at {0} on {1}.", [this.money(entry.original_rate), doc]);
	}

	lots_used_note(entry) {
		const used = entry.used_lots || [];
		if (!used.length) {
			return __("There was no stock left to take from, so it goes out at {0}.", [
				this.b(this.money(entry.rate)),
			]);
		}
		const list = used.map(([qty, rate]) => __("{0} at {1}", [this.qty(qty), this.money(rate)]));
		const text = __("It uses {0}, worth {1}.", [
			this.b(this.join_list(list)),
			this.b(this.money(Math.abs(entry.value_change))),
		]);
		return `${text} ${this.lot_reason(entry, used)}`;
	}

	lot_reason(entry, used) {
		const matches_original =
			entry.is_return &&
			entry.original_rate != null &&
			used.every(([, rate]) => this.same(rate, entry.original_rate));
		if (matches_original) {
			return __("As a return, it uses the lot at the same rate as {0}.", [
				this.doc_link(entry.voucher_type, entry.return_against),
			]);
		}
		return this.data.item.valuation_method === "LIFO"
			? __("Under LIFO the newest lot is used first.")
			: __("Under FIFO the oldest lot is used first.");
	}

	standard_cost_note(entry) {
		return __("Each unit is valued at the standard cost of {0}, so the stock value is {1} × {0} = {2}.", [
			this.b(this.money(entry.rate_after)),
			this.qty(entry.qty_after),
			this.b(this.money(entry.value_after)),
		]);
	}

	balance_note(entry) {
		const text = __("Stock is now {0} worth {1}.", [
			this.qty(entry.qty_after),
			this.b(this.money(entry.value_after)),
		]);
		return entry.qty_after > 0 ? `${text} ${this.per_unit(entry)}` : text;
	}

	per_unit(entry) {
		return __("Value per unit: {0} ÷ {1} = {2}.", [
			this.money(entry.value_after),
			this.qty(entry.qty_after),
			this.b(this.money(entry.rate_after)),
		]);
	}

	negative_note(entry) {
		return __("Stock is now below zero. It is valued at {0} per unit until new stock comes in.", [
			this.money(entry.rate_after),
		]);
	}

	scroll_to(name) {
		if (!name) return;
		const row = this.container.find(`.sve-entry[data-entry="${CSS.escape(name)}"]`);
		if (row.length) row[0].scrollIntoView({ block: "center" });
	}

	is_queue() {
		return ["FIFO", "LIFO"].includes(this.data.item.valuation_method);
	}

	signed_qty(entry) {
		if (!entry.qty) return "";
		return `${entry.qty > 0 ? "+" : "−"}${this.qty(Math.abs(entry.qty))}`;
	}

	qty_class(entry) {
		if (!entry.qty) return "";
		return entry.qty > 0 ? "sve-in" : "sve-out";
	}

	qty(value) {
		const rounded = Number(flt(value, 3).toFixed(3));
		const decimals = (String(rounded).split(".")[1] || "").length;
		return `${format_number(rounded, null, decimals)} ${__(this.data.item.stock_uom)}`;
	}

	money(value) {
		return `<span class="sve-nowrap">${format_currency(value, this.data.currency)}</span>`;
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

	doc_link(doctype, name) {
		const url = frappe.utils.get_form_link(doctype, name);
		return `<a href="${url}">${frappe.utils.escape_html(name)}</a>`;
	}

	styles() {
		return `<style>
			.sve { display: flex; flex-direction: column; gap: var(--padding-md); max-width: 1040px; margin-bottom: var(--margin-xl); }
			.sve-panel { background: var(--fg-color); border: 1px solid var(--border-color); border-radius: var(--radius-5, 10px); padding: var(--padding-md); }
			.sve-head { display: flex; align-items: center; justify-content: space-between; gap: var(--margin-md); }
			.sve-title { font-size: var(--text-lg); font-weight: 600; color: var(--ink-gray-8); min-width: 0; }
			.sve-muted { color: var(--ink-gray-5); font-weight: 400; }
			.sve-intro { margin-top: var(--margin-xs); color: var(--ink-gray-6); font-size: var(--text-sm); }
			.sve-tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--padding-md); }
			.sve-tile { background: var(--fg-color); border: 1px solid var(--border-color); border-radius: var(--radius-5, 10px); padding: var(--padding-sm) var(--padding-md); min-width: 0; }
			.sve-tile-label { font-size: var(--text-xs); color: var(--ink-gray-5); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
			.sve-tile-value { font-size: var(--text-lg); font-weight: 600; color: var(--ink-gray-8); font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
			.sve-ledger { padding: 0; }
			.sve-scroll { overflow-x: auto; }
			.sve-table { min-width: 820px; }
			.sve-grid { display: grid; grid-template-columns: 96px minmax(0, 1fr) 96px 120px 110px 130px 120px; gap: var(--margin-sm); align-items: center; padding: 0 var(--padding-md); }
			.sve-columns { height: 36px; font-size: var(--text-xs); color: var(--ink-gray-5); border-bottom: 1px solid var(--border-color); }
			.sve-row { height: 40px; font-size: var(--text-sm); color: var(--ink-gray-8); font-variant-numeric: tabular-nums; }
			.sve-entry { border-bottom: 1px solid var(--border-color); border-left: 2px solid transparent; }
			.sve-entry:last-child { border-bottom: none; }
			.sve-entry.is-focus { background: var(--surface-gray-1); border-left-color: var(--ink-gray-8); }
			.sve-opening .sve-row { color: var(--ink-gray-6); }
			.sve-say { padding: 0 var(--padding-md) var(--padding-sm); padding-left: calc(96px + var(--margin-sm) + var(--padding-md)); font-size: var(--text-sm); color: var(--ink-gray-6); line-height: 1.5; max-width: 860px; }
			.sve-nowrap { white-space: nowrap; }
			.sve-say b { color: var(--ink-gray-8); font-weight: 600; }
			.sve-lots { display: flex; align-items: center; gap: var(--margin-xs); padding: 0 var(--padding-md) var(--padding-sm); padding-left: calc(96px + var(--margin-sm) + var(--padding-md)); font-size: var(--text-xs); flex-wrap: nowrap; overflow: hidden; }
			.sve-lot { border: 1px solid var(--border-color); border-radius: var(--radius-sm, 6px); padding: 1px 6px; white-space: nowrap; font-variant-numeric: tabular-nums; color: var(--ink-gray-7); }
			.sve-lot.is-used { text-decoration: line-through; color: var(--ink-red-7); background: var(--surface-red-1); border-color: transparent; }
			.sve-lot.is-added { color: var(--ink-green-7); background: var(--surface-green-1); border-color: transparent; }
			.sve-in { color: var(--ink-green-7); }
			.sve-out { color: var(--ink-red-7); }
			.sve-earlier { padding: var(--padding-xs) var(--padding-md); border-bottom: 1px solid var(--border-color); }
			@media (max-width: 767px) {
				.sve-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
			}
		</style>`;
	}
};
