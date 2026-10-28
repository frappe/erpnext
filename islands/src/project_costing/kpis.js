const __ = window.__;

/**
 * The four headline numbers of the Costing tab, each captioned with what it is measured against.
 *
 * A running project shows cost and forecast against the estimate, then billing and margin. A
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
		const cost = this.cost(__("Cost to date"), __("{0} booked so far.", [this.sources()]));
		if (view.labour_understated) {
			cost.sub = __("+ ~{0} unpriced labour", [this.format.short(view.rate_gaps.estimate)]);
		}
		const items = [cost, this.forecast()];
		if (view.internal) return [...items, this.hours()];
		return [...items, this.billed(), this.margin(__("Gross margin"))];
	}

	completed() {
		const view = this.view;
		const items = [
			this.cost(
				__("Final cost"),
				__("{0} booked against the project, including entries after it closed.", [this.sources()])
			),
		];
		if (view.has_estimate) items.push(this.final_variance());
		if (view.internal) return [...items, this.hours()];
		items.push(this.billed(), this.margin(__("Final gross margin")));
		if (!view.has_estimate) items.push(this.hours());
		return items.slice(0, 4);
	}

	cancelled() {
		const view = this.view;
		const items = [
			this.cost(__("Cost incurred"), __("{0} booked against the project.", [this.sources()])),
		];
		if (view.internal) return [...items, this.hours()];
		return [
			...items,
			{ ...this.billed(), sub: __("Recovered before cancelling") },
			{
				label: __("Net result"),
				value: this.format.short(view.margin),
				sub: __("Billed − cost incurred"),
				hint: __("Billed − cost incurred. The same figure as the gross margin on the Project."),
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
				? __("{0} of {1} estimate", [format.percent(view.used_percent), format.short(view.estimate)])
				: __("No estimate set"),
			hint: view.has_estimate
				? `${hint} ${__("Measured against the estimated cost on the Project.")}`
				: hint,
		};
	}

	forecast() {
		const view = this.view;
		const started = view.percent_complete > 0;
		return {
			label: __("Forecast at completion"),
			value: started ? this.format.short(view.forecast) : "—",
			sub: this.forecast_caption(),
			hint: __("Cost to date ÷ % complete. Assumes the rest of the work costs the same per percent."),
		};
	}

	forecast_caption() {
		const view = this.view;
		const format = this.format;
		if (view.labour_understated) return __("Likely higher");
		if (!view.percent_complete) return __("Needs % complete");
		if (!view.has_estimate) return __("Based on {0}% complete", [view.percent_complete]);
		return view.variance > 0
			? __("{0} over estimate", [format.short(view.variance)])
			: __("{0} under estimate", [format.short(-view.variance)]);
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
			hint: __("Final cost − estimated cost."),
		};
	}

	billed() {
		const view = this.view;
		const format = this.format;
		return {
			label: __("Billed"),
			value: format.short(view.billed),
			sub: view.has_contract
				? __("{0} of {1} contract", [
						format.percent(view.billed_percent),
						format.short(view.contract),
				  ])
				: __("No sales order"),
			hint: __("Sales invoices for this project, net of returns, before tax."),
		};
	}

	margin(label) {
		const view = this.view;
		return {
			label,
			value: this.format.short(view.margin),
			sub: view.billed
				? __("{0} of billed", [this.format.percent(view.margin_percent, 1)])
				: __("Nothing billed yet"),
			hint: __("Billed − cost. The same figure as the gross margin on the Project."),
		};
	}

	hours() {
		const view = this.view;
		return {
			label: __("Hours logged"),
			value: this.format.number(view.hours),
			sub: view.access.labour ? __("At {0}/h average cost", [this.format.short(view.rate)]) : null,
			hint: __("Hours on submitted timesheets."),
		};
	}

	sources() {
		return this.view.hrms
			? __("Timesheet labour, non-stock purchases, materials consumed and expense claims")
			: __("Timesheet labour, non-stock purchases and materials consumed");
	}
}
