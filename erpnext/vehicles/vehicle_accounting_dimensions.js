frappe.provide("erpnext.vehicles.vehicle_accounting_dimensions")

erpnext.vehicles.vehicle_accounting_dimensions.vehicle_copy_fields = [
	'applies_to_item_name',
	'vehicle_chassis_no',
	'vehicle_engine_no',
	'vehicle_license_plate',
]
erpnext.vehicles.vehicle_accounting_dimensions.booking_copy_fileds = [
	'booking_customer_name',
]

cur_frm.cscript.vehicle_booking_order = function(doc, dt, dn) {
	if (dt && dn) {
		doc = frappe.get_doc(dt, dn);
	} else {
		dt = this.frm.doc.doctype;
		dn = this.frm.doc.name;
	}

	if (doc.vehicle_booking_order) {
		frappe.db.get_value("Vehicle Booking Order", doc.vehicle_booking_order, "vehicle", function (r) {
			if (r) {
				frappe.model.set_value(dt, dn, 'applies_to_vehicle', r.vehicle);
			}
		});
	} else {
		$.each(erpnext.vehicles.vehicle_accounting_dimensions.booking_copy_fileds, function (i, f) {
			frappe.model.set_value(dt, dn, f, null);
		});
	}
};

cur_frm.cscript.vehicle_registration_order = function(doc, dt, dn) {
	if (dt && dn) {
		doc = frappe.get_doc(dt, dn);
	} else {
		dt = this.frm.doc.doctype;
		dn = this.frm.doc.name;
	}

	if (doc.vehicle_registration_order) {
		frappe.db.get_value("Vehicle Registration Order", doc.vehicle_registration_order,
			["vehicle_booking_order", "vehicle"], function (r) {
			if (r) {
				frappe.run_serially([
					() => frappe.model.set_value(dt, dn, 'vehicle_booking_order', r.vehicle_booking_order),
					() => frappe.model.set_value(dt, dn, 'applies_to_vehicle', r.vehicle),
				])
			}
		});
	}
};

cur_frm.cscript.applies_to_vehicle = function(doc, dt, dn) {
	if (dt && dn) {
		doc = frappe.get_doc(dt, dn);
	} else {
		dt = this.frm.doc.doctype;
		dn = this.frm.doc.name;
	}

	if (!doc.applies_to_vehicle) {
		$.each(erpnext.vehicles.vehicle_accounting_dimensions.vehicle_copy_fields, function (i, f) {
			frappe.model.set_value(dt, dn, f, null);
		});
	}
};