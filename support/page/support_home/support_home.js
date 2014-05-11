// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

wn.module_page["Support"] = [
	{
		title: wn._("Top"),
		top: true,
		icon: "icon-copy",
		items: [
			{
				label: wn._("Support Ticket"),
				description: wn._("Support queries from customers."),
				doctype:"Support Ticket"
			},
			{
				label: wn._("Customer Issue"),
				description: wn._("Customer Issue against Serial No."),
				doctype:"Customer Issue"
			},
		]
	},

	{
		title: wn._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: wn._("Maintenance Schedule"),
				description: wn._("Plan for maintenance visits."),
				doctype:"Maintenance Schedule"
			},
			{
				label: wn._("Maintenance Visit"),
				description: wn._("Visit report for maintenance call."),
				doctype:"Maintenance Visit"
			},
			{
				label: wn._("Newsletter"),
				description: wn._("Newsletters to contacts, leads."),
				doctype:"Newsletter"
			},
			{
				label: wn._("Communication"),
				description: wn._("Communication log."),
				doctype:"Communication"
			},
		]
	},
	{
		title: wn._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: wn._("Serial No"),
				description: wn._("Single unit of an Item."),
				doctype:"Serial No"
			},
		]
	},
	{
		title: wn._("Setup"),
		icon: "icon-cog",
		items: [
			{
				"route":"Form/Email Settings/Email Settings",
				"label":wn._("Email Settings"),
				"description":wn._("Setup to pull emails from support email account"),
				doctype: "Email Settings"
			},
		]
	},
	{
		title: wn._("Analytics"),
		right: true,
		icon: "icon-bar-chart",
		items: [
			{
				"label":wn._("Support Analytics"),
				page: "support-analytics"
			},
		]
	},
	{
		title: wn._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":wn._("Maintenance Schedules"),
				route: "query-report/Maintenance Schedules",
				doctype: "Maintenance Schedule"
			}
		]
	}
]

pscript['onload_support-home'] = function(wrapper) {
	wn.views.moduleview.make(wrapper, "Support");
}
