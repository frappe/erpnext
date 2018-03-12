import frappe
from fedex.config import FedexConfig
import frappe.client as client


def fedex_config():
	settings = frappe.get_single("FedEx Settings")
	config_obj = FedexConfig(key= settings.get("fedex_key"),
		password=client.get_password("FedEx Settings", "FedEx Settings", "password"),
		account_number=settings.get("fedex_meter_no"),
		meter_number=settings.get("fedex_meter_no"),
		freight_account_number=settings.get("fedex_meter_no"),
		use_test_server=True if settings.get('is_sandbox') else False)