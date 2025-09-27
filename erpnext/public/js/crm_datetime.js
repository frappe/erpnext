// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// Override frappe.datetime.global_date_format to use localized date formatting
// This fixes issue #49707 where dates were not being localized according to user's language settings

frappe.provide("frappe.datetime");

// Wait for frappe to be fully loaded
$(document).ready(function() {
	// Override frappe.datetime.global_date_format with localized version
	if (frappe.datetime) {
		// Store the original function if needed
		if (!frappe.datetime._original_global_date_format) {
			frappe.datetime._original_global_date_format = frappe.datetime.global_date_format;
		}
		
		// Override with localized version
		frappe.datetime.global_date_format = function (d) {
			if (!d) return "";

			const defaults = (frappe.boot && frappe.boot.sysdefaults) || {};
			const lang = (frappe.boot && frappe.boot.lang) || "en";
			const dateFmt = defaults.date_format || "yyyy-mm-dd";
			const timeFmt = defaults.time_format || "HH:mm";
			const tz = defaults.time_zone;
			const toTokens = (fmt) =>
				fmt.replace(/yyyy/g, "YYYY").replace(/mm/g, "MM").replace(/dd/g, "DD");
			const hasTime =
				(typeof d === "string" && /[ T]\d{1,2}:\d{2}/.test(d));

			// Prefer dayjs if available (used by Frappe v15), else fall back to moment
			try {
				const fmt = hasTime ? `${toTokens(dateFmt)} ${toTokens(timeFmt)}` : toTokens(dateFmt);
				if (typeof dayjs !== "undefined") {
					const m = (tz && dayjs.tz) ? dayjs.tz(d, tz) : dayjs(d);
					return m.locale(lang).format(fmt);
				}
				if (typeof moment !== "undefined") {
					const m = moment(d);
					return m.locale(lang).format(fmt);
				}
				// Last resort: original
				return frappe.datetime._original_global_date_format
					? frappe.datetime._original_global_date_format(d)
					: "";
			} catch (e) {
				return frappe.datetime._original_global_date_format
					? frappe.datetime._original_global_date_format(d)
					: "";
			}
		};
	}
});