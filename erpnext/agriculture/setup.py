from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.setup.utils import insert_record

def setup_agriculture():
	if frappe.get_all('Agriculture Analysis Criteria'):
		# already setup
		return
	create_agriculture_data()

def create_agriculture_data():
	records = [
		dict(
			doctype='Item Group',
			item_group_name='Fertilizer',
			is_group=0,
			parent_item_group=_('All Item Groups')),
		dict(
			doctype='Item Group',
			item_group_name='Seed',
			is_group=0,
			parent_item_group=_('All Item Groups')),
		dict(
			doctype='Item Group',
			item_group_name='By-product',
			is_group=0,
			parent_item_group=_('All Item Groups')),
		dict(
			doctype='Item Group',
			item_group_name='Produce',
			is_group=0,
			parent_item_group=_('All Item Groups')),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Nitrogen Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Phosphorous Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Potassium Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Calcium Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Sulphur Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Magnesium Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Iron Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Copper Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Zinc Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Boron Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Manganese Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Chlorine Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Molybdenum Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Sodium Content',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Humic Acid',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Fulvic Acid',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Inert',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Others',
			standard=1,
			linked_doctype='Fertilizer'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Nitrogen',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Phosphorous',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Potassium',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Calcium',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Magnesium',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Sulphur',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Boron',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Copper',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Iron',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Manganese',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Zinc',
			standard=1,
			linked_doctype='Plant Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Depth (in cm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Soil pH',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Salt Concentration (%)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Organic Matter (%)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='CEC (Cation Exchange Capacity) (MAQ/100mL)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Potassium Saturation (%)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Calcium Saturation (%)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Manganese Saturation (%)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Nirtogen (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Phosphorous (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Potassium (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Calcium (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Magnesium (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Sulphur (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Copper (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Iron (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Manganese (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Zinc (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Aluminium (ppm)',
			standard=1,
			linked_doctype='Soil Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Water pH',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Conductivity (mS/cm)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Hardness (mg/CaCO3)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Turbidity (NTU)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Odor',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Color',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Nitrate (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Nirtite (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Calcium (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Magnesium (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Sulphate (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Boron (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Copper (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Iron (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Manganese (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Zinc (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Chlorine (mg/L)',
			standard=1,
			linked_doctype='Water Analysis'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Bulk Density',
			standard=1,
			linked_doctype='Soil Texture'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Field Capacity',
			standard=1,
			linked_doctype='Soil Texture'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Wilting Point',
			standard=1,
			linked_doctype='Soil Texture'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Hydraulic Conductivity',
			standard=1,
			linked_doctype='Soil Texture'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Organic Matter',
			standard=1,
			linked_doctype='Soil Texture'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Temperature High',
			standard=1,
			linked_doctype='Weather'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Temperature Low',
			standard=1,
			linked_doctype='Weather'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Temperature Average',
			standard=1,
			linked_doctype='Weather'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Dew Point',
			standard=1,
			linked_doctype='Weather'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Precipitation Received',
			standard=1,
			linked_doctype='Weather'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Humidity',
			standard=1,
			linked_doctype='Weather'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Pressure',
			standard=1,
			linked_doctype='Weather'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Insolation/ PAR (Photosynthetically Active Radiation)',
			standard=1,
			linked_doctype='Weather'),
		dict(
			doctype='Agriculture Analysis Criteria',
			title='Degree Days',
			standard=1,
			linked_doctype='Weather')
	] 
	insert_record(records)
