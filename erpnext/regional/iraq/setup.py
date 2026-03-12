import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission, update_permission_property


def setup(company=None, patch=True):
	make_custom_fields()


def make_custom_fields():
	iraq_fields = [
		dict(
			fieldname="iraq_tax_section",
			label="Tax Details / تفاصيل الضريبة / وردەکاری باج",
			fieldtype="Section Break",
			insert_after="language",
			print_hide=1,
			collapsible=1,
		),
		dict(
			fieldname="tax_registration_number",
			label="Tax Registration Number / الرقم الضريبي / ژمارەی تۆمارکردنی باج",
			fieldtype="Data",
			insert_after="iraq_tax_section",
			print_hide=0,
		),
	]

	custom_fields = {
		"Company": [
			dict(
				fieldname="iraq_tax_id",
				label="Tax ID / الرقم الضريبي / ژمارەی باج",
				fieldtype="Data",
				insert_after="tax_id",
			),
			dict(
				fieldname="social_security_number",
				label="Social Security Number / رقم الضمان الاجتماعي / ژمارەی دڵنیایی کۆمەڵایەتی",
				fieldtype="Data",
				insert_after="iraq_tax_id",
			),
			dict(
				fieldname="commercial_registration",
				label="Commercial Registration / السجل التجاري / تۆماری بازرگانی",
				fieldtype="Data",
				insert_after="social_security_number",
			),
		],
		"Customer": [
			dict(
				fieldname="customer_name_in_arabic",
				label="Customer Name in Arabic / اسم الزبون بالعربية",
				fieldtype="Data",
				insert_after="customer_name",
			),
			dict(
				fieldname="customer_name_in_kurdish",
				label="Customer Name in Kurdish / ناوی کڕیار بە کوردی",
				fieldtype="Data",
				insert_after="customer_name_in_arabic",
			),
			dict(
				fieldname="customer_tax_id",
				label="Tax ID / الرقم الضريبي / ژمارەی باج",
				fieldtype="Data",
				insert_after="tax_id",
			),
		],
		"Supplier": [
			dict(
				fieldname="supplier_name_in_arabic",
				label="Supplier Name in Arabic / اسم المجهز بالعربية",
				fieldtype="Data",
				insert_after="supplier_name",
			),
			dict(
				fieldname="supplier_name_in_kurdish",
				label="Supplier Name in Kurdish / ناوی دابینکەر بە کوردی",
				fieldtype="Data",
				insert_after="supplier_name_in_arabic",
			),
			dict(
				fieldname="supplier_tax_id",
				label="Tax ID / الرقم الضريبي / ژمارەی باج",
				fieldtype="Data",
				insert_after="tax_id",
			),
		],
		"Sales Invoice": iraq_fields,
		"Purchase Invoice": iraq_fields,
		"Sales Order": iraq_fields,
		"Purchase Order": iraq_fields,
		"Address": [
			dict(
				fieldname="governorate",
				label="Governorate / المحافظة / پارێزگا",
				fieldtype="Select",
				insert_after="state",
				options="\n".join([
					"",
					"Baghdad / بغداد / بەغدا",
					"Basra / البصرة / بەسرە",
					"Maysan / ميسان / مەیسان",
					"Dhi Qar / ذي قار / زیقار",
					"Muthanna / المثنى / موسەننا",
					"Qadisiyyah / القادسية / قادسییە",
					"Babylon / بابل / بابل",
					"Karbala / كربلاء / کەربەلا",
					"Najaf / النجف / نەجەف",
					"Wasit / واسط / واسط",
					"Diyala / ديالى / دیالە",
					"Saladin / صلاح الدين / سەلاحەددین",
					"Kirkuk / كركوك / کەرکوک",
					"Nineveh / نينوى / نەینەوا",
					"Anbar / الأنبار / ئەنبار",
					"Erbil / أربيل / هەولێر",
					"Duhok / دهوك / دهۆک",
					"Sulaymaniyah / السليمانية / سلێمانی",
				]),
			),
		],
	}

	create_custom_fields(custom_fields, ignore_validate=True)


def update_regional_tax_settings(country=None, company=None):
	pass
