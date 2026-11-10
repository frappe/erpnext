from urllib.parse import urlparse

import frappe


def get_webhook_address(connector_name, method, exclude_uri=False, force_https=False):
	endpoint = f"erpnext.erpnext_integrations.connectors.{connector_name}.{method}"

	if exclude_uri:
		return endpoint

	try:
		url = frappe.request.url
	except RuntimeError:
		url = "http://localhost:8000"

	url_data = urlparse(url)
	scheme = "https" if force_https else url_data.scheme
	netloc = url_data.netloc

	server_url = f"{scheme}://{netloc}/api/method/{endpoint}"

	return server_url
