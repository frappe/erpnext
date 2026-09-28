import frappe

# (sidebar, the desk Dashboard its Dashboard item links, the Insights dashboard that replaces it)
DASHBOARD_LINKS = [
	("Accounts", "Accounts", "accounts"),
	("Accounts", "Payments", "payments"),
	("Assets", "Asset", "assets"),
	("Buying", "Buying", "buying"),
	("Selling", "Selling", "selling"),
	("Stock", "Stock", "stock"),
]


def set_dashboard_links(links=DASHBOARD_LINKS):
	"""Point each Dashboard sidebar item at its Insights dashboard where Insights ships it,
	and at the desk Dashboard where it does not.

	The sidebar files link the desk Dashboard, so a site without Insights keeps a working
	link. A sidebar re-sync restores that link, so this runs after every migrate.
	"""
	has_insights = "insights" in frappe.get_installed_apps()
	changed = False

	for sidebar, dashboard, insights_dashboard in links:
		if has_insights and frappe.db.exists("Insights Dashboard v3", insights_dashboard):
			link = {"link_type": "Page", "link_to": "insights-dashboard", "route": insights_dashboard}
		else:
			link = {"link_type": "Dashboard", "link_to": dashboard, "route": None}

		items = frappe.get_all(
			"Sidebar Item",
			filters={
				"parenttype": "Sidebar",
				"parent": sidebar,
				"link_type": "Dashboard",
				"link_to": dashboard,
			},
			fields=["name", "link_type", "link_to", "route"],
		) + frappe.get_all(
			"Sidebar Item",
			filters={
				"parenttype": "Sidebar",
				"parent": sidebar,
				"link_type": "Page",
				"link_to": "insights-dashboard",
				"route": insights_dashboard,
			},
			fields=["name", "link_type", "link_to", "route"],
		)
		for item in items:
			if any(item[field] != value for field, value in link.items()):
				# not a save of the Sidebar, which in developer mode writes the app's file
				frappe.db.set_value("Sidebar Item", item.name, link)
				changed = True

	if changed:
		frappe.clear_cache()
