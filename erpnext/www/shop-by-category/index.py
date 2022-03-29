import frappe
from frappe import _

sitemap = 1


def get_context(context):
	context.body_class = "product-page"

	settings = frappe.get_cached_doc("E Commerce Settings")
	context.categories_enabled = settings.enable_field_filters

	if context.categories_enabled:
		categories = [row.fieldname for row in settings.filter_fields]
		context.tabs = get_tabs(categories)

	if settings.slideshow:
		context.slideshow = get_slideshow(settings.slideshow)

	context.no_cache = 1


def get_slideshow(slideshow):
	values = {"show_indicators": 1, "show_controls": 1, "rounded": 1, "slider_name": "Categories"}
	slideshow = frappe.get_cached_doc("Website Slideshow", slideshow)
	slides = slideshow.get({"doctype": "Website Slideshow Item"})
	for index, slide in enumerate(slides, start=1):
		values[f"slide_{index}_image"] = slide.image
		values[f"slide_{index}_title"] = slide.heading
		values[f"slide_{index}_subtitle"] = slide.description
		values[f"slide_{index}_theme"] = slide.get("theme") or "Light"
		values[f"slide_{index}_content_align"] = slide.get("content_align") or "Centre"
		values[f"slide_{index}_primary_action"] = slide.url

	return values


def get_tabs(categories):
	tab_values = {
		"title": _("Shop by Category"),
	}

	categorical_data = get_category_records(categories)
	for index, tab in enumerate(categorical_data, start=1):
		tab_values[f"tab_{index + 1}_title"] = frappe.unscrub(tab)
		# pre-render cards for each tab
		tab_values[f"tab_{index + 1}_content"] = frappe.render_template(
			"erpnext/www/shop-by-category/category_card_section.html",
			{"data": categorical_data[tab], "type": tab},
		)
	return tab_values


def get_category_records(categories):
	categorical_data = {}
	for category in categories:
		if category == "item_group":
			categorical_data["item_group"] = frappe.db.sql(
				"""
				Select
					name, parent_item_group, is_group, image, route
				from
					`tabItem Group`
				where
					parent_item_group = 'All Item Groups'
					and show_in_website = 1
				""",
				as_dict=1,
			)
		else:
			doctype = frappe.unscrub(category)
			fields = ["name"]
			if frappe.get_meta(doctype, cached=True).get_field("image"):
				fields += ["image"]

			categorical_data[category] = frappe.db.sql(
				f"""
					Select
						{",".join(fields)}
					from
						`tab{doctype}`
				""",
				as_dict=1,
			)

	return categorical_data
