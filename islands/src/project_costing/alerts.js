const __ = window.__;

/**
 * The one alert above a running project's numbers, or null. Only what the user can act on gets an
 * alert: hours saved without a costing rate, which make every labour figure low. Budget state and
 * the on-hold note live in the Budget card.
 */
export function alertFor(view, format, { fix_rates }) {
	if (view.closed || !view.labour_understated) return null;
	const gaps = view.rate_gaps;
	return {
		theme: "amber",
		title: __("{0} h have no costing rate", [format.number(gaps.hours)]),
		description: gaps.estimate
			? __("That is {0} of logged hours, so labour cost is understated by about {1}.", [
					format.percent(gaps.share),
					format.short(gaps.estimate),
			  ])
			: __("That is {0} of logged hours, so labour cost is understated.", [format.percent(gaps.share)]),
		primaryAction: { label: __("Fix rates"), onClick: fix_rates },
	};
}

/** What the user's permissions leave out of the tab, for one quiet note at its foot. */
export function hiddenFor(view) {
	if (!view) return [];
	const access = view.access;
	const hidden = [];
	if (!access.labour) hidden.push(__("labour cost by person and activity"));
	if (!access.invoices) hidden.push(__("sales invoices"));
	if (!access.sales_orders) hidden.push(__("sales orders"));
	if (!access.purchases) hidden.push(__("cost by supplier"));
	if (!access.materials) hidden.push(__("cost by item"));
	return hidden;
}
