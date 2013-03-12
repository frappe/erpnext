// ERPNext: Copyright 2013 Web Notes Technologies Pvt Ltd
// GNU General Public License. See "license.txt"

wn.module_page["Setup"] = [
	{
		title: wn._("Organization"),
		icon: "icon-building",
		items: [
			{
				"label":wn._("Company"),
				"doctype":"Company",
				"description":wn._("List of companies (not customers / suppliers)")
			},
			{
				"doctype":"Fiscal Year",
				"label": wn._("Fiscal Year"),
				"description":wn._("Financial Years for books of accounts")
			},
			{
				"doctype":"Currency",
				"label": wn._("Currency"),
				"description": wn._("Enable / disable currencies.")
			},
		]
	},
	{
		title: wn._("Users"),
		icon: "icon-group",
		right: true,
		items: [
			{
				"doctype":"Profile",
				"label": wn._("Profile"),
				"description": wn._("Add/remove users, set roles, passwords etc")
			},
			{
				"page":"permission-manager",
				label: wn._("Permission Manager"),
				"description": wn._("Set permissions on transactions / masters")
			},
			{
				"page":"user-properties",
				label: wn._("User Properties"),
				"description":wn._("Set default values for users (also used for permissions).")
			},
			{
				"doctype":"Workflow",
				label:wn._("Workfow"),
				"description":wn._("Set workflow rules.")
			},
			{
				"doctype":"Authorization Rule",
				label:wn._("Authorization Rule"),
				"description":wn._("Restrict submission rights based on amount")
			},
		]
	},
	{
		title: wn._("Data"),
		icon: "icon-table",
		items: [
			{
				"page":"data-import-tool",
				label: wn._("Data Import"),
				"description":wn._("Import data from spreadsheet (csv) files")
			},
			{
				"route":"Form/Global Defaults",
				doctype: "Global Defaults",
				label: wn._("Global Defaults"),
				"description":wn._("Set default values for entry"),
			},
			{
				"route":"Form/Naming Series/Naming Series",
				doctype: "Naming Series",
				label: wn._("Manage numbering series"),
				"description":wn._("Set multiple numbering series for transactions")
			},
		]
	},
	{
		title: wn._("Branding and Printing"),
		icon: "icon-print",
		right: true,
		items: [
			{
				"doctype":"Letter Head",
				label:wn._("Letter Head"),
				"description":wn._("Letter heads for print")
			},
			{
				"doctype":"Print Format",
				label:wn._("Print Format"),
				"description":wn._("HTML print formats for quotes, invoices etc")
			},
			{
				"doctype":"Print Heading",
				label:wn._("Print Heading"),
				"description":wn._("Add headers for standard print formats")
			},
		]
	},
	{
		title: wn._("Email Settings"),
		icon: "icon-envelope",
		items: [
			{
				"route":"Form/Email Settings/Email Settings",
				doctype:"Email Settings",
				label: wn._("Email Settings"),
				"description":wn._("Out going mail server and support ticket mailbox")
			},
			{
				"route":"Form/Sales Email Settings",
				doctype:"Sales Email Settings",
				label: wn._("Sales Email Settings"),
				"description":wn._("Extract Leads from sales email id e.g. sales@example.com")
			},
			{
				"route":"Form/Jobs Email Settings",
				doctype:"Jobs Email Settings",
				label: wn._("Jobs Email Settings"),
				"description":wn._("Extract Job Applicant from jobs email id e.g. jobs@example.com")
			},
			{
				"route":"Form/Notification Control/Notification Control",
				doctype:"Notification Control",
				label: wn._("Notification Control"),
				"description":wn._("Prompt email sending to customers and suppliers"),
			},
			{
				"doctype":"Email Digest",
				label: wn._("Email Digest"),
				"description":wn._("Daily, weekly, monthly email Digests")
			},
			{
				"route":"Form/SMS Settings/SMS Settings",
				doctype:"SMS Settings",
				label: wn._("SMS Settings"),
				"description":wn._("Setup outgoing SMS via your bulk SMS provider")
			},
			{
				"route":"Form/SMS Center/SMS Center",
				doctype:"SMS Center",
				label: wn._("SMS Center"),
				"description":wn._("Send bulk SMS to leads, customers, contacts")
			},
		]
	},
	{
		title: wn._("Customize"),
		icon: "icon-wrench",
		items: [			
			{
				"route":"Form/Customize Form/Customize Form",
				doctype:"Customize Form",
				label: wn._("Customize Form"),
				"description":wn._("Change entry properties (hide fields, make mandatory etc)")
			},
			{
				"doctype":"Custom Field",
				label: wn._("Custom Field"),
				"description":wn._("Add fields to forms")
			},
			{
				"doctype":"Custom Script",
				label: wn._("Custom Script"),
				"description":wn._("Add custom code to forms")
			},
			{
				"route":"Form/Features Setup/Features Setup",
				"description":wn._("Simplify entry forms by disabling features"),
				doctype:"Features Setup",
				label: wn._("Features Setup"),
			},
			{
				"page":"modules_setup",
				label: wn._("Show / Hide Modules"),
				"description":wn._("Show, hide modules")
			},
		]
	},
	{
		title: wn._("Backups"),
		icon: "icon-cloud-upload",
		right: true,
		items: [
			{
				"route":"Form/Backup Manager",
				doctype:"Backup Manager",
				label: wn._("Backup Manager"),
				"description":wn._("Sync backups with remote tools like Dropbox etc.")
			},
		]
	},
]

pscript['onload_Setup'] = function(wrapper) {
	wn.views.moduleview.make(wrapper, "Setup");
	if(wn.boot.expires_on) {
		$(wrapper).find(".main-section")
			.prepend("<div class='alert'>Your ERPNext account will expire on "
				+ wn.datetime.global_date_format(wn.boot.expires_on) + "</div>");
	}
}