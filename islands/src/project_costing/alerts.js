const __ = window.__;

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
