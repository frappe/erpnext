const __ = window.__;

/**
 * The four headline numbers of the Costing tab, each captioned with what it is measured against.
 *
 * A running project shows cost against the estimate, then billing and margin. A
 * completed one shows final figures, and a cancelled one what was spent and recovered.
 */
export function kpisFor(view, format) {
	const kpis = new HeadlineNumbers(view, format);
	if (view.phase === "cancelled") return kpis.cancelled();
	if (view.phase === "completed") return kpis.completed();
	return kpis.running();
}

class HeadlineNumbers {
	constructor(view, format) {
		this.view = view;
		this.format = format;
	}

	running() {
		const view = this.view;
		const cost = this.cost(__("Cost to date"), this.sources());
		if (view.labour_understated) Object.assign(cost, this.unpriced_labour(cost.hint));
		if (view.internal) return [cost, this.hours()];
		return [cost, this.billed(), this.margin(__("Gross margin"))];
	}

	completed() {
		const view = this.view;
		const items = [this.cost(__("Final cost"), this.sources())];
		if (view.has_estimate) items.push(this.final_variance());
		if (view.internal) return [...items, this.hours()];
		items.push(this.billed(), this.margin(__("Final gross margin")));
		if (!view.has_estimate) items.push(this.hours());
		return items.slice(0, 4);
	}

	cancelled() {
		const view = this.view;
		const items = [this.cost(__("Cost incurred"), this.sources())];
		if (view.internal) return [...items, this.hours()];
		return [
			...items,
			{ ...this.billed(), sub: __("Recovered before cancelling") },
			{
				label: __("Net result"),
				value: this.format.short(view.margin),
				hint: __("Billed − cost incurred"),
			},
		];
	}

	cost(label, hint) {
		const view = this.view;
		const format = this.format;
		return {
			label,
			value: format.short(view.cost),
			sub: view.has_estimate
				? __("{0} of estimate", [format.percent(view.used_percent)])
				: __("No estimate set"),
			hint,
		};
	}

	/**
	 * Hours saved without a costing rate add nothing to cost, so cost to date reads low. The
	 * caption says how many hours; the tooltip roughly how much labour that leaves out.
	 */
	unpriced_labour(hint) {
		const gaps = this.view.rate_gaps;
		return {
			sub: __("{0} h have no costing rate", [this.format.number(gaps.hours)]),
			hint: gaps.estimate
				? __("{0} · about {1} of labour not counted", [hint, this.format.short(gaps.estimate)])
				: hint,
		};
	}

	final_variance() {
		const view = this.view;
		const share = this.format.percent((Math.abs(view.variance) * 100) / view.estimate);
		return {
			label: __("Final variance"),
			value: (view.variance > 0 ? "+" : "") + this.format.short(view.variance),
			sub:
				view.variance > 0
					? __("{0} over the estimate", [share])
					: __("{0} under the estimate", [share]),
			hint: __("Final cost − estimated cost"),
		};
	}

	billed() {
		const view = this.view;
		const format = this.format;
		return {
			label: __("Billed"),
			value: format.short(view.billed),
			// without a sales order there is nothing to measure billing against, so no caption
			sub: view.has_contract ? __("{0} of sales orders", [format.percent(view.billed_percent)]) : null,
			hint: __("Sales invoices, net of returns"),
		};
	}

	margin(label) {
		const view = this.view;
		return {
			label,
			value: this.format.short(view.margin),
			sub: this.margin_caption(),
			hint:
				view.planned_margin == null
					? __("Billed − cost")
					: __("Billed − cost · Planned: sales orders − estimated cost"),
		};
	}

	// The planned margin is the benchmark when there is one; otherwise the share of billing.
	margin_caption() {
		const view = this.view;
		if (view.planned_margin != null) return __("Planned {0}", [this.format.short(view.planned_margin)]);
		return view.billed
			? __("{0} of billed", [this.format.percent(view.margin_percent, 1)])
			: __("Nothing billed yet");
	}

	hours() {
		const view = this.view;
		return {
			label: __("Hours logged"),
			value: this.format.number(view.hours),
			sub: view.access.labour ? __("{0}/h average", [this.format.short(view.rate)]) : null,
			hint: __("Hours on submitted timesheets"),
		};
	}

	sources() {
		return this.view.hrms
			? __("Timesheets + purchases + materials + expense claims")
			: __("Timesheets + purchases + materials");
	}
}
