# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Sample data emitted with the "Template with sample" download.

These are illustrative rows that show users what a well-formed import file
looks like. Each row is a dict keyed by target-field name — the template
writer orders columns from the schema, so values may safely be sparse.
"""

from erpnext.selling.doctype.party_import_log.schema import CUSTOMER, SUPPLIER

CUSTOMER_SAMPLES = [
	{
		"customer_name": "Acme Corp",
		"customer_type": "Company",
		"tax_id": "29ABCDE1234F1Z5",
		"customer_group": "Industrial",
		"territory": "Delhi NCR",
		"industry": "Manufacturing",
		"market_segment": "Enterprise",
		"default_currency": "INR",
		"default_price_list": "Standard Selling",
		"website": "https://acme.example",
		"credit_limit": "500000",
		"primary_first_name": "John",
		"primary_last_name": "Doe",
		"primary_email": "john.doe@acme.example",
		"primary_mobile": "+91-98765-43210",
		"primary_phone": "+91-11-2345-6789",
		"billing_address_line1": "12 MG Road",
		"billing_address_line2": "Suite 401",
		"billing_city": "New Delhi",
		"billing_state": "Delhi",
		"billing_country": "India",
		"billing_pincode": "110001",
		"shipping_address_line1": "Plot 17, Industrial Area",
		"shipping_address_line2": "Sector 32",
		"shipping_city": "Gurugram",
		"shipping_state": "Haryana",
		"shipping_country": "India",
		"shipping_pincode": "122001",
		"notes": "Sample row — replace with your data",
	},
	{
		"customer_name": "Globex Pvt Ltd",
		"customer_type": "Company",
		"tax_id": "29XYZAB5678C2D9",
		"customer_group": "Retail",
		"territory": "Bangalore",
		"industry": "Software",
		"market_segment": "SMB",
		"default_currency": "INR",
		"website": "https://globex.example",
		"credit_limit": "250000",
		"primary_first_name": "Jane",
		"primary_last_name": "Smith",
		"primary_email": "jane.smith@globex.example",
		"primary_mobile": "+91-99887-65432",
		"billing_address_line1": "45 Brigade Road",
		"billing_city": "Bangalore",
		"billing_state": "Karnataka",
		"billing_country": "India",
		"billing_pincode": "560001",
		"shipping_address_line1": "Warehouse 7, Electronic City",
		"shipping_address_line2": "Phase 2",
		"shipping_city": "Bangalore",
		"shipping_state": "Karnataka",
		"shipping_country": "India",
		"shipping_pincode": "560100",
	},
	{
		"customer_name": "Riya Mehta",
		"customer_type": "Individual",
		"customer_group": "Individual",
		"territory": "Mumbai",
		"default_currency": "INR",
		"primary_first_name": "Riya",
		"primary_last_name": "Mehta",
		"primary_email": "riya.mehta@example.com",
		"primary_mobile": "+91-98201-23456",
		"billing_address_line1": "Flat 5B, Sea View Apartments",
		"billing_address_line2": "Bandra West",
		"billing_city": "Mumbai",
		"billing_state": "Maharashtra",
		"billing_country": "India",
		"billing_pincode": "400050",
		"notes": "Individual customer example",
	},
]


SUPPLIER_SAMPLES = [
	{
		"supplier_name": "Acme Components Ltd",
		"supplier_type": "Company",
		"tax_id": "27DEFGH9876I1J2",
		"supplier_group": "Local",
		"country": "India",
		"default_currency": "INR",
		"website": "https://acme-components.example",
		"primary_first_name": "Anil",
		"primary_last_name": "Kumar",
		"primary_email": "anil@acme-components.example",
		"primary_mobile": "+91-98123-45678",
		"primary_phone": "+91-22-3456-7890",
		"billing_address_line1": "Plot 88, MIDC",
		"billing_address_line2": "Andheri East",
		"billing_city": "Mumbai",
		"billing_state": "Maharashtra",
		"billing_country": "India",
		"billing_pincode": "400093",
		"notes": "Sample supplier — replace with your data",
	},
	{
		"supplier_name": "Pacific Imports Inc",
		"supplier_type": "Company",
		"supplier_group": "International",
		"country": "United States",
		"default_currency": "USD",
		"website": "https://pacificimports.example",
		"primary_first_name": "Sarah",
		"primary_last_name": "Lee",
		"primary_email": "sarah.lee@pacificimports.example",
		"primary_mobile": "+1-415-555-0123",
		"billing_address_line1": "500 Market Street",
		"billing_address_line2": "Floor 12",
		"billing_city": "San Francisco",
		"billing_state": "CA",
		"billing_country": "United States",
		"billing_pincode": "94105",
	},
]


def samples_for(party_type: str) -> list[dict]:
	"""Return illustrative sample rows for the given party type."""
	return CUSTOMER_SAMPLES if party_type == CUSTOMER else SUPPLIER_SAMPLES
