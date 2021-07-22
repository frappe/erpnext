import os
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup(company=None, patch=True):
	make_custom_fields()
def make_custom_fields():
	custom_fields = {
        'Material Request': [
            dict(fieldname='date_nepal', label='Date(Nepal)',fieldtype='Data', insert_after='transaction_date', translatable=0, read_only=1),
            dict(fieldname='required_by_nepal', label='Required By(Nepal)',fieldtype='Data', insert_after='schedule_date', translatable=0, read_only=1)
        ],
        'Purchase Order': [
            dict(fieldname='date_nepal', label='Date(Nepal)',fieldtype='Data', insert_after='transaction_date', translatable=0, read_only=1),
            dict(fieldname='required_by_nepal', label='Required By(Nepal)',fieldtype='Data', insert_after='schedule_date', translatable=0, read_only=1),
            dict(fieldname='from_date_nepal', label='From Date(Nepal)',fieldtype='Data', insert_after='from_date', translatable=0, read_only=1),
            dict(fieldname='to_date_nepal', label='To Date(Nepal)',fieldtype='Data', insert_after='to_date', translatable=0, read_only=1)
        ],
        'Purchase Invoice': [
            dict(fieldname='date_nepal', label='Date(Nepal)',fieldtype='Data', insert_after='posting_date', translatable=0, read_only=1),
            dict(fieldname='due_date_nepal', label='Due Date(Nepal)',fieldtype='Data', insert_after='due_date', translatable=0, read_only=1),
            dict(fieldname='from_date_nepal', label='From Date(Nepal)',fieldtype='Data', insert_after='from_date', translatable=0, read_only=1),
            dict(fieldname='to_date_nepal', label='To Date(Nepal)',fieldtype='Data', insert_after='to_date', translatable=0, read_only=1)
        ],
        'Request for Quotation': [
            dict(fieldname='date_nepal', label='Date(Nepal)',fieldtype='Data', insert_after='transaction_date', translatable=0, read_only=1),
        ],
        'Supplier Quotation': [
            dict(fieldname='date_nepal', label='Date(Nepal)',fieldtype='Data', insert_after='transaction_date', translatable=0, read_only=1),
            dict(fieldname='valid_till_nepal', label='Valid Till(Nepal)',fieldtype='Data', insert_after='valid_till', translatable=0, read_only=1),
        ],
        'Item Price': [
            dict(fieldname='valid_from_nepal', label='Valid From(Nepal)',fieldtype='Data', insert_after='valid_from', translatable=0, read_only=1),
            dict(fieldname='valid_upto_nepal', label='Valid Upto(Nepal)',fieldtype='Data', insert_after='valid_upto', translatable=0, read_only=1),
        ],
        'Promotional Scheme': [
            dict(fieldname='valid_from_nepal', label='Valid From(Nepal)',fieldtype='Data', insert_after='valid_from', translatable=0, read_only=1),
            dict(fieldname='valid_upto_nepal', label='Valid Upto(Nepal)',fieldtype='Data', insert_after='valid_upto', translatable=0, read_only=1),
        ],
        'Pricing Rule': [
            dict(fieldname='valid_from_nepal', label='Valid From(Nepal)',fieldtype='Data', insert_after='valid_from', translatable=0, read_only=1),
            dict(fieldname='valid_upto_nepal', label='Valid Upto(Nepal)',fieldtype='Data', insert_after='valid_upto', translatable=0, read_only=1),
        ],
        'Sales Order': [
            dict(fieldname='date_nepal', label='Date(Nepal)',fieldtype='Data', insert_after='transaction_date', translatable=0, read_only=1),
            dict(fieldname='dalivery_date_nepal', label='Delivery Date(Nepal)',fieldtype='Data', insert_after='delivery_date', translatable=0, read_only=1),
            dict(fieldname='from_date_nepal', label='From Date(Nepal)',fieldtype='Data', insert_after='from_date', translatable=0, read_only=1),
            dict(fieldname='to_date_nepal', label='To Date(Nepal)',fieldtype='Data', insert_after='to_date', translatable=0, read_only=1)
        ],
        'Blanket Order': [
            dict(fieldname='from_date_nepal', label='From Date(Nepal)',fieldtype='Data', insert_after='from_date', translatable=0, read_only=1),
            dict(fieldname='to_date_nepal', label='To Date(Nepal)',fieldtype='Data', insert_after='to_date', translatable=0, read_only=1)
        ],
        'Coupon Code': [
            dict(fieldname='valid_from_nepal', label='Valid From(Nepal)',fieldtype='Data', insert_after='valid_from', translatable=0, read_only=1),
            dict(fieldname='valid_upto_nepal', label='Valid Upto(Nepal)',fieldtype='Data', insert_after='valid_upto', translatable=0, read_only=1),
        ],
        'Lead': [
            dict(fieldname='contact_date_nepal', label='Next Contact Date(Nepal)',fieldtype='Data', insert_after='contact_date', translatable=0, read_only=1),
            dict(fieldname='ends_on_nepal', label='Ends On(Nepal)',fieldtype='Data', insert_after='ends_on', translatable=0, read_only=1),
        ],
        'Email Campaign': [
            dict(fieldname='start_date_nepal', label='Start Date(Nepal)',fieldtype='Data', insert_after='start_date', translatable=0, read_only=1),
        ],
        'Social Media Post': [
            dict(fieldname='scheduled_time_nepal', label='Scheduled Time(Nepal)',fieldtype='Data', insert_after='scheduled_time', translatable=0, read_only=1),
        ],
        'Maintenance Schedule': [
            dict(fieldname='date_nepal', label='Date(Nepal)',fieldtype='Data', insert_after='transaction_date', translatable=0, read_only=1),
        ],
        'Warranty Claim': [
            dict(fieldname='issue_date_nepal', label='Issue Date(Nepal)',fieldtype='Data', insert_after='complaint_date', translatable=0, read_only=1),
            dict(fieldname='warranty_expire_date_nepal', label='Warranty Expire Date(Nepal)',fieldtype='Data', insert_after='warranty_expiry_date', translatable=0, read_only=1),
            dict(fieldname='amc_expire_date_nepal', label='AMC Expire Date(Nepal)',fieldtype='Data', insert_after='amc_expiry_date', translatable=0, read_only=1),
            dict(fieldname='resolution_date_date_nepal', label='Resolution Date(Nepal)',fieldtype='Data', insert_after='resolution_date', translatable=0, read_only=1)
        ],
        'Salary Structure Assignment': [
            dict(fieldname='from_date_nepal', label='From Date(Nepal)',fieldtype='Data', insert_after='from_date', translatable=0, read_only=1),
        ],
        'Payroll Entry': [
            dict(fieldname='posting_date_nepal', label='Posting Date(Nepal)',fieldtype='Data', insert_after='posting_date', translatable=0, read_only=1),
            dict(fieldname='start_date_nepal', label='Start Date(Nepal)',fieldtype='Data', insert_after='start_date', translatable=0, read_only=1),
            dict(fieldname='end_date_nepal', label='End Date(Nepal)',fieldtype='Data', insert_after='end_date', translatable=0, read_only=1),
        ],
        'Salary Slip': [
            dict(fieldname='posting_date_nepal', label='Posting Date(Nepal)',fieldtype='Data', insert_after='posting_date', translatable=0, read_only=1),
            dict(fieldname='start_date_nepal', label='Start Date(Nepal)',fieldtype='Data', insert_after='start_date', translatable=0, read_only=1),
            dict(fieldname='end_date_nepal', label='End Date(Nepal)',fieldtype='Data', insert_after='end_date', translatable=0, read_only=1),
        ],
        'Payroll Period': [
            dict(fieldname='start_date_nepal', label='Start Date(Nepal)',fieldtype='Data', insert_after='start_date', translatable=0, read_only=1),
            dict(fieldname='end_date_nepal', label='End Date(Nepal)',fieldtype='Data', insert_after='end_date', translatable=0, read_only=1),
        ],
        'Income Tax Slab': [
            dict(fieldname='effective_from_nepal', label='Effective From(Nepal)',fieldtype='Data', insert_after='effective_from', translatable=0, read_only=1),
        ],
        # 'Lead Details': [
        #     dict(fieldname='valid_from_nepal', label='Valid From(Nepal)',fieldtype='Data', insert_after='valid_from', translatable=0, read_only=1),
        #     dict(fieldname='valid_upto_nepal', label='Valid Upto(Nepal)',fieldtype='Data', insert_after='valid_upto', translatable=0, read_only=1),
        # ],
        'Fiscal Year': [
            dict(fieldname='year_start_date_nepal', label='Year Start Date(Nepal)',fieldtype='Data', insert_after='year_start_date', translatable=0, read_only=1),
            dict(fieldname='year_end_date_nepal', label='Year End Date(Nepal)',fieldtype='Data', insert_after='year_end_date', translatable=0, read_only=1),
        ],
        'GL Entry': [
            dict(fieldname='posting_datenepali', label='Posting Date(Nepal)',fieldtype='Data', insert_after='posting_date', translatable=0, read_only=1),
        ],
	}
	create_custom_fields(custom_fields)

    