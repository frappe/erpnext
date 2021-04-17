import frappe
from frappe import _
from frappe.utils import cstr, flt
from erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order import force_fields,\
	get_customer_details, get_item_details, update_vehicle_booked, update_allocation_booked


def set_can_change_onload(vbo_doc):
	can_change = {
		"vehicle": can_change_vehicle(vbo_doc),
		"allocation": can_change_allocation(vbo_doc),
		"delivery_period": can_change_delivery_period(vbo_doc),
		"color": can_change_color(vbo_doc),
		"customer_details": can_change_customer_details(vbo_doc),
		"item": can_change_item(vbo_doc),
		"payment_adjustment": can_change_payment_adjustment(vbo_doc),
	}
	vbo_doc.set_onload("can_change", can_change)


@frappe.whitelist()
def change_vehicle(vehicle_booking_order, vehicle):
	if not vehicle:
		frappe.throw(_("Vehicle not provided"))

	vbo_doc = get_vehicle_booking_for_update(vehicle_booking_order)
	can_change_vehicle(vbo_doc, throw=True)

	if vehicle == vbo_doc.vehicle:
		frappe.throw(_("Vehicle {0} is already selected in {1}").format(vehicle, vehicle_booking_order))

	previous_vehicle = vbo_doc.vehicle

	vbo_doc.vehicle = vehicle
	vbo_doc.validate_vehicle_item()
	vbo_doc.validate_vehicle()
	vbo_doc.set_vehicle_details()

	vbo_doc.update_delivery_status()

	save_vehicle_booking_for_update(vbo_doc)

	update_vehicle_booked(vehicle, 1)
	if previous_vehicle:
		update_vehicle_booked(previous_vehicle, 0)

	frappe.msgprint(_("Vehicle Changed Successfully"), indicator='green', alert=True)


def can_change_vehicle(vbo_doc, throw=False):
	if check_vehicle_received(vbo_doc, throw=throw):
		return False

	return True


@frappe.whitelist()
def change_allocation(vehicle_booking_order, vehicle_allocation):
	if not vehicle_allocation:
		frappe.throw(_("Vehicle Allocation not provided"))

	vbo_doc = get_vehicle_booking_for_update(vehicle_booking_order)
	can_change_allocation(vbo_doc, throw=True)

	if vehicle_allocation == vbo_doc.vehicle_allocation:
		frappe.throw(_("Vehicle Allocation {0} is already selected in {1}").format(vehicle_allocation, vehicle_booking_order))

	previous_allocation = vbo_doc.vehicle_allocation

	vbo_doc.vehicle_allocation = vehicle_allocation
	vbo_doc.validate_allocation()

	if vbo_doc.delivery_period != vbo_doc._doc_before_save.delivery_period:
		handle_delivery_period_changed(vbo_doc)

	save_vehicle_booking_for_update(vbo_doc)

	update_allocation_booked(vehicle_allocation, 1)
	if previous_allocation:
		update_allocation_booked(previous_allocation, 0)

	frappe.msgprint(_("Allocation Changed Successfully"), indicator='green', alert=True)


def can_change_allocation(vbo_doc, throw=False):
	if not allowed_after_supplier_payment():
		if check_supplier_payment_exists(vbo_doc, throw=throw):
			return False
	if not allowed_after_vehicle_receipt():
		if check_vehicle_received(vbo_doc, throw=throw):
			return False

	if not vbo_doc.vehicle_allocation_required:
		if throw:
			frappe.throw(_("Vehicle Allocation is not required in {0}").format(vbo_doc.name))

		return False

	return True


@frappe.whitelist()
def change_delivery_period(vehicle_booking_order, delivery_period):
	if not delivery_period:
		frappe.throw(_("Delivery Period not provided"))

	vbo_doc = get_vehicle_booking_for_update(vehicle_booking_order)
	can_change_delivery_period(vbo_doc, throw=True)

	if delivery_period == vbo_doc.delivery_period:
		frappe.throw(_("Delivery Period {0} is already selected in {1}").format(delivery_period, vehicle_booking_order))

	if vbo_doc.vehicle_allocation:
		frappe.throw(_("Cannot change Delivery Period because Vehicle Allocation is already set in {0}. Please change Vehicle Allocation instead")
			.format(frappe.bold(vehicle_booking_order)))

	vbo_doc.delivery_period = delivery_period
	handle_delivery_period_changed(vbo_doc)

	save_vehicle_booking_for_update(vbo_doc)

	frappe.msgprint(_("Delivery Period Changed Successfully"), indicator='green', alert=True)


