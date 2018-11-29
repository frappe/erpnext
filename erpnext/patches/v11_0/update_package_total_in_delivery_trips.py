import frappe

def execute():
    for trip in frappe.get_all("Delivery Trip", {"docstatus" : 1}):
        trip_doc = frappe.get_doc("Delivery Trip", trip.name)
        total = sum([stop.grand_total for stop in trip_doc.delivery_stops if stop.grand_total])
        frappe.db.set_value("Delivery Trip", trip.name, "package_total", total, update_modified=False)