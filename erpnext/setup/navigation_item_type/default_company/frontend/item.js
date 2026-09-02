// The `Default Company` kind: the one company this site works in.
//
// ERPNext's own kind, and the first one contributed by an app that is not frappe
// (frappe/frappe#42424). It exists because the eight framework kinds cannot express it:
// a `Record` item names its document, and the company's name is chosen during the setup
// wizard, so ERPNext has no name to ship. The destination is therefore computed here,
// out of a value the boot already carries.
//
// `boot.sysdefaults` is `frappe.defaults.get_defaults()`, which every desk v2 boot sends
// and which holds `company` on any ERPNext site past setup. Nothing new rides in boot for
// this, and the server half reads the same key when it decides who may see the item, so
// the two cannot point at different companies.

import { routeFor } from "@shell";

export default {
	render(item, { boot }) {
		const company = boot.sysdefaults?.company;

		// A site still in the setup wizard has no default company. The server drops the item
		// before boot for exactly this case; this is the second fence, and it is here rather
		// than trusted away because a renderer runs on whatever the browser was handed.
		if (!company) return null;

		return { to: routeFor("Company", company) };
	},

	// No authored label on the shipped row, deliberately: the company's name is the most
	// useful thing this item can say, and it is not knowable when the row is written. An
	// authored label would still win (frappe/frappe#42230), so a site that prefers a fixed
	// word can set one.
	label(item, { boot }) {
		return boot.sysdefaults?.company;
	},
};
