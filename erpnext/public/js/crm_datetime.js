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
			if (!d) {
				return "";
			}
			
			// Use frappe's system date format settings
			var user_date_format = frappe.boot && frappe.boot.sysdefaults ? 
				(frappe.boot.sysdefaults.date_format || "yyyy-mm-dd") : "yyyy-mm-dd";
			var user_language = frappe.boot && frappe.boot.lang ? 
				frappe.boot.lang : "en";
			
			// Convert to moment object
			var m = moment(d);
			
			// Format according to user's locale
			if (m._f && m._f.indexOf("HH") !== -1) {
				// For datetime values, include time
				return m.locale(user_language).format("Do MMMM YYYY, hh:mm A");
			} else {
				// For date values only
				return m.locale(user_language).format("Do MMMM YYYY");
			}
		};
	}
});