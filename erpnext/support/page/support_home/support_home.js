// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

frappe.module_page["Support"] = [
	{
		title: frappe._("Top"),
		top: true,
		icon: "icon-copy",
		items: [
			{
				label: frappe._("Support Ticket"),
				description: frappe._("Support queries from customers."),
				doctype:"Support Ticket"
			},
			{
				label: frappe._("Customer Issue"),
				description: frappe._("Customer Issue against Serial No."),
				doctype:"Customer Issue"
			},
		]
	},

	{
		title: frappe._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: frappe._("Maintenance Schedule"),
				description: frappe._("Plan for maintenance visits."),
				doctype:"Maintenance Schedule"
			},
			{
				label: frappe._("Maintenance Visit"),
				description: frappe._("Visit report for maintenance call."),
				doctype:"Maintenance Visit"
			},
			{
				label: frappe._("Newsletter"),
				description: frappe._("Newsletters to contacts, leads."),
				doctype:"Newsletter"
			},
			{
				label: frappe._("Communication"),
				description: frappe._("Communication log."),
				doctype:"Communication"
			},
		]
	},
	{
		title: frappe._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: frappe._("Serial No"),
				description: frappe._("Single unit of an Item."),
				doctype:"Serial No"
			},
		]
	},
	{
		title: frappe._("Setup"),
		icon: "icon-cog",
		items: [
			{
				"route":"Form/Email Settings/Email Settings",
				"label":frappe._("Email Settings"),
				"description":frappe._("Setup to pull emails from support email account"),
				doctype: "Email Settings"
			},
		]
	},
	{
		title: frappe._("Analytics"),
		right: true,
		icon: "icon-bar-chart",
		items: [
			{
				"label":frappe._("Support Analytics"),
				page: "support-analytics"
			},
		]
	},
	{
		title: frappe._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":frappe._("Maintenance Schedules"),
				route: "query-report/Maintenance Schedules",
				doctype: "Maintenance Schedule"
			}
		]
	}
]

pscript['onload_support-home'] = function(wrapper) {
	frappe.views.moduleview.make(wrapper, "Support");
}