def can_change_delivery_period(vbo_doc, throw=False):
	if not allowed_after_supplier_payment():
		if check_supplier_payment_exists(vbo_doc, throw=throw):
			return False

	if not allowed_after_vehicle_receipt():
		if check_vehicle_received(vbo_doc, throw=throw):
			return False

	return True


@frappe.whitelist()
def change_color(vehicle_booking_order, color_1, color_2, color_3):
	if not color_1:
		frappe.throw(_("Color (1st Priority) not provided"))

	vbo_doc = get_vehicle_booking_for_update(vehicle_booking_order)
	can_change_color(vbo_doc, throw=True)

	if cstr(color_1) == cstr(vbo_doc.color_1) and cstr(color_2) == cstr(vbo_doc.color_2) and cstr(color_3) == cstr \
			(vbo_doc.color_3):
		frappe.throw(_("Color is the same in Vehicle Allocation {0}").format(vehicle_booking_order))

	vbo_doc.color_1 = color_1
	vbo_doc.color_2 = color_2
	vbo_doc.color_3 = color_3
	vbo_doc.validate_color_mandatory()

	save_vehicle_booking_for_update(vbo_doc)

	frappe.msgprint(_("Color Changed Successfully"), indicator='green', alert=True)


def can_change_color(vbo_doc, throw=False):
	if not allowed_after_vehicle_receipt():
		if check_vehicle_received(vbo_doc, throw=throw):
			return False

	return True


@frappe.whitelist()
def change_customer_details(vehicle_booking_order):
	vbo_doc = get_vehicle_booking_for_update(vehicle_booking_order)
	can_change_customer_details(vbo_doc, throw=True)

	customer_details = get_customer_details(vbo_doc.as_dict(), get_withholding_tax=True)
	for k, v in customer_details.items():
		if not vbo_doc.get(k) or k in force_fields:
			vbo_doc.set(k, v)

	vbo_doc.validate_customer()
	vbo_doc.calculate_taxes_and_totals()
	vbo_doc.validate_payment_schedule()
	vbo_doc.update_payment_status()
	vbo_doc.validate_amounts()

	save_vehicle_booking_for_update(vbo_doc)

	frappe.msgprint(_("Customer Details Updated Successfully"), indicator='green', alert=True)


def can_change_customer_details(vbo_doc, throw=False):
	if not allowed_after_supplier_payment():
		if check_supplier_payment_exists(vbo_doc, throw=throw):
			return False

	if not allowed_after_vehicle_receipt():
		if check_vehicle_received(vbo_doc, throw=throw):
			return False

	return True


@frappe.whitelist()
def change_item(vehicle_booking_order, item_code):
	if not item_code:
		frappe.throw(_("Vehicle Item Code (Variant) not provided"))

	vbo_doc = get_vehicle_booking_for_update(vehicle_booking_order)
	can_change_item(vbo_doc, throw=True)

	if item_code == vbo_doc.item_code:
		frappe.throw(_("Vehicle Item Code (Variant) {0} is already selected in {1}").format(frappe.bold(item_code), vehicle_booking_order))

	previous_item_code = vbo_doc.item_code
	previous_item = frappe.get_cached_doc("Item", previous_item_code)
	template_item_name = frappe.get_cached_value("Item", previous_item.variant_of, "item_name") if previous_item.variant_of else None
	item = frappe.get_cached_doc("Item", item_code)

	if previous_item.variant_of and item.variant_of != previous_item.variant_of:
		frappe.throw(_("New Vehicle Item (Variant) must be a variant of {0}").format
			(frappe.bold(template_item_name or previous_item.variant_of)))

	if not vbo_doc.previous_item_code:
		vbo_doc.previous_item_code = vbo_doc.item_code

	vbo_doc.item_code = item_code

	if vbo_doc.vehicle_allocation and not flt(vbo_doc.supplier_advance):
		update_allocation_booked(vbo_doc.vehicle_allocation, 0)
		vbo_doc.vehicle_allocation = None

	if vbo_doc.vehicle:
		update_vehicle_booked(vbo_doc.vehicle, 0)
		vbo_doc.vehicle = None

	item_detail_args = vbo_doc.as_dict()
	item_detail_args['tc_name'] = None
	item_details = get_item_details(item_detail_args)
	vbo_doc.update(item_details)

	vbo_doc.validate_vehicle_item()
	vbo_doc.validate_allocation()
	vbo_doc.validate_vehicle()

	vbo_doc.calculate_taxes_and_totals()
	vbo_doc.validate_payment_schedule()
	vbo_doc.update_payment_status()
	vbo_doc.validate_amounts()

	vbo_doc.get_terms_and_conditions()

	save_vehicle_booking_for_update(vbo_doc)

	frappe.msgprint(_("Vehicle Item Code (Variant) Updated Successfully"), indicator='green')


