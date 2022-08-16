import frappe
from frappe import _
from frappe.utils import cstr, flt, cint
from erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order import update_vehicle_booked,\
	update_allocation_booked
from erpnext.vehicles.vehicle_booking_controller import force_fields, get_customer_details, get_item_details,\
	get_delivery_period_details
from erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order import get_vehicle_registration_order


def set_can_change_onload(vbo_doc):
	can_change = {
		"vehicle": can_change_vehicle(vbo_doc),
		"allocation": can_change_allocation(vbo_doc),
		"delivery_period": can_change_delivery_period(vbo_doc),
		"color": can_change_color(vbo_doc),
		"customer_details": can_change_customer_details(vbo_doc),
		"item": can_change_item(vbo_doc),
		"payment_adjustment": can_change_payment_adjustment(vbo_doc),
		"vehicle_price": can_change_vehicle_price(vbo_doc),
		"priority": can_change_priority(vbo_doc),
		"cancellation": can_change_cancellation(vbo_doc),
		"vehicle_receipt": can_receive_vehicle(vbo_doc),
		"vehicle_delivery": can_deliver_vehicle(vbo_doc),
		"vehicle_transfer": can_transfer_vehicle(vbo_doc),
		"invoice_receipt": can_receive_invoice(vbo_doc),
		"invoice_delivery": can_deliver_invoice(vbo_doc),
		"vehicle_assign": can_assign_vehicle(vbo_doc),
		"allocation_assign": can_assign_allocation(vbo_doc)
	}
	vbo_doc.set_onload("can_change", can_change)


@frappe.whitelist()
def change_vehicle(vehicle_booking_order, vehicle):
	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_change_vehicle(vbo_doc, throw=True)

	if cstr(vehicle) == cstr(vbo_doc.vehicle):
		if vehicle:
			frappe.throw(_("Vehicle {0} is already selected in {1}").format(vehicle, vehicle_booking_order))
		else:
			frappe.throw(_("Vehicle is already unassigned in {0}").format(vehicle_booking_order))

	previous_vehicle = vbo_doc.vehicle

	vbo_doc.vehicle = vehicle
	vbo_doc.validate_vehicle_item()
	vbo_doc.validate_vehicle()
	vbo_doc.set_vehicle_details()

	vbo_doc.set_delivery_status()
	vbo_doc.set_invoice_status()
	vbo_doc.set_registration_status()

	save_document_for_update(vbo_doc)

	if vehicle:
		update_vehicle_booked(vehicle, 1)
	if previous_vehicle:
		update_vehicle_booked(previous_vehicle, 0)

	change_vehicle_in_registration_order(vbo_doc)

	frappe.msgprint(_("Vehicle Changed Successfully"), indicator='green', alert=True)


def change_vehicle_in_registration_order(booking_doc):
	vehicle_registration_order = get_vehicle_registration_order(vehicle_booking_order=booking_doc.name)
	if not vehicle_registration_order:
		return

	vro_doc = get_document_for_update(vehicle_registration_order, doctype="Vehicle Registration Order")

	vro_doc.vehicle = booking_doc.vehicle

	vro_doc.validate_vehicle_item()
	vro_doc.validate_vehicle()

	vro_doc.set_vehicle_details()

	vro_doc.validate_vehicle_booking_order()
	vro_doc.set_invoice_status()

	save_document_for_update(vro_doc)


