import frappe
from frappe import _
from fedex_config import fedex_config
from frappe.utils import get_datetime
from fedex.services.pickup_service import FedexCreatePickupRequest

class FedExController():
	""" A Higher-Level wrapper for Fedex python library
		which handles API like Shipment, Tracking, GET Rate
		& other supplementary tasks. """

	uom_mapper = {"Kg":"KG", "LB":"LB"}

	def __init__(self, args):
		self.args = args
		self.config_obj = fedex_config()

	def validate(self):
		pass

	def schedule_pickup(self, request_data):
		shipper_details, closing_time, company = self.get_company_data(request_data)

		pickup_service = FedexCreatePickupRequest(self.config_obj)
		pickup_service.OriginDetail.PickupLocation.Contact.PersonName = shipper_details.get("address_title")
		pickup_service.OriginDetail.PickupLocation.Contact.EMailAddress = request_data.get("email_id") or shipper_details.get("email_id")
		pickup_service.OriginDetail.PickupLocation.Contact.CompanyName = company
		pickup_service.OriginDetail.PickupLocation.Contact.PhoneNumber = shipper_details.get("phone")
		pickup_service.OriginDetail.PickupLocation.Address.StateOrProvinceCode = shipper_details.get("state_code")
		pickup_service.OriginDetail.PickupLocation.Address.PostalCode = shipper_details.get("pincode")
		pickup_service.OriginDetail.PickupLocation.Address.CountryCode = shipper_details.get("country_code")
		pickup_service.OriginDetail.PickupLocation.Address.StreetLines = [shipper_details.get("address_line1"),\
																	 shipper_details.get("address_line2")]
		pickup_service.OriginDetail.PickupLocation.Address.City = shipper_details.get("city")
		pickup_service.OriginDetail.PickupLocation.Address.Residential = True if shipper_details.get("is_residential_address") \
																			else False
		pickup_service.OriginDetail.PackageLocation = 'NONE'
		pickup_service.OriginDetail.ReadyTimestamp = get_datetime(request_data.get("ready_time")).replace(microsecond=0).isoformat()
		pickup_service.OriginDetail.CompanyCloseTime = closing_time if closing_time else '20:00:00'
		pickup_service.CarrierCode = 'FDXE'
		pickup_service.PackageCount = request_data.get("package_count")

		package_weight = pickup_service.create_wsdl_object_of_type('Weight')
		package_weight.Units = FedExController.uom_mapper.get(request_data.get("uom"))
		package_weight.Value = request_data.get("gross_weight")
		pickup_service.TotalWeight = package_weight

		pickup_service.send_request()
		if pickup_service.response.HighestSeverity not in ["SUCCESS", "NOTE", "WARNING"]:
			self.show_notification(pickup_service)
			frappe.throw(_('Pickup service scheduling failed.'))
		return { "response": pickup_service.response.HighestSeverity,
				  "pickup_id": pickup_service.response.PickupConfirmationNumber,
				  "location_no": pickup_service.response.Location
				}

	def show_notification(self, shipment):
		for notification in shipment.response.Notifications:
			frappe.msgprint(_('Code: %s, %s' % (notification.Code, notification.Message)))

	@staticmethod
	def get_company_data(request_data):
		shipper_details = frappe.db.get_value("Address", request_data.get("shipper_id"), "*", as_dict=True)
		company = frappe.db.get_value("Delivery Note", request_data.get("delivery_note"), "company")
		closing_time = frappe.db.get_value("Company", shipper_details.get("company"), "closing_time")
		return shipper_details, closing_time, company
