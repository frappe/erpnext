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
	explainer.open(options.item_code, options.warehouse, options.entry, {
		batch_no: options.batch_no,
		serial_no: options.serial_no,
	});
};

const PARTS_SHOWN = 5;
const PARTS_LISTED = 100;

erpnext.ValuationRateBreakdown = class ValuationRateBreakdown {
	constructor(page) {
		this.page = page;
		this.body = $(this.page.body);
		this.body.append(`${this.styles()}<div class="vrb"></div>`);
		this.container = this.body.find(".vrb");
		this.container.on("click", ".vrb-details-toggle", (e) => this.toggle_open(e, ".vrb-explain"));
		this.container.on("click", ".vrb-more-toggle", (e) => this.toggle_open(e, ".vrb-stock-list"));
		this.stock_parts_open = false;
		this.container.on("click", ".vrb-stock-toggle", (e) => {
			this.stock_parts_open = this.toggle_open(e, ".vrb-stock-parts");
		});
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
		this.batch_field = this.page.add_field({
			fieldname: "batch_no",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Batch",
			get_query: () => ({ filters: { item: this.item_field.get_value() } }),
			change: on_change,
		});
		this.serial_field = this.page.add_field({
			fieldname: "serial_no",
			label: __("Serial No"),
			fieldtype: "Link",
			options: "Serial No",
			get_query: () => ({ filters: { item_code: this.item_field.get_value() } }),
			change: on_change,
		});
		this.toggle_part_fields(null);
	}

	toggle_part_fields(valued_by) {
		this.batch_field.$wrapper.toggle(valued_by === "batch");
		this.serial_field.$wrapper.toggle(valued_by === "serial");
	}

	on_filter_change() {
		if (this.setting_filters) return;
		const item_code = this.item_field.get_value();
		const warehouse = this.warehouse_field.get_value();
		const item_changed = item_code !== this.last_item;
		if (item_changed) this.clear_part_fields(item_code);
		if (item_code && warehouse) {
			this.load({ item_code, warehouse, ...(item_changed ? {} : this.part_args()) });
		} else {
			this.key = null;
			this.render_blank_state();
		}
	}

	clear_part_fields(item_code) {
		this.last_item = item_code;
		this.toggle_part_fields(null);
		this.setting_filters = true;
		Promise.all([this.batch_field.set_value(""), this.serial_field.set_value("")]).then(() => {
			this.setting_filters = false;
		});
	}

	part_args() {
		const args = {};
		if (this.batch_field.get_value()) args.batch_no = this.batch_field.get_value();
		if (this.serial_field.get_value()) args.serial_no = this.serial_field.get_value();
		return args;
	}

	open(item_code, warehouse, entry, parts = {}) {
		this.setting_filters = true;
		this.last_item = item_code;
		Promise.all([this.item_field.set_value(item_code), this.warehouse_field.set_value(warehouse)])
			.then(() =>
				Promise.all([
					this.batch_field.set_value(parts.batch_no || ""),
					this.serial_field.set_value(parts.serial_no || ""),
				])
			)
			.then(() => {
				this.setting_filters = false;
				this.load({ item_code, warehouse, upto: entry, ...this.part_args() });
			});
	}

	load(args) {
		const key = [args.item_code, args.warehouse, args.upto, args.batch_no, args.serial_no].join("::");
		this.key = key;
		this.args = args;
		this.focus = args.upto || null;
		this.render_skeleton();
		this.fetch("get_valuation_steps", args).then(
			(data) => {
				if (this.key !== key) return;
				this.data = data;
				this.breakdown_state = this.is_pooled_view() && data.entries.length ? "loading" : null;
				this.toggle_part_fields(data.item.valued_by);
				this.render();
				if (this.breakdown_state) this.load_breakdown(key);
			},
			() => {
				if (this.key === key) this.render_failed(args);
			}
		);
	}

	load_breakdown(key) {
		this.fetch("get_stock_breakdown", {
			item_code: this.data.item.item_code,
			warehouse: this.data.warehouse,
			upto: this.last_entry().name,
		}).then(
			(breakdown) => this.show_breakdown(key, "ready", breakdown),
			() => this.show_breakdown(key, "failed", {})
		);
	}

	show_breakdown(key, state, breakdown) {
		if (this.key !== key) return;
		Object.assign(this.data, breakdown);
		this.breakdown_state = state;
		this.container.find(".vrb-stock-parts").replaceWith(this.stock_parts_html());
		this.update_notices();
	}

	notices() {
		return [this.problems_alert(), this.gap_alert(), this.backdated_alert()].filter(Boolean);
	}

	update_notices() {
		const slot = this.container.find(".vrb-notices-slot").empty();
		const count = this.notices().length;
		if (!count) return;
		const tone = this.repost_target() ? "is-red" : this.data.stock_gap ? "is-amber" : "is-blue";
		slot.append(
			frappe.ui.button({
				label: count === 1 ? __("1 notice") : __("{0} notices", [count]),
				icon: tone === "is-blue" ? "info" : "triangle-alert",
				variant: "subtle",
				css_class: `vrb-notices-button ${tone}`,
				onclick: () => this.show_notices(),
			})
		);
	}

	show_notices() {
		this.notices_dialog = new frappe.ui.Dialog({ title: __("Notices"), size: "large" });
		this.notices_dialog.$body.append($('<div class="vrb-notices"></div>').append(this.notices()));
		this.notices_dialog.show();
	}

	problems_alert() {
		const target = this.repost_target();
		if (!target) return null;
		const count = this.data.entries.filter((entry) => entry.ledger_problems).length;
		const alert = {
			title:
				count === 1
					? __("1 entry has figures that don't add up")
					: __("{0} entries have figures that don't add up", [count]),
			description: __("Reposting from {0} recalculates it and every entry after it.", [
				this.repost_start_label(target.repost_from),
			]),
			theme: "red",
		};
		if (this.can_repost()) {
			alert.primary_action = {
				label: __("Repost from {0}", [frappe.datetime.str_to_user(target.repost_from.posting_date)]),
				onclick: () => this.confirm_repost(target.repost_from),
			};
		}
		return frappe.ui.alert(alert);
	}

	repost_target() {
		return this.data.entries.find((entry) => entry.repost_from) || null;
	}

	can_repost() {
		return frappe.model.can_create("Repost Item Valuation") && this.data.repost_status !== "pending";
	}

	repost_start_label(start) {
		const date = frappe.datetime.str_to_user(start.posting_date);
		const time = moment(start.posting_time, "HH:mm:ss").format("HH:mm");
		return `${date} ${time}, ${frappe.utils.escape_html(start.voucher_no)}`;
	}

	repost_block(entry) {
		const start = entry.repost_from;
		const block = $('<div class="vrb-repost"></div>');
		if (start.name !== entry.name) {
			const text = __("This started earlier, on {0}. Reposting starts there.", [
				this.repost_start_label(start),
			]);
			block.append(
				`<div class="vrb-muted ellipsis" title="${frappe.utils.escape_html(text)}">${text}</div>`
			);
		}
		if (!this.can_repost()) {
			const text =
				this.data.repost_status === "pending"
					? __("A repost is already queued for this item and warehouse.")
					: __("Ask a Stock Manager to repost from this entry.");
			return block.append(`<div class="vrb-muted ellipsis">${text}</div>`);
		}
		return block.append(
			frappe.ui.button({
				label:
					start.name === entry.name
						? __("Repost from this entry")
						: __("Repost from {0}", [frappe.datetime.str_to_user(start.posting_date)]),
				icon: "refresh-cw",
				variant: "subtle",
				onclick: () => this.confirm_repost(start),
			})
		);
	}

	confirm_repost(start) {
		if (this.notices_dialog) this.notices_dialog.hide();
		const item = this.data.item;
		const message = __(
			"Stock values for {0} in {1} will be recalculated from {2} onward. Later entries and their accounting entries may change. The repost runs in the background.",
			[
				this.b(frappe.utils.escape_html(item.item_name || item.item_code)),
				this.b(frappe.utils.escape_html(this.data.warehouse)),
				this.b(this.repost_start_label(start)),
			]
		);
		frappe.confirm(message, () => this.repost(start));
	}

	repost(start) {
		return this.fetch("repost_from_entry", { entry: start.name }).then(
			(name) => {
				const link = this.doc_link("Repost Item Valuation", name);
				frappe.show_alert({ message: __("Repost {0} queued", [link]), indicator: "green" });
				this.load(this.args);
			},
			() => null
		);
	}

	load_older() {
		const oldest = this.data.entries[0];
		const key = this.key;
		return this.fetch("get_valuation_steps", {
			item_code: this.data.item.item_code,
			warehouse: this.data.warehouse,
			before: oldest.name,
			...this.focus_args(),
		}).then(
			(data) => {
				if (this.key !== key) return;
				const top = this.step_top(oldest.name);
				this.data.entries = data.entries.concat(this.data.entries);
				this.data.opening = data.opening;
				this.data.has_earlier = data.has_earlier;
				this.render();
				this.keep_step_at(oldest.name, top);
			},
			() => frappe.show_alert({ message: __("Could not load older entries"), indicator: "red" })
		);
	}

	fetch(method, args) {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: `erpnext.stock.page.valuation_rate_breakdown.valuation_rate_breakdown.${method}`,
				args,
				callback: (r) => resolve(r.message),
				error: reject,
			});
		});
	}

	focus_args() {
		const focus = this.data.focus;
		return focus ? { [focus.field]: focus.name } : {};
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

	render() {
		const data = this.data;
		this.container.empty();
		if (!data.entries.length) {
			this.container.append(this.no_entries_state());
			return;
		}
		const repost = this.repost_alert();
		if (repost) this.container.append(repost);
		this.container.append(this.summary());
		this.update_notices();
		this.container.append(`<div class="vrb-section-title">${__("How we got here, newest first")}</div>`);
		this.container.append(this.timeline());
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
		if (this.data.repost_status === "pending") {
			return frappe.ui.alert({
				title: __("Stock values are being recalculated"),
				description: __(
					"A recalculation is queued for this item and warehouse. The rates below may change once it finishes."
				),
				theme: "amber",
			});
		}
		if (this.data.repost_status !== "failed") return null;
		return frappe.ui.alert({
			title: __("Stock values could not be recalculated"),
			description: __(
				"The last recalculation for this item and warehouse failed, so the rates below may be out of date."
			),
			theme: "red",
			primary_action: {
				label: __("View Repost Item Valuation"),
				onclick: () => frappe.set_route("List", "Repost Item Valuation", { status: "Failed" }),
			},
		});
	}

	summary() {
		const item = this.data.item;
		const card = $(`
			<div class="vrb-card vrb-summary">
				<div class="vrb-summary-head">
					<div class="vrb-summary-text">
						<div class="vrb-item ellipsis">
							${frappe.utils.escape_html(item.item_name || item.item_code)}
							<span class="vrb-muted">${frappe.utils.escape_html(item.item_code)}</span>
						</div>
						<div class="vrb-lead">${this.summary_sentence()}</div>
					</div>
					<div class="vrb-summary-side">
						<span class="vrb-notices-slot"></span>
						${frappe.ui.badge.html({ label: this.method_label(), theme: "blue", size: "lg" })}
					</div>
				</div>
				${this.figures_html()}
				${this.stock_parts_html()}
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
		if (this.data.focus) return this.focus_sentence(warehouse);
		if (this.data.item.valued_by && last.qty_after > 0) {
			const holds = __("On {0}, {1} holds {2} worth {3}.", [
				date,
				warehouse,
				this.b(this.qty(last.qty_after)),
				this.b(this.money(last.value_after)),
			]);
			const why = {
				serial: __(
					"Each serial number keeps the value it came in at, so the stock value is the sum of those values."
				),
				batch_own: __(
					"Each batch keeps its own value per unit, so the stock value is the sum of the batches."
				),
				batch_mixed: __(
					"Some batches keep their own value per unit and the rest share one, so the stock value is the sum of both."
				),
				batch_shared: __("Its batches share one value per unit."),
			}[this.guide_key()];
			return `${holds} ${why}`;
		}
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

	focus_sentence(warehouse) {
		const focus = this.data.focus;
		if (focus.field === "batch_no") {
			const batch = this.b(this.doc_link("Batch", focus.name, focus.label));
			if (focus.qty <= 0) return __("Batch {0} has no stock left in {1}.", [batch, warehouse]);
			return __("Batch {0} in {1} holds {2} worth {3}, so each unit is valued at {4}.", [
				batch,
				warehouse,
				this.b(this.qty(focus.qty)),
				this.b(this.money(focus.value)),
				this.b(this.money(focus.rate)),
			]);
		}
		const serial = this.b(this.doc_link("Serial No", focus.name, focus.label));
		if (focus.qty > 0) {
			return __("Serial number {0} is in {1}, valued at {2}. It keeps this value until it goes out.", [
				serial,
				warehouse,
				this.b(this.money(focus.value)),
			]);
		}
		const gone = __("Serial number {0} is no longer in {1}.", [serial, warehouse]);
		if (this.same(focus.value, 0)) return gone;
		return `${gone} ${__(
			"It left {0} of value behind, because it went out at a different value than it came in at.",
			[this.b(this.money(focus.value))]
		)}`;
	}

	figures_html() {
		const focus = this.data.focus;
		if (focus && focus.field === "serial_no") return "";
		const last = this.last_entry();
		const figure = (label, value, align) => `
			<div class="vrb-figure ${align}">
				<div class="vrb-figure-label">${label}</div>
				<div class="vrb-figure-value ellipsis">${value}</div>
			</div>
		`;
		return `
			<div class="vrb-figures">
				${figure(focus ? __("Units in batch") : __("Units in stock"), this.qty(last.qty_after), "")}
				${figure(focus ? __("Batch value") : __("Stock value"), this.money(last.value_after), "text-right")}
				${figure(
					this.is_pooled_view() ? __("Average per unit") : __("Value per unit"),
					this.money(last.rate_after),
					"text-right"
				)}
			</div>
		`;
	}

	method_label() {
		const labels = {
			batch_own: __("Valued batch by batch"),
			batch_mixed: __("Valued batch by batch"),
			batch_shared: __("Batches share one value"),
			serial: __("Valued per serial number"),
		};
		return labels[this.guide_key()] || __("Valued by {0}", [__(this.data.item.valuation_method)]);
	}

	guide_key() {
		const item = this.data.item;
		if (item.valued_by === "batch") return `batch_${item.batch_valuation || "own"}`;
		return item.valued_by || item.valuation_method;
	}

	guide_html() {
		const item = this.data.item;
		const guide = this.method_guides()[this.guide_key()];
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
			batch_shared: {
				short: __("All batches share one value per unit."),
				steps: [
					__("These batches are not valued batch by batch, so they share one value per unit."),
					__("When stock comes into any batch, its value is added to the shared value."),
					__(
						"When stock goes out of any batch, it leaves at the shared value per unit, not at the rate that batch was bought at."
					),
				],
			},
			batch_mixed: {
				short: __("Some batches keep their own value per unit, the rest share one."),
				steps: [
					__(
						"A batch valued batch by batch keeps its own value per unit, and stock leaves it at that value."
					),
					__(
						"Batches not valued batch by batch share one value per unit, and stock leaves them at that shared value."
					),
					__(
						"The average per unit is the value of all batches divided by all units. Reports show this average, but stock goes out at a batch's own value or at the shared value."
					),
				],
			},
			batch_own: {
				short: __("Each batch keeps its own value per unit."),
				steps: [
					__("When stock comes into a batch, its value is added to that batch only."),
					__(
						"When stock goes out of a batch, it leaves at that batch's value per unit: the batch's value divided by its units."
					),
					__(
						"The average per unit is the value of all batches divided by all units. Reports show this average, but stock never goes out at it."
					),
				],
			},
			serial: {
				short: __("Each serial number keeps the value it came in at."),
				steps: [
					__("When a serial number comes in, it keeps the value it came in at."),
					__("When it goes out, it leaves at that same value, whatever the average is."),
					__(
						"The average per unit is the value of all serial numbers in stock divided by their count. Reports show this average, but stock never goes out at it."
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
		[...this.data.entries].reverse().forEach((entry) => list.append(this.entry_step(entry)));
		list.append(this.start_step());
		return list;
	}

	start_step() {
		const opening = this.data.opening;
		const focus = this.data.focus;
		const empty = focus
			? __("Start: {0} had nothing in this warehouse", [frappe.utils.escape_html(focus.label)])
			: __("Start: no stock in this warehouse");
		const title = opening.qty
			? __("Start: {0} worth {1}", [this.qty(opening.qty), this.money(opening.value)])
			: empty;
		let hint = __("The explanation starts from the last time stock was zero or was counted.");
		if (focus)
			hint = __("This is the whole history of {0} in this warehouse.", [
				frappe.utils.escape_html(focus.label),
			]);
		if (this.data.has_earlier)
			hint = __("Older entries are not shown. The explanation picks up from here.");
		const step = $(`
			<div class="vrb-step">
				<div class="vrb-rail">
					<div class="vrb-dot is-gray">${frappe.utils.icon("flag", "sm")}</div>
				</div>
				<div class="vrb-step-body vrb-start">
					<div class="vrb-start-title">${title}</div>
					<div class="vrb-muted">${hint}</div>
				</div>
			</div>
		`);
		if (this.data.has_earlier) step.find(".vrb-start").append(this.older_button());
		return step;
	}

	older_button() {
		return $('<div class="vrb-earlier"></div>').append(
			frappe.ui.button({
				label: __("Show older entries"),
				variant: "subtle",
				icon: "history",
				onclick: () => this.load_older(),
			})
		);
	}

	entry_step(entry) {
		const focus = entry.name === this.focus;
		const step = $(`
			<div class="vrb-step" data-entry="${frappe.utils.escape_html(entry.name)}">
				<div class="vrb-rail">
					${this.dot_html(entry)}
					<div class="vrb-line"></div>
				</div>
				<div class="vrb-step-body">
					${this.entry_header_html(entry)}
					<div class="vrb-card vrb-explain${focus ? " is-focus is-open" : ""}${
			entry.ledger_problems ? " is-wrong" : ""
		}">
						${focus ? this.opened_html() : ""}
						<div class="vrb-lead">${this.headline(entry)}</div>
						<div class="vrb-outcome">${this.outcome_text(entry)}</div>
						${this.notes_html(entry)}
						${this.details_html(entry)}
						${this.details_toggle_html(focus)}
					</div>
				</div>
			</div>
		`);
		for (const note of [this.rate_note(entry), this.changed_note(entry)]) {
			if (note) step.find(".vrb-details").append(frappe.ui.alert(note));
		}
		if (entry === this.repost_target()) step.find(".vrb-details").before(this.repost_block(entry));
		return step;
	}

	details_html(entry) {
		return `
			<div class="vrb-details">
				${this.entered_late_html(entry)}
				${this.parts_html(entry)}
				${this.math_html(entry)}
				${this.is_queue() ? this.lots_html(entry) : ""}
				${this.result_html(entry)}
			</div>
		`;
	}

	details_toggle_html(open) {
		return `
			<button class="vrb-details-toggle" aria-expanded="${open}">
				<span class="vrb-when-closed">${__("Show calculation")}</span>
				<span class="vrb-when-open">${__("Hide calculation")}</span>
				${frappe.utils.icon("chevron-down", "sm")}
			</button>
		`;
	}

	toggle_open(event, selector) {
		const button = $(event.currentTarget);
		const open = button.closest(selector).toggleClass("is-open").hasClass("is-open");
		button.attr("aria-expanded", open);
		return open;
	}

	outcome_text(entry) {
		if (entry.qty_after <= 0) return this.result_text(entry);
		const holds = __("Now {0} worth {1}", [this.qty(entry.qty_after), this.money(entry.value_after)]);
		if (this.is_pooled_view()) return `${holds}.`;
		const rate = this.b(this.money(entry.rate_after));
		if (entry.qty_before > 0 && !this.same(entry.rate_after, entry.rate_before)) {
			return __("{0}, so {1} per unit, was {2}.", [holds, rate, this.money(entry.rate_before)]);
		}
		return __("{0}, so {1} per unit.", [holds, rate]);
	}

	notes_html(entry) {
		const changed = (entry.changed_by || []).length && !entry.awaiting_recalculation;
		const lines = [
			entry.ledger_problems
				? this.note_line(this.problem_text(entry, entry.ledger_problems[0]), "is-red")
				: "",
			entry.awaiting_recalculation
				? this.note_line(__("Waiting for recalculation. These figures are not final yet."), "is-blue")
				: "",
			changed && this.rate_changed(entry) ? this.note_line(this.changed_title(entry), "is-amber") : "",
			this.rate_note(entry) ? this.note_line(this.rate_note(entry).title, "is-amber") : "",
			...(entry.parts || []).map((part) => this.mismatch_line(part)),
		];
		return lines.filter(Boolean).slice(0, 3).join("");
	}

	problem_text(entry, problem) {
		const texts = {
			qty: () =>
				__("Units don't add up: should be {0}, the ledger says {1}.", [
					this.qty(problem.expected),
					this.qty(problem.actual),
				]),
			value: () =>
				__("Value doesn't add up: should be {0}, the ledger says {1}.", [
					this.money(problem.expected),
					this.money(problem.actual),
				]),
			rate: () =>
				__("Value per unit × units gives {0}, but the ledger says {1}.", [
					this.money(problem.expected),
					this.money(problem.actual),
				]),
			lots: () =>
				__("The lots add up to {0} worth {1}, not {2} worth {3}.", [
					this.qty(problem.qty),
					this.money(problem.value),
					this.qty(entry.qty_after),
					this.money(entry.value_after),
				]),
			outgoing_rate: () =>
				__("Went out at {0} each, not the average {1}.", [
					this.money(problem.actual),
					this.money(problem.expected),
				]),
		};
		return texts[problem.check]();
	}

	note_line(text, tone) {
		const plain = frappe.utils.escape_html($("<div>").html(text).text());
		const icon = frappe.utils.icon(tone === "is-blue" ? "info" : "triangle-alert", "sm");
		return `<div class="vrb-note ${tone}" title="${plain}">${icon}<span class="ellipsis">${text}</span></div>`;
	}

	rate_changed(entry) {
		if (entry.rate_after_when_entered == null) return false;
		if (entry.kind === "out" && !this.same(entry.rate, entry.rate_when_entered)) return true;
		return !this.same(entry.rate_after, entry.rate_after_when_entered);
	}

	mismatch_line(part) {
		if (part.batch_no && this.batch_mismatch(part)) {
			return this.note_line(
				__("Batch {0} went out at {1}, not its own {2}.", [
					frappe.utils.escape_html(part.batch_id),
					this.plain_money(part.rate),
					this.plain_money(this.per_unit(part.qty_before, part.value_before)),
				]),
				"is-amber"
			);
		}
		if (!part.batch_no && this.serial_mismatch(part)) {
			return this.note_line(`${this.part_label(part)}: ${this.serial_source(part)}`, "is-amber");
		}
		return "";
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
				<span class="vrb-entry-doc">
					<span class="vrb-voucher ellipsis">${this.voucher_label(entry)}</span>
					<span class="vrb-doc ellipsis">${this.doc_link(entry.voucher_type, entry.voucher_no)}</span>
				</span>
				<span class="vrb-entry-status">${this.status_badges(entry)}</span>
				<span class="vrb-entry-qty">${this.qty_badge(entry)}</span>
			</div>
		`;
	}

	status_badges(entry) {
		return [
			entry.later_dated_count ? frappe.ui.badge.html({ label: __("Backdated"), theme: "amber" }) : "",
			entry.ledger_problems ? frappe.ui.badge.html({ label: __("Needs repost"), theme: "red" }) : "",
			this.change_badge(entry),
		].join("");
	}

	change_badge(entry) {
		if (!(entry.changed_by || []).length) return "";
		return entry.awaiting_recalculation
			? frappe.ui.badge.html({ label: __("Waiting"), theme: "blue" })
			: frappe.ui.badge.html({ label: __("Recalculated") });
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
		if (this.data.item.valued_by) return this.own_value_inward(entry);
		const qty = this.b(this.qty(entry.qty));
		const rate = this.b(this.money(entry.rate));
		const lead = entry.is_return
			? __("Received {0} back against {1} at {2}.", [qty, this.return_link(entry), rate])
			: __("Received {0} at {1}.", [qty, rate]);
		const parts = [lead, entry.is_return ? this.return_in_note(entry) : this.inward_reason(entry)];
		if (!entry.rate) parts.push(__("This receipt has a zero rate, so it adds no value."));
		return parts.filter(Boolean).join(" ");
	}

	own_value_inward(entry) {
		const parts = entry.parts || [];
		const qty = this.b(this.qty(entry.qty));
		const lead = entry.is_return
			? __("Received {0} back against {1}", [qty, this.return_link(entry)])
			: __("Received {0}", [qty]);
		const total = this.b(this.money(entry.value_change));
		if (!parts.length) return __("{0} worth {1}.", [lead, total]);
		if (this.is_serial()) {
			if (parts.length === 1) {
				return __("{0} at {1} each.", [lead, this.b(this.money(parts[0].rate))]);
			}
			return __("{0} worth {1}.", [lead, total]);
		}
		if (parts.length === 1) {
			return __("{0} into batch {1} at {2} each.", [
				lead,
				this.batch_link(parts[0]),
				this.b(this.money(parts[0].rate)),
			]);
		}
		return __("{0} into {1} batches, worth {2}.", [lead, parts.length, total]);
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
		if (this.data.item.valued_by) return this.own_rate_headline(entry, lead);
		if (this.is_queue()) return `${lead}. ${this.lots_used_note(entry)}`;
		if (this.data.item.valuation_method === "Standard Cost") {
			return __("{0} at the standard cost, {1}.", [lead, rate]);
		}
		if (this.at_original_rate(entry)) return __("{0} at {1}, the rate it came in at.", [lead, rate]);
		return __("{0} at the current value per unit, {1}.", [lead, rate]);
	}

	own_rate_headline(entry, lead) {
		const parts = entry.parts || [];
		const total = this.b(this.money(Math.abs(entry.value_change)));
		if (!parts.length) return __("{0}, {1} in total.", [lead, total]);
		if (this.is_serial()) {
			if (parts.some((part) => this.serial_mismatch(part))) {
				return __("{0} for {1} in total.", [lead, total]);
			}
			if (parts.length === 1) {
				return __("{0} at {1} each, the value the serial number came in at.", [
					lead,
					this.b(this.money(parts[0].rate)),
				]);
			}
			return __("{0} at the value each serial number came in at, {1} in total.", [lead, total]);
		}
		if (parts.length !== 1) {
			return __("{0} from {1} batches, each at its own value per unit: {2} in total.", [
				lead,
				parts.length,
				total,
			]);
		}
		const part = parts[0];
		const rate = this.b(this.money(part.rate));
		return part.own_rate
			? __("{0} from batch {1} at {2} each, the batch's own value per unit.", [
					lead,
					this.batch_link(part),
					rate,
			  ])
			: __("{0} from batch {1} at {2} each, the value it shares with other batches.", [
					lead,
					this.batch_link(part),
					rate,
			  ]);
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
		if (this.is_pooled_view()) return this.together_html(entry);
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
		if (!entry.qty_after && !this.same(entry.value_after, 0)) {
			return __(
				"No units are left, but {0} of value stayed behind, because it went out at a different value than it came in at.",
				[this.b(this.money(entry.value_after))]
			);
		}
		if (!entry.qty_after) return __("No stock is left, so the stock value is {0}.", [this.money(0)]);
		const per_unit = this.is_pooled_view()
			? __("{0} average per unit", [this.money(entry.rate_after)])
			: __("{0} per unit", [this.money(entry.rate_after)]);
		const math = __("{0} ÷ {1} = {2}", [
			this.money(entry.value_after),
			this.qty(entry.qty_after),
			this.b(per_unit),
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
		if (!parts.length || (this.data.focus && !this.is_serial())) return "";
		if (this.data.focus) return this.focus_source_html(parts);
		const blocks = parts
			.slice(0, 8)
			.map((part) => (part.batch_no ? this.batch_block(part) : this.serial_rows(part)));
		const more = parts.length > 8 ? this.part_hint(__("+{0} more", [parts.length - 8])) : "";
		const css = this.is_serial() ? "vrb-parts" : "vrb-batches";
		return `<div class="${css}">${blocks.join("")}${more}</div>`;
	}

	batch_block(part) {
		const note = part.own_rate
			? __("Keeps its own value per unit")
			: __("Shares one value with other batches");
		const head = `<div class="vrb-part-head"><span class="ellipsis">${this.batch_link(
			part
		)}</span><span class="vrb-muted ellipsis">${note}</span></div>`;
		const change = this.math_row(
			part.qty > 0 ? __("In") : __("Out"),
			part.qty,
			part.rate,
			part.value,
			"change"
		);
		if (!part.own_rate)
			return `<div class="vrb-batch">${head}<div class="vrb-math">${change}</div></div>`;
		const rows = [
			this.math_row(
				__("Before"),
				part.qty_before,
				this.per_unit(part.qty_before, part.value_before),
				part.value_before
			),
			change,
			this.math_row(
				__("After"),
				part.qty_after,
				this.per_unit(part.qty_after, part.value_after),
				part.value_after,
				"total"
			),
		];
		const hint = this.batch_mismatch(part)
			? this.part_hint(
					__("Went out at {0}, not the batch's own {1}.", [
						this.plain_money(part.rate),
						this.plain_money(this.per_unit(part.qty_before, part.value_before)),
					]),
					"is-warning"
			  )
			: "";
		return `<div class="vrb-batch">${head}<div class="vrb-math">${rows.join("")}</div>${hint}</div>`;
	}

	focus_source_html(parts) {
		const hints = parts
			.filter((part) => part.qty < 0 && part.source_voucher_no)
			.map((part) =>
				this.part_hint(this.serial_source(part), this.serial_mismatch(part) ? "is-warning" : "")
			);
		return hints.length ? `<div class="vrb-focus-source">${hints.join("")}</div>` : "";
	}

	serial_rows(part) {
		const row = this.part_row(this.part_label(part), part.qty, part.rate, part.value, "", true);
		if (part.qty > 0 || !part.source_voucher_no) return row;
		return row + this.part_hint(this.serial_source(part), this.serial_mismatch(part) ? "is-warning" : "");
	}

	part_row(label, qty, rate, value, css, signed) {
		const tone = signed ? (qty > 0 ? "vrb-in" : "vrb-out") : "";
		return `
			<div class="vrb-part-row ${css || ""}">
				<span class="ellipsis">${label}</span>
				<span class="text-right ${tone}">${signed ? this.signed_qty(qty) : this.qty(qty)}</span>
				<span class="text-right vrb-muted vrb-nowrap">${rate == null ? "" : `× ${this.money(rate)}`}</span>
				<span class="text-right ${tone}">${signed ? this.signed_money(value) : this.money(value)}</span>
			</div>
		`;
	}

	part_label(part) {
		const labels = part.serial_labels || part.serial_nos;
		const serials = labels.map((serial_no) => frappe.utils.escape_html(serial_no)).join(", ");
		return part.more ? __("{0} and {1} more", [serials, part.more]) : serials;
	}

	serial_source(part) {
		const returns = {
			"Delivery Note": "Sales Return",
			"Sales Invoice": "Sales Return",
			"Purchase Receipt": "Purchase Return",
			"Purchase Invoice": "Purchase Return",
		};
		const doctype = part.source_is_return ? returns[part.source_voucher_type] : part.source_voucher_type;
		const args = [
			__(doctype || part.source_voucher_type),
			frappe.utils.escape_html(part.source_voucher_no),
			frappe.datetime.str_to_user(part.source_date),
			this.plain_money(part.source_rate),
		];
		if (this.serial_mismatch(part)) {
			args.push(this.plain_money(part.rate));
			return part.source_is_return
				? __("Came back through {0} {1} on {2} at {3}, but went out at {4}", args)
				: __("Came in through {0} {1} on {2} at {3}, but went out at {4}", args);
		}
		return part.source_is_return
			? __("Came back through {0} {1} on {2} at {3}", args)
			: __("Came in through {0} {1} on {2} at {3}", args);
	}

	serial_mismatch(part) {
		return part.source_rate != null && part.qty < 0 && !this.same(part.source_rate, part.rate);
	}

	batch_mismatch(part) {
		return (
			part.own_rate &&
			part.qty < 0 &&
			part.qty_before > 0 &&
			!this.same(part.rate, this.per_unit(part.qty_before, part.value_before))
		);
	}

	together_html(entry) {
		const change_labels = {
			in: __("In"),
			out: __("Out"),
			reconciliation: __("Count"),
			revaluation: __("Change"),
		};
		const title = this.is_serial() ? __("All serial numbers together") : __("All batches together");
		const rows = [
			this.plain_row(__("Before"), entry.qty_before, entry.value_before),
			this.plain_row(
				change_labels[entry.kind],
				entry.qty_after - entry.qty_before,
				entry.value_after - entry.value_before,
				"change"
			),
			this.plain_row(__("After"), entry.qty_after, entry.value_after, "total"),
		];
		return `<div><div class="vrb-subtitle">${title}</div><div class="vrb-math is-plain">${rows.join(
			""
		)}</div></div>`;
	}

	plain_row(label, qty, value, type) {
		const change = type === "change";
		const tone = change ? (qty > 0 || (!qty && value > 0) ? "vrb-in" : "vrb-out") : "";
		return `
			<div class="vrb-math-row${type === "total" ? " is-total" : ""}">
				<span class="vrb-muted">${label}</span>
				<span class="text-right ${tone}">${change ? this.signed_qty(qty) : this.qty(qty)}</span>
				<span class="text-right ${tone}">${change ? this.signed_money(value) : this.money(value)}</span>
			</div>
		`;
	}

	stock_parts_html() {
		if (!this.is_pooled_view()) return "";
		const body = this.stock_parts_body();
		if (!body) return "";
		const open = this.stock_parts_open;
		return `
			<div class="vrb-stock-parts${open ? " is-open" : ""}">
				<button class="vrb-stock-toggle" aria-expanded="${open}">
					<span class="vrb-subtitle">${__("What the stock is made of")}</span>
					<span class="vrb-stock-chevron">${frappe.utils.icon("chevron-down", "sm")}</span>
				</button>
				<div class="vrb-stock-body">${body}</div>
			</div>
		`;
	}

	stock_parts_body() {
		if (this.breakdown_state === "loading") {
			return frappe.ui.skeleton.html({ width: "100%", height: "96px" });
		}
		if (this.breakdown_state === "failed") {
			const text = __("Could not work out what the stock is made of. Reload the page to try again.");
			return `<div class="vrb-muted">${text}</div>`;
		}
		const parts = this.data.stock_parts || [];
		if (!parts.length) return "";
		const rows = parts
			.slice(0, PARTS_LISTED)
			.map((part, i) =>
				this.part_row(
					this.stock_part_label(part),
					part.qty,
					part.rate,
					part.value,
					i < PARTS_SHOWN ? "" : "is-extra"
				)
			);
		const qty = parts.reduce((sum, part) => sum + part.qty, 0);
		const value = parts.reduce((sum, part) => sum + part.value, 0);
		const total = this.part_row(`<b>${__("Adds up to")}</b>`, qty, null, value, "is-total");
		return `
			<div class="vrb-parts vrb-stock-list">${rows.join("")}${this.more_parts_html(parts)}${total}</div>
			${this.average_html()}
		`;
	}

	more_parts_html(parts) {
		if (parts.length <= PARTS_SHOWN) return "";
		const hidden = parts.length - PARTS_LISTED;
		const unlisted = hidden > 0 ? this.part_hint(__("+{0} more", [hidden]), "vrb-when-open") : "";
		return `
			${unlisted}
			<button class="vrb-more-toggle" aria-expanded="false">
				<span class="vrb-when-closed">${__("Show all {0}", [parts.length])}</span>
				<span class="vrb-when-open">${__("Show fewer")}</span>
			</button>
		`;
	}

	stock_part_label(part) {
		if (part.shared) {
			return part.count === 1
				? __("1 batch that shares one value")
				: __("{0} batches that share one value", [part.count]);
		}
		if (part.batch_no) return this.batch_link(part);
		const count = !this.is_serial()
			? ""
			: flt(part.qty) === 1
			? __("1 serial number")
			: __("{0} serial numbers", [this.number(part.qty)]);
		return `${count} <span class="vrb-muted">${this.part_label(part)}</span>`;
	}

	average_html() {
		const last = this.last_entry();
		if (last.qty_after <= 0) return "";
		const math = __("{0} ÷ {1} = {2}", [
			this.money(last.value_after),
			this.qty(last.qty_after),
			this.b(__("{0} average per unit", [this.money(last.rate_after)])),
		]);
		const takes = this.is_serial()
			? __(
					"Reports such as Stock Balance show this average, but a delivery or issue uses the value of the serial number it takes."
			  )
			: __(
					"Reports such as Stock Balance show this average, but a delivery or issue uses the value per unit of the batch it takes from."
			  );
		return `<div class="vrb-result">${frappe.utils.icon(
			"equal",
			"sm"
		)}<span>${math}. ${takes}</span></div>`;
	}

	gap_alert() {
		const gap = this.data.stock_gap;
		if (!gap) return null;
		const noun = this.is_serial() ? __("serial numbers") : __("batches");
		const title =
			gap.gap > 0
				? __("The stock value is {0} more than its {1} add up to", [this.plain_money(gap.gap), noun])
				: __("The stock value is {0} less than its {1} add up to", [
						this.plain_money(Math.abs(gap.gap)),
						noun,
				  ]);
		const lines = this.is_serial()
			? this.serial_gap_lines(gap)
			: [
					__(
						"The batch values recorded on each entry add up to a different total than the stock ledger."
					),
			  ];
		return frappe.ui.alert({ title, description: lines.join(" "), theme: "amber" });
	}

	serial_gap_lines(gap) {
		const lines = [__("This happens when stock goes out at a different value than it came in at.")];
		lines.push(...gap.causes.map((cause) => this.cause_text(cause)));
		if (gap.more_causes) lines.push(__("{0} more did the same.", [this.entries_count(gap.more_causes)]));
		const untraced = gap.gap - gap.explained;
		if (!this.same(untraced, 0)) {
			lines.push(
				__("The other {0} comes from older entries this page cannot trace.", [
					this.plain_money(Math.abs(untraced)),
				])
			);
		}
		return lines;
	}

	cause_text(cause) {
		return __("{0} {1} on {2} sent out {3} at {4} each instead of {5}.", [
			__(cause.voucher_type),
			cause.voucher_no,
			frappe.datetime.str_to_user(cause.posting_date),
			this.join_list(cause.serial_labels || cause.serial_nos),
			this.plain_money(cause.actual),
			this.plain_money(cause.expected),
		]);
	}

	batch_link(part) {
		return this.doc_link("Batch", part.batch_no, part.batch_id);
	}

	per_unit(qty, value) {
		return flt(qty) ? value / qty : 0;
	}

	is_pooled_view() {
		return Boolean(this.data.item.valued_by && !this.data.focus);
	}

	is_serial() {
		return this.data.item.valued_by === "serial";
	}

	part_hint(text, css) {
		return `<div class="vrb-part-hint ellipsis ${css || ""}" title="${frappe.utils.escape_html(
			text
		)}">${text}</div>`;
	}

	backdated_alert() {
		const entries = this.data.entries;
		const backdated = entries.filter((entry) => entry.later_dated_count).length;
		const changed = entries.filter((entry) => (entry.changed_by || []).length).length;
		if (!backdated && !changed) return null;
		const waiting = entries.filter((entry) => entry.awaiting_recalculation).length;
		const lines = [
			changed === 1
				? __("1 entry below was recalculated because of it.")
				: __("{0} entries below were recalculated because of it.", [changed]),
		];
		if (waiting) lines.push(__("{0} still waiting, so their figures are not final yet.", [waiting]));
		if (!backdated)
			lines[0] = __("Entries added or cancelled with an earlier date changed {0} below.", [
				this.entries_count(changed),
			]);
		return frappe.ui.alert({
			title:
				backdated === 1
					? __("1 entry was posted with an earlier date")
					: backdated
					? __("{0} entries were posted with an earlier date", [backdated])
					: __("Some entries were recalculated"),
			description: lines.join(" "),
			theme: "blue",
		});
	}

	entered_late_html(entry) {
		if (!entry.later_dated_count) return "";
		const outcome = {
			pending: __("Those entries are waiting to be recalculated."),
			failed: __("Recalculating those entries failed."),
		}[this.data.repost_status];
		const text = __("Entered on {0}, after {1} with a later date. {2}", [
			this.user_datetime(entry.entered_on),
			this.entries_count(entry.later_dated_count),
			outcome || __("Those entries were recalculated."),
		]);
		return `<div class="vrb-opened">${frappe.utils.icon("history", "xs")} ${text}</div>`;
	}

	changed_note(entry) {
		const changes = entry.changed_by || [];
		if (!changes.length) return null;
		if (entry.awaiting_recalculation) return this.waiting_note(entry, changes);
		return {
			theme: "amber",
			title: this.changed_title(entry),
			description: __("Entered on {0}. Changed later by: {1}.", [
				this.user_datetime(entry.entered_on),
				this.change_list(changes),
			]),
		};
	}

	waiting_note(entry, changes) {
		return {
			theme: "blue",
			title: __("Waiting for recalculation after an earlier-dated entry"),
			description: __(
				"Entered on {0}. Until the recalculation runs, the figures above are not final. It will take these into account: {1}.",
				[this.user_datetime(entry.entered_on), this.change_list(changes)]
			),
		};
	}

	entries_count(count) {
		return count === 1 ? __("1 entry") : __("{0} entries", [count]);
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

	step_top(name) {
		const step = this.step_element(name);
		return step ? step.getBoundingClientRect().top : null;
	}

	keep_step_at(name, top) {
		const step = this.step_element(name);
		if (step && top !== null) window.scrollBy(0, step.getBoundingClientRect().top - top);
	}

	step_element(name) {
		return this.container.find(`.vrb-step[data-entry="${CSS.escape(name)}"]`)[0];
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
			.vrb-summary-side { display: flex; align-items: center; gap: var(--margin-sm); flex-shrink: 0; }
			.vrb-notices-slot:empty { display: none; }
			.vrb-notices-button.is-amber .icon { stroke: var(--ink-amber-7); }
			.vrb-notices-button.is-blue .icon { stroke: var(--ink-blue-7); }
			.vrb-notices-button.is-red .icon { stroke: var(--ink-red-6); }
			.vrb-notices { display: flex; flex-direction: column; gap: var(--margin-sm); }
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
				.vrb { padding: 0 var(--padding-md); }
				.vrb-summary-head { flex-direction: column; gap: var(--margin-sm); }
				.vrb-figures { grid-template-columns: minmax(0, 1fr); }
				.vrb-figure { display: flex; align-items: center; justify-content: space-between; gap: var(--margin-sm); }
				.vrb-figure + .vrb-figure { border-left: 0; border-top: 1px solid var(--outline-gray-1); }
				.vrb-figure-value { margin-top: 0; font-size: var(--text-lg); }
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
			.vrb-entry-doc { display: flex; align-items: center; gap: var(--margin-sm); flex: 1; min-width: 0; }
			.vrb-entry-status, .vrb-entry-qty { display: flex; align-items: center; gap: var(--margin-sm); flex-shrink: 0; }
			.vrb-entry-status:empty { display: none; }
			.vrb-explain { margin-top: var(--margin-sm); padding: var(--padding-md); display: flex; flex-direction: column; gap: var(--margin-xs); }
			.vrb-outcome { font-size: var(--text-sm); line-height: 1.6; color: var(--ink-gray-6); }
			.vrb-note { display: flex; align-items: center; gap: 6px; height: 24px; min-width: 0; font-size: var(--text-sm); }
			.vrb-note .icon { flex-shrink: 0; stroke: currentColor; }
			.vrb-note.is-amber { color: var(--ink-amber-7); }
			.vrb-note.is-blue { color: var(--ink-blue-7); }
			.vrb-note.is-red { color: var(--ink-red-6); }
			.vrb-explain.is-wrong { border-color: var(--outline-red-2); }
			.vrb-repost { display: flex; flex-direction: column; align-items: flex-start; gap: var(--margin-xs); min-width: 0; margin-top: 2px; font-size: var(--text-sm); }
			.vrb-repost .vrb-muted { max-width: 100%; }
			.vrb-details { display: none; flex-direction: column; gap: var(--margin-md); margin-top: var(--margin-sm); padding-top: var(--padding-md); border-top: 1px solid var(--outline-gray-1); }
			.vrb-explain.is-open .vrb-details { display: flex; }
			.vrb-details-toggle, .vrb-more-toggle { display: inline-flex; align-items: center; gap: 4px; align-self: flex-start; height: 24px; margin-top: 2px; padding: 0; background: none; border: 0; font-size: var(--text-sm); color: var(--ink-gray-6); }
			.vrb-details-toggle:hover, .vrb-more-toggle:hover { color: var(--ink-gray-8); }
			.vrb-details-toggle .icon { stroke: currentColor; transition: transform 0.15s; }
			.vrb-explain.is-open .vrb-details-toggle .icon { transform: rotate(180deg); }
			.vrb-explain:not(.is-open) .vrb-details-toggle .vrb-when-open, .vrb-explain.is-open .vrb-details-toggle .vrb-when-closed { display: none; }
			.vrb-stock-list:not(.is-open) .vrb-when-open, .vrb-stock-list.is-open .vrb-when-closed, .vrb-stock-list:not(.is-open) .is-extra { display: none; }
			.vrb-explain .vrb-lead { margin-top: 0; }
			.vrb-explain .vrb-opened { margin-bottom: var(--margin-xs); }
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
			.vrb-part-hint.is-warning { color: var(--ink-amber-7); }
			.vrb-focus-source .vrb-part-hint { margin-top: 0; font-size: var(--text-sm); }
			.vrb-part-row.is-total { border-top: 1px solid var(--outline-gray-2); color: var(--ink-gray-9); font-weight: 600; }
			.vrb-batches { display: flex; flex-direction: column; gap: var(--margin-md); }
			.vrb-batch { display: flex; flex-direction: column; gap: 4px; }
			.vrb-batch .vrb-part-hint { margin-top: 0; }
			.vrb-part-head { display: flex; align-items: center; gap: var(--margin-sm); height: 24px; min-width: 0; font-size: var(--text-sm); }
			.vrb-part-head > :first-child { flex-shrink: 0; max-width: 50%; font-weight: 500; }
			.vrb-subtitle { margin-bottom: 4px; font-size: var(--text-sm); font-weight: 500; color: var(--ink-gray-7); }
			.vrb-stock-parts { display: flex; flex-direction: column; gap: var(--margin-sm); padding: var(--padding-sm) var(--padding-lg); border-top: 1px solid var(--outline-gray-1); }
			.vrb-stock-parts .vrb-subtitle { margin-bottom: 0; }
			.vrb-stock-toggle { display: flex; align-items: center; gap: var(--margin-sm); width: 100%; min-height: 20px; padding: 0; background: none; border: 0; text-align: left; }
			.vrb-stock-toggle:hover .vrb-subtitle { color: var(--ink-gray-9); }
			.vrb-stock-chevron { margin-left: auto; display: flex; transition: transform 0.15s; }
			.vrb-stock-chevron .icon { stroke: var(--ink-gray-5); }
			.vrb-stock-parts.is-open .vrb-stock-chevron { transform: rotate(180deg); }
			.vrb-stock-body { display: flex; flex-direction: column; gap: var(--margin-sm); }
			.vrb-stock-parts:not(.is-open) .vrb-stock-body { display: none; }
			.vrb-math.is-plain .vrb-math-row { grid-template-columns: 64px 120px 140px; }
			.vrb-result { display: flex; align-items: flex-start; gap: var(--margin-sm); font-size: var(--text-sm); line-height: 1.5; color: var(--ink-gray-7); }
			.vrb-result .icon { flex-shrink: 0; margin: 2px 0 0; stroke: var(--ink-gray-5); }
			@media (max-width: 767px) {
				.vrb-entry-head { display: grid; grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "date qty" "doc doc" "status status"; grid-template-rows: 32px auto auto; row-gap: 2px; height: auto; }
				.vrb-date { grid-area: date; }
				.vrb-entry-qty { grid-area: qty; }
				.vrb-entry-doc { grid-area: doc; }
				.vrb-entry-status { grid-area: status; flex-wrap: wrap; row-gap: var(--margin-xs); }
				.vrb-math-row { grid-template-columns: 56px 96px 96px 112px; }
				.vrb-part-row { grid-template-columns: auto minmax(0, 1fr) auto; row-gap: 2px; height: auto; padding: 6px 0; }
				.vrb-part-row > :first-child { grid-column: 1 / -1; }
				.vrb-math.is-plain .vrb-math-row { grid-template-columns: 56px 96px 112px; }
			}
		`;
	}
};