def can_change_vehicle(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if not can_assign_vehicle(vbo_doc, throw=throw):
		return False
	if not vbo_doc.vehicle_receipt and check_vehicle_received(vbo_doc, throw=throw):
		return False
	if check_vehicle_delivered(vbo_doc, throw=throw):
		return False

	if check_invoice_exists(vbo_doc, throw=throw):
		return False
	if check_invoice_delivered(vbo_doc, throw=throw):
		return False
	if check_invoice_issued(vbo_doc, throw=throw):
		return False

	return True


@frappe.whitelist()
def change_item(vehicle_booking_order, item_code):
	if not item_code:
		frappe.throw(_("Variant Item Code not provided"))

	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_change_item(vbo_doc, throw=True)

	if item_code == vbo_doc.item_code:
		frappe.throw(_("Variant Item Code {0} is already selected in {1}").format(frappe.bold(item_code), vehicle_booking_order))

	previous_item_code = vbo_doc.item_code
	previous_item = frappe.get_cached_doc("Item", previous_item_code)
	new_item = frappe.get_cached_doc("Item", item_code)
	model_item_name = frappe.get_cached_value("Item", previous_item.variant_of, "item_name") if previous_item.variant_of else None

	if previous_item.variant_of and new_item.variant_of != previous_item.variant_of:
		frappe.throw(_("New Variant Item Code must be a variant of {0}").format
			(frappe.bold(model_item_name or previous_item.variant_of)))

	if not vbo_doc.previous_item_code:
		vbo_doc.previous_item_code = vbo_doc.item_code

	vbo_doc.item_code = item_code

	if vbo_doc.vehicle_allocation and not flt(vbo_doc.supplier_advance):
		update_allocation_booked(vbo_doc.vehicle_allocation, 0, 0)
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
	vbo_doc.set_payment_status()
	vbo_doc.validate_amounts()

	vbo_doc.get_terms_and_conditions()

	save_document_for_update(vbo_doc)

	change_item_in_registration_order(vbo_doc)

	frappe.msgprint(_("Variant Item Changed Successfully"), indicator='green')


def change_item_in_registration_order(booking_doc):
	vehicle_registration_order = get_vehicle_registration_order(vehicle_booking_order=booking_doc.name)
	if not vehicle_registration_order:
		return

	vro_doc = get_document_for_update(vehicle_registration_order, doctype="Vehicle Registration Order")

	vro_doc.item_code = booking_doc.item_code
	vro_doc.vehicle = booking_doc.vehicle

	vro_doc.validate_vehicle_item()
	vro_doc.validate_vehicle()

	vro_doc.set_item_details(force=1)
	vro_doc.set_vehicle_details()
	vro_doc.set_pricing_details(update_component_amounts=True)

	vro_doc.calculate_totals()
	vro_doc.set_payment_status()

	vro_doc.validate_vehicle_booking_order()
	vro_doc.set_invoice_status()

	save_document_for_update(vro_doc)


def can_change_item(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if not check_allowed_after_supplier_payment(vbo_doc, throw=throw):
		return False

	if check_vehicle_received(vbo_doc, throw=throw):
		return False

	if check_invoice_exists(vbo_doc, throw=throw):
		return False
	if check_invoice_delivered(vbo_doc, throw=throw):
		return False
	if check_invoice_issued(vbo_doc, throw=throw):
		return False

	return True


@frappe.whitelist()
def change_allocation(vehicle_booking_order, vehicle_allocation):
	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_change_allocation(vbo_doc, throw=True)

	if cstr(vehicle_allocation) == cstr(vbo_doc.vehicle_allocation):
		if vehicle_allocation:
			frappe.throw(_("Vehicle Allocation {0} is already selected in {1}").format(vehicle_allocation, vehicle_booking_order))
		else:
			frappe.throw(_("{0} is already unallocated").format(vehicle_booking_order))

	previous_allocation = vbo_doc.vehicle_allocation

	vbo_doc.vehicle_allocation = vehicle_allocation
	vbo_doc.validate_allocation()

	if vbo_doc.delivery_period != vbo_doc._doc_before_save.delivery_period:
		handle_delivery_period_changed(vbo_doc)

	save_document_for_update(vbo_doc)

	is_cancelled = cint(vbo_doc.status == "Cancelled Booking")
	update_allocation_booked(vehicle_allocation, 1, is_cancelled)
	if previous_allocation:
		update_allocation_booked(previous_allocation, 0, 0)

	frappe.msgprint(_("Allocation Changed Successfully"), indicator='green', alert=True)


def can_change_allocation(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if not can_assign_allocation(vbo_doc, throw=throw):
		return False

	if vbo_doc.vehicle_allocation and not check_allowed_after_supplier_payment(vbo_doc, throw=throw):
		return False
	if vbo_doc.vehicle_allocation and not check_allowed_after_vehicle_receipt(vbo_doc, throw=throw):
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

	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_change_delivery_period(vbo_doc, throw=True)

	if delivery_period == vbo_doc.delivery_period:
		frappe.throw(_("Delivery Period {0} is already selected in {1}").format(delivery_period, vehicle_booking_order))

	if vbo_doc.vehicle_allocation:
		frappe.throw(_("Cannot change Delivery Period because Vehicle Allocation is already set in {0}. Please change Vehicle Allocation instead")
			.format(frappe.bold(vehicle_booking_order)))

	vbo_doc.delivery_period = delivery_period
	handle_delivery_period_changed(vbo_doc)

	save_document_for_update(vbo_doc)

	frappe.msgprint(_("Delivery Period Changed Successfully"), indicator='green', alert=True)


def can_change_delivery_period(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if not check_allowed_after_supplier_payment(vbo_doc, throw=throw):
		return False
	if not check_allowed_after_vehicle_receipt(vbo_doc, throw=throw):
		return False

	return True


@frappe.whitelist()
def change_color(vehicle_booking_order, color_1, color_2, color_3):
	if not color_1:
		frappe.throw(_("Color (1st Priority) not provided"))

	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_change_color(vbo_doc, throw=True)

	if cstr(color_1) == cstr(vbo_doc.color_1) and cstr(color_2) == cstr(vbo_doc.color_2) and cstr(color_3) == cstr(vbo_doc.color_3):
		frappe.throw(_("Color is the same in Vehicle Allocation {0}").format(vehicle_booking_order))

	if not vbo_doc.previous_color:
		vbo_doc.previous_color = vbo_doc.color_1

	vbo_doc.color_1 = color_1
	vbo_doc.color_2 = color_2
	vbo_doc.color_3 = color_3

	vbo_doc.validate_color_mandatory()
	vbo_doc.validate_color()

	save_document_for_update(vbo_doc)

	frappe.msgprint(_("Color Changed Successfully"), indicator='green', alert=True)


def can_change_color(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if not check_allowed_after_supplier_payment(vbo_doc, throw=throw):
		return False
	if not check_allowed_after_vehicle_receipt(vbo_doc, throw=throw):
		return False

	return True


@frappe.whitelist()
def change_customer_details(vehicle_booking_order, customer_is_company=None, customer=None, financer=None,
		finance_type=None, customer_address=None, contact_person=None, financer_contact_person=None):
	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_change_customer_details(vbo_doc, throw=True)

	# if previous customer is completely removed
	if customer not in (vbo_doc.customer, vbo_doc.financer) and (not financer or financer not in (vbo_doc.customer, vbo_doc.financer)):
		frappe.throw(_("Cannot remove the original Customer"))

	customer_is_company = cint(customer_is_company)
	vbo_doc.customer_is_company = customer_is_company
	vbo_doc.customer = customer
	vbo_doc.financer = financer
	vbo_doc.finance_type = finance_type
	vbo_doc.customer_address = customer_address
	vbo_doc.contact_person = contact_person
	vbo_doc.financer_contact_person = financer_contact_person

	customer_details = get_customer_details(vbo_doc.as_dict(), get_withholding_tax=True)
	for k, v in customer_details.items():
		if not vbo_doc.get(k) or k in force_fields:
			vbo_doc.set(k, v)

	vbo_doc.validate_customer()
	vbo_doc.set_title()
	vbo_doc.calculate_taxes_and_totals()
	vbo_doc.validate_payment_schedule()
	vbo_doc.set_payment_status()
	vbo_doc.validate_amounts()

	save_document_for_update(vbo_doc)

	frappe.msgprint(_("Customer Details Updated Successfully"), indicator='green', alert=True)


def can_change_customer_details(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if not check_allowed_after_supplier_payment(vbo_doc, throw=throw):
		return False
	if not check_allowed_after_vehicle_receipt(vbo_doc, throw=throw):
		return False

	return True


@frappe.whitelist()
def change_payment_adjustment(vehicle_booking_order, payment_adjustment):
	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_change_payment_adjustment(vbo_doc, throw=True)

	payment_adjustment = flt(payment_adjustment, vbo_doc.precision('payment_adjustment'))

	if payment_adjustment == flt(vbo_doc.payment_adjustment):
		frappe.throw(_("Payment Adjustment is already {0}"
			.format(frappe.bold(vbo_doc.get_formatted('payment_adjustment')))))

	vbo_doc.payment_adjustment = payment_adjustment

	vbo_doc.set_payment_status()
	vbo_doc.validate_amounts()
	vbo_doc.validate_payment_adjustment()

	save_document_for_update(vbo_doc)

	frappe.msgprint(_("Payment Adjustment Updated Successfully"), indicator='green', alert=True)


def can_change_payment_adjustment(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	role_allowed = frappe.get_cached_value("Vehicles Settings", None, "role_change_payment_adjustment")
	allowed = role_allowed and role_allowed in frappe.get_roles()
	if not allowed:
		if throw:
			frappe.throw(_("You are not allowed to change Booking Payment Adjustment"))
		return False

	if not check_allowed_after_vehicle_delivery(vbo_doc, throw=throw):
		return False

	return True


@frappe.whitelist()
def change_vehicle_price(vehicle_booking_order, vehicle_amount=0, fni_amount=0):
	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_change_vehicle_price(vbo_doc, throw=True)

	vehicle_amount = flt(vehicle_amount, vbo_doc.precision('vehicle_amount'))
	fni_amount = flt(fni_amount, vbo_doc.precision('fni_amount'))

	tax_status = vbo_doc.get_party_tax_status()
	withholding_tax_amount = vbo_doc.get_withholding_tax_amount(tax_status)

	if vehicle_amount == flt(vbo_doc.vehicle_amount) and fni_amount == flt(vbo_doc.fni_amount)\
			and withholding_tax_amount == flt(vbo_doc.withholding_tax_amount):
		frappe.throw(_("Vehicle Price is the same"))

	vbo_doc.vehicle_amount = vehicle_amount
	vbo_doc.fni_amount = fni_amount
	vbo_doc.withholding_tax_amount = withholding_tax_amount
	vbo_doc.tax_status = tax_status

	vbo_doc.calculate_taxes_and_totals()
	vbo_doc.validate_payment_schedule()
	vbo_doc.set_payment_status()
	vbo_doc.validate_amounts()

	save_document_for_update(vbo_doc)

	frappe.msgprint(_("Vehicle Price Updated Successfully"), indicator='green', alert=True)


def can_change_vehicle_price(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	role_allowed = frappe.get_cached_value("Vehicles Settings", None, "role_change_vehicle_price")
	allowed = role_allowed and role_allowed in frappe.get_roles()
	if not allowed:
		if throw:
			frappe.throw(_("You are not allowed to change Booking Vehicle Price"))
		return False

	if not check_allowed_after_vehicle_delivery(vbo_doc, throw=throw):
		return False

	return True


@frappe.whitelist()
def change_priority(vehicle_booking_order, priority):
	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_change_priority(vbo_doc, throw=True)

	priority = cint(priority)

	if priority == cint(vbo_doc.priority):
		frappe.throw(_("Priority is the same"))

	vbo_doc.priority = priority
	save_document_for_update(vbo_doc)

	frappe.msgprint(_("Payment Adjustment Updated Successfully"), indicator='green', alert=True)


def can_change_priority(vbo_doc, throw=False):
	if not check_allowed_after_vehicle_delivery(vbo_doc, throw=throw):
		return False

	return True


@frappe.whitelist()
def change_pdi_requested(vehicle_booking_order, pdi_requested):
	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_deliver_vehicle(vbo_doc, throw=True)

	pdi_requested = cint(pdi_requested)

	if pdi_requested == cint(vbo_doc.pdi_requested):
		if pdi_requested:
			frappe.throw(_("Pre-Delivery Inspection is already requested"))
		else:
			frappe.throw(_("Pre-Delivery Inspection is not requested"))

	vbo_doc.pdi_requested = pdi_requested
	vbo_doc.set_pdi_status()
	save_document_for_update(vbo_doc)

	frappe.msgprint(_("Pre-Delivery Inspection Request Updated Successfully"), indicator='green', alert=True)


@frappe.whitelist()
def change_cancellation(vehicle_booking_order, cancelled):
	vbo_doc = get_document_for_update(vehicle_booking_order)
	can_change_cancellation(vbo_doc, throw=True)

	cancelled = cint(cancelled)

	if cancelled and vbo_doc.status == "Cancelled Booking":
		frappe.throw(_("Booking is already cancelled"))
	elif not cancelled and vbo_doc.status != "Cancelled Booking":
		frappe.throw(_("Booking is not cancelled"))

	undeposited_amount = flt(vbo_doc.customer_advance - vbo_doc.supplier_advance, vbo_doc.precision('supplier_outstanding'))
	if undeposited_amount > 0:
		frappe.throw(_("Cannot cancel booking because there is an undeposited amount of {0}")
			.format(frappe.format(undeposited_amount, df=vbo_doc.meta.get_field('supplier_outstanding'))))

	vbo_doc.status = "Cancelled Booking" if cancelled else None
	vbo_doc.set_payment_status()

	save_document_for_update(vbo_doc)
	vbo_doc.update_allocation_status()

	if vbo_doc.status == "Cancelled Booking":
		vbo_doc.add_status_comment(None)
		vbo_doc.send_notification_on_cancellation()

	message = "Booking Cancelled Successfully" if cancelled else "Booking Re-Opened Successfully"
	frappe.msgprint(_(message), indicator='green', alert=True)


def can_change_cancellation(vbo_doc, throw=False):
	if not has_cancel_booking_permission(throw):
		return False

	if check_vehicle_assigned(vbo_doc, throw):
		return False
	if check_vehicle_received(vbo_doc, throw):
		return False
	if check_vehicle_delivered(vbo_doc, throw):
		return False

	if check_invoice_exists(vbo_doc, throw):
		return False
	if check_invoice_delivered(vbo_doc, throw):
		return False
	if check_invoice_issued(vbo_doc, throw):
		return False

	return True


def has_cancel_booking_permission(throw=False):
	role_allowed = frappe.get_cached_value("Vehicles Settings", None, "role_cancel_booking")
	allowed = role_allowed and role_allowed in frappe.get_roles()

	if throw and not allowed:
		frappe.throw(_("You do not have permission to cancel bookings"))

	return allowed


def handle_delivery_period_changed(vbo_doc):
	delivery_period_details = get_delivery_period_details(vbo_doc.delivery_period, vbo_doc.item_code)
	vbo_doc.delivery_date = delivery_period_details.delivery_date
	vbo_doc.vehicle_allocation_required = delivery_period_details.vehicle_allocation_required

	vbo_doc.lead_time_days = 0
	vbo_doc.validate_delivery_date()

	vbo_doc.due_date = vbo_doc.delivery_date
	vbo_doc.payment_schedule = []
	vbo_doc.validate_payment_schedule()

	vbo_doc.set_delivery_status()
	vbo_doc.set_payment_status()

	frappe.msgprint(_("Delivery Period has been changed from {0} to {1}")
		.format(frappe.bold(vbo_doc._doc_before_save.delivery_period or 'None'), frappe.bold(vbo_doc.delivery_period)))


def get_document_for_update(name, doctype="Vehicle Booking Order"):
	vbo_doc = frappe.get_doc(doctype, name)
	vbo_doc._doc_before_save = frappe.get_doc(vbo_doc.as_dict())

	if vbo_doc.docstatus != 1:
		frappe.throw(_("{0} {1} is not submitted").format(doctype, name))

	return vbo_doc


def save_document_for_update(doc, update_child_tables=True):
	doc.set_status()

	doc.set_user_and_timestamp()
	doc.db_update()

	if update_child_tables:
		doc.update_children()

	doc.notify_update()
	doc.save_version()


def check_cancelled(vbo_doc, throw=False):
	if vbo_doc.status == "Cancelled Booking":
		if throw:
			frappe.throw(_("Cannot modify Vehicle Booking Order {0} because it is cancelled")
				.format(frappe.bold(vbo_doc.name)))
		return True

	return False


def check_vehicle_assigned(vbo_doc, throw=False):
	if vbo_doc.vehicle:
		if throw:
			frappe.throw(_("Cannot modify Vehicle Booking Order {0} because Vehicle is already assigned")
				.format(frappe.bold(vbo_doc.name)))
		return True

	return False


def check_vehicle_received(vbo_doc, throw=False):
	if vbo_doc.delivery_status != 'Not Received':
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


def check_invoice_exists(vbo_doc, throw=False):
	if not hasattr(vbo_doc, '_has_vehicle_invoice'):
		vbo_doc._has_vehicle_invoice = frappe.db.get_value("Vehicle Invoice",
			{'vehicle_booking_order': vbo_doc.name, 'docstatus': 1})

	vehicle_invoice = vbo_doc.get('_has_vehicle_invoice')
	if vehicle_invoice:
		if throw:
			frappe.throw(_("Cannot modify Vehicle Booking Order {0} because Invoice is already received against booking")
				.format(frappe.bold(vbo_doc.name)))
		return True

	return False


def check_invoice_delivered(vbo_doc, throw=False):
	if vbo_doc.invoice_status == "Delivered":
		if throw:
			frappe.throw(_("Cannot modify Vehicle Booking Order {0} because Invoice is already delivered")
				.format(frappe.bold(vbo_doc.name)))
			return True

	return False


def check_invoice_issued(vbo_doc, throw=False):
	if not hasattr(vbo_doc, '_has_vehicle_invoice_issue'):
		vbo_doc._has_vehicle_invoice_issue = frappe.db.sql("""
			select m.name
			from `tabVehicle Invoice Movement Detail` d
			inner join `tabVehicle Invoice Movement` m on m.name = d.parent
			where m.docstatus = 1 and m.purpose = 'Issue' and d.vehicle_booking_order = %s
			limit 1
		""", vbo_doc.name)
		vbo_doc._has_vehicle_invoice_issue = vbo_doc._has_vehicle_invoice_issue[0][0]\
			if vbo_doc._has_vehicle_invoice_issue else None

	vehicle_invoice_issue = vbo_doc.get('_has_vehicle_invoice_issue')
	if vehicle_invoice_issue:
		if throw:
			frappe.throw(_("Cannot modify Vehicle Booking Order {0} because Invoice is already issued against booking")
				.format(frappe.bold(vbo_doc.name)))
		return True

	return False


def check_registration_order_exists(vbo_doc, throw=False):
	if not hasattr(vbo_doc, '_has_vehicle_registration_order'):
		vbo_doc._has_vehicle_registration_order = get_vehicle_registration_order(vehicle_booking_order=vbo_doc.name)

	vehicle_registration_order = vbo_doc.get('_has_vehicle_registration_order')
	if vehicle_registration_order:
		if throw:
			frappe.throw(_("Cannot modify Vehicle Booking Order {0} because Registration Order exists against booking")
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


def check_allowed_after_vehicle_receipt(vbo_doc, throw=False):
	role_allowed = frappe.get_cached_value("Vehicles Settings", None, "role_change_booking_after_vehicle_receipt")
	allowed = role_allowed and role_allowed in frappe.get_roles()
	if not allowed and check_vehicle_received(vbo_doc, throw=throw):
		return False

	return True


def check_allowed_after_vehicle_delivery(vbo_doc, throw=False):
	role_allowed = frappe.get_cached_value("Vehicles Settings", None, "role_change_booking_after_vehicle_delivery")
	allowed = role_allowed and role_allowed in frappe.get_roles()
	if not allowed and check_vehicle_delivered(vbo_doc, throw=throw):
		return False

	return True


def check_allowed_after_supplier_payment(vbo_doc, throw=False):
	role_allowed = frappe.get_cached_value("Vehicles Settings", None, "role_change_booking_after_payment")
	allowed = role_allowed and role_allowed in frappe.get_roles()
	if not allowed and check_supplier_payment_exists(vbo_doc, throw=throw):
		return False

	return True


def can_assign_vehicle(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	return frappe.has_permission("Vehicle", "create", throw=throw)


def can_assign_allocation(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	return frappe.has_permission("Vehicle Allocation", "write", throw=throw)


def can_receive_vehicle(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if frappe.has_permission("Vehicle Receipt", "create"):
		return True
	else:
		if throw:
			frappe.throw(_("You do not have permission to receive vehicles"))
		return False


def can_deliver_vehicle(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if frappe.has_permission("Vehicle Delivery", "create"):
		return True
	else:
		if throw:
			frappe.throw(_("You do not have permission to deliver vehicles"))
		return False


def can_transfer_vehicle(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if frappe.has_permission("Vehicle Transfer Letter", "create"):
		return True
	else:
		if throw:
			frappe.throw(_("You do not have permission to transfer vehicles"))
		return False


def can_receive_invoice(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if frappe.has_permission("Vehicle Invoice", "create"):
		return True
	else:
		if throw:
			frappe.throw(_("You do not have permission to receive invoices"))
		return False


def can_deliver_invoice(vbo_doc, throw=False):
	if check_cancelled(vbo_doc, throw):
		return False

	if frappe.has_permission("Vehicle Invoice Delivery", "create"):
		return True
	else:
		if throw:
			frappe.throw(_("You do not have permission to deliver invoices"))
		return False
