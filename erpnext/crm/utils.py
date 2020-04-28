import frappe


def update_lead_phone_numbers(contact, method):
	if contact.phone_nos:
		contact_lead = contact.get_link_for("Lead")
		if contact_lead:
			phone = mobile_no = contact.phone_nos[0].phone

			if len(contact.phone_nos) > 1:
				# get the default phone number
				primary_phones = [phone.phone for phone in contact.phone_nos if phone.is_primary_phone]
				if primary_phones:
					phone = primary_phones[0]

				# get the default mobile number
				primary_mobile_nos = [phone.phone for phone in contact.phone_nos if phone.is_primary_mobile_no]
				if primary_mobile_nos:
					mobile_no = primary_mobile_nos[0]

			lead = frappe.get_doc("Lead", contact_lead)
			lead.phone = phone
			lead.mobile_no = mobile_no
			lead.save()
