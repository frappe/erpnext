import frappe
from frappe.contacts.doctype.address.address import Address
from frappe.contacts.address_and_contact import set_link_title
from frappe.core.doctype.dynamic_link.dynamic_link import deduplicate_dynamic_links

class CustomAddress(Address):
	def validate(self):
		self.link_address()
		self.validate_reference()
		super(CustomAddress, self).validate_preferred_address()
		set_link_title(self)
		deduplicate_dynamic_links(self)

	def validate_reference(self):
		if self.is_your_company_address:
			if not [row for row in self.links if row.link_doctype == "Company"]:
				frappe.throw(_("Address needs to be linked to a Company. Please add a row for Company in the Links table below."),
					title =_("Company not Linked"))
	
	def link_address(self):
		"""Link address based on owner"""
		if not self.links and not self.is_your_company_address:
			contact_name = frappe.db.get_value("Contact", {"email_id": self.owner})
			if contact_name:
				contact = frappe.get_cached_doc('Contact', contact_name)
				print('here', str(contact))
				for link in contact.links:
					self.append('links', dict(link_doctype=link.link_doctype, link_name=link.link_name))
				return True

		return False