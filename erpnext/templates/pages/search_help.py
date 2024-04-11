import frappe
import requests
from frappe import _
from frappe.core.utils import html2text
from frappe.utils import sanitize_html
from frappe.utils.global_search import search
from jinja2 import utils


def get_context(context):
	context.no_cache = 1
	if frappe.form_dict.q:
		query = str(utils.escape(sanitize_html(frappe.form_dict.q)))
		context.title = _("Help Results for")
		context.query = query

		context.route = "/search_help"
		d = frappe._dict()
		d.results_sections = get_help_results_sections(query)
		context.update(d)
	else:
		context.title = _("Docs Search")


@frappe.whitelist(allow_guest=True)
def get_help_results_sections(text):
	out = []
	settings = frappe.get_doc("Support Settings", "Support Settings")

	for api in settings.search_apis:
		results = []
		if api.source_type == "API":
			response_json = get_response(api, text)
			topics_data = get_topics_data(api, response_json)
			results = prepare_api_results(api, topics_data)
		else:
			# Source type is Doctype
			doctype = api.source_doctype
			raw = search(text, 0, 20, doctype)
			results = prepare_doctype_results(api, raw)

		if results:
			# Add section
			out.append({"title": api.source_name, "results": results})

	return out


def get_response(api, text):
	response = requests.get(api.base_url + "/" + api.query_route, data={api.search_term_param_name: text})

	response.raise_for_status()
	return response.json()


def get_topics_data(api, response_json):
	if not response_json:
		response_json = {}
	topics_data = {}  # it will actually be an array
	key_list = api.response_result_key_path.split(",")

	for key in key_list:
		topics_data = response_json.get(key) if not topics_data else topics_data.get(key)

	return topics_data or []


def prepare_api_results(api, topics_data):
	if not topics_data:
		topics_data = []

	results = []
	for topic in topics_data:
		route = api.base_url + "/" + (api.post_route + "/" if api.post_route else "")
		for key in api.post_route_key_list.split(","):
			route += str(topic[key])

		results.append(
			frappe._dict(
				{
					"title": topic[api.post_title_key],
					"preview": html2text(topic[api.post_description_key]),
					"route": route,
				}
			)
		)
	return results[:5]


def prepare_doctype_results(api, raw):
	results = []
	for r in raw:
		prepared_result = {}
		parts = r["content"].split(" ||| ")

		for part in parts:
			pair = part.split(" : ", 1)
			prepared_result[pair[0]] = pair[1]

		results.append(
			frappe._dict(
				{
					"title": prepared_result[api.result_title_field],
					"preview": prepared_result[api.result_preview_field],
					"route": prepared_result[api.result_route_field],
				}
			)
		)

	return results
