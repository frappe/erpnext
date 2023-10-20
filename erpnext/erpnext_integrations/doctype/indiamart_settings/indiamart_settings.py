# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import http.client
import json
import requests
import datetime
from frappe.model.document import Document
from frappe.utils import today,now
from frappe.utils.password import get_decrypted_password

class IndiamartSettings(Document):
	pass


## Indiamart Integration
def indiamart_lead_integration():
	enabled=frappe.db.get_single_value('Indiamart Settings', 'enabled')
	api_url=frappe.db.get_single_value('Indiamart Settings', 'indiamart_url')
	api_key=get_decrypted_password('Indiamart Settings','Indiamart Settings', 'api_key')
	start_time=end_time=today()
	
	if enabled:
		try:
			url = f"{api_url}?glusr_crm_key={api_key}&start_time={start_time}&end_time={end_time}"
			payload={}
			headers = {}
			response = requests.request("GET", url, headers=headers, data=payload)
			response=json.loads(response.text)
			status=response["STATUS"]

			if status == "SUCCESS":
				for i in response["RESPONSE"]:
					if not frappe.db.exists("Lead", {"first_name":i["SENDER_NAME"], "mobile_no": i["SENDER_MOBILE"]}):
						doc = frappe.new_doc("Lead")
						doc.update({
							"first_name":i["SENDER_NAME"] or "",
							"source":"Indiamagirt",
							"mobile_no":i["SENDER_MOBILE"] or "",
							"status":"Lead",
							"email_id":i["SENDER_EMAIL"] or "",
							"company_name":i["SENDER_COMPANY"] or "" ,
							"source_of_lead":{"W":"Direct","B":"Consumed BuyLead","P":"Call"}.get(i["QUERY_TYPE"]),
							"city": i["SENDER_CITY"] or "",
							"state":i["SENDER_STATE"] or "",
							"pincode":i["SENDER_PINCODE"] or "",
							"notes":[{'note': f"""{i["QUERY_MESSAGE"]}""", 'added_on': now(), 'added_by': frappe.session.user}]
						})
						doc.flags.ignore_permissions = True
						doc.flags.ignore_mandatory = True
						doc.insert()
				doc = frappe.new_doc("Indiamart Sync Log")
				doc.update({
					"status": response["STATUS"] or "",
					"status_code": response["CODE"] or "",
					"total_records":response["TOTAL_RECORDS"] or "",
					"message":response["MESSAGE"] or "",
					"payload": f"{url}",
					"response" : f"{response}",
					"last_execution": frappe.utils.now()
				})
				doc.flags.ignore_permissions = True
				doc.flags.ignore_mandatory = True
				doc.insert()
				
			else:
				doc = frappe.new_doc("Indiamart Sync Log")
				doc.update({
					"status": response["STATUS"],
					"status_code": response["CODE"],
					"total_records":response["TOTAL_RECORDS"] or "",
					"message":response["MESSAGE"] or "",
					"payload": f"{url}",
					"response" : f"{response}",
					"last_execution": frappe.utils.now()
				})
				doc.flags.ignore_permissions = True
				doc.flags.ignore_mandatory = True
				doc.insert()

		except Exception as e:
			error = str(e) + frappe.get_traceback()
			frappe.log_error(error,"Indiamart Integration error")