def can_change_item(vbo_doc, throw=False):
	if check_vehicle_received(vbo_doc, throw=throw):
		return False

	return True


@frappe.whitelist()
def change_payment_adjustment(vehicle_booking_order, payment_adjustment):
	vbo_doc = get_vehicle_booking_for_update(vehicle_booking_order)
	can_change_payment_adjustment(vbo_doc, throw=True)

	vbo_doc.payment_adjustment = flt(payment_adjustment)

	vbo_doc.calculate_outstanding_amount()
	vbo_doc.update_payment_status()
	vbo_doc.validate_amounts()

	save_vehicle_booking_for_update(vbo_doc)

	frappe.msgprint(_("Payment Adjustment Updated Successfully"), indicator='green', alert=True)


def can_change_payment_adjustment(vbo_doc, throw=False):
	if not allowed_after_vehicle_delivery():
		if check_vehicle_delivered(vbo_doc, throw=throw):
			return False

	return True


def handle_delivery_period_changed(vbo_doc):
	to_date = frappe.get_cached_value("Vehicle Allocation Period", vbo_doc.delivery_period, 'to_date')

	vbo_doc.delivery_date = to_date
	vbo_doc.validate_delivery_date()

	vbo_doc.due_date = to_date
	vbo_doc.payment_schedule = []
	vbo_doc.validate_payment_schedule()
	vbo_doc.update_payment_status()

	frappe.msgprint(_("Delivery Period has been changed from {0} to {1}")
		.format(frappe.bold(vbo_doc._doc_before_save.delivery_period or 'None'), frappe.bold(vbo_doc.delivery_period)))


def get_vehicle_booking_for_update(vehicle_booking_order):
	vbo_doc = frappe.get_doc("Vehicle Booking Order", vehicle_booking_order)
	vbo_doc._doc_before_save = frappe.get_doc(vbo_doc.as_dict())

	if vbo_doc.docstatus != 1:
		frappe.throw(_("Vehicle Booking Order {0} is not submitted").format(vehicle_booking_order))

	return vbo_doc


def save_vehicle_booking_for_update(vbo_doc, update_child_tables=True):
	vbo_doc.set_status()

	vbo_doc.set_user_and_timestamp()
	vbo_doc.db_update()

	if update_child_tables:
		vbo_doc.update_children()

	vbo_doc.notify_update()
	vbo_doc.save_version()


def check_vehicle_received(vbo_doc, throw=False):
	if vbo_doc.delivery_status != 'To Receive':
		if throw:
			frappe.throw(_("Cannot modify Vehicle Booking Order {0} because Vehicle is already received")
				.format(frappe.bold(vbo_doc.name)))
		return True

	return False


def check_vehicle_delivered(vbo_doc, throw=False):
	if vbo_doc.delivery_status == 'Delivered':
		if throw:
			frappe.throw(_("Cannot modify Vehicle Booking Order {0} because Vehicle is already delivered")
				.format(frappe.bold(vbo_doc.name)))
		return True

	return False


def check_supplier_payment_exists(vbo_doc, throw=False):
	if flt(vbo_doc.supplier_advance):
		if throw:
			frappe.throw(_("Cannot modify Vehicle Booking Order {0} because Supplier Payment has already been made")
				.format(frappe.bold(vbo_doc.name)))
		return True

	return False


def allowed_after_vehicle_receipt():
	role_allowed = frappe.get_cached_value("Vehicles Settings", None, "role_change_booking_after_vehicle_receipt")
	return role_allowed and role_allowed in frappe.get_roles()


def allowed_after_vehicle_delivery():
	role_allowed = frappe.get_cached_value("Vehicles Settings", None, "role_change_booking_after_vehicle_delivery")
	return role_allowed and role_allowed in frappe.get_roles()


def allowed_after_supplier_payment():
	role_allowed = frappe.get_cached_value("Vehicles Settings", None, "role_change_booking_after_payment")
	return role_allowed and role_allowed in frappe.get_roles()
