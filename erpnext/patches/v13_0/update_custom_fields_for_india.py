import frappe

from erpnext.regional.india import states
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    company = frappe.get_all('Company', filters = {'country': 'India'})
    if not company:
        return

    # create custom fields
    custom_fields = {
        'Address': [
            dict(fieldname='gst_category',label='GST Category',fieldtype='Select', insert_after='gstin',
                options='Registered Regular\nRegistered Composition\nUnregistered\nSEZ\nOverseas\nConsumer\nDeemed Export\nUIN Holders',
                default='Unregistered'),
            dict(fieldname='export_type', label='Export Type', fieldtype='Select', insert_after='gst_category',
                depends_on='eval:in_list(["SEZ", "Overseas", "Deemed Export"], doc.gst_category)',
                options='\nWith Payment of Tax\nWithout Payment of Tax',
                mandatory_depends_on='eval:in_list(["SEZ", "Overseas", "Deemed Export"], doc.gst_category)'),
            dict(fieldname='gst_state', label='GST State', fieldtype='Select',
                options='\n'.join(states), insert_after='export_type'),
        ]
    }
    create_custom_fields(custom_fields, update=True)

    #patch fields created
    link = frappe.qb.DocType('Dynamic Link')
    cust = frappe.qb.DocType('Customer')
    supp = frappe.qb.DocType('Supplier')

    cust_addr = (frappe.qb.from_(link)
        .join(cust)
        .on(link.link_name == cust.name)
        .select(link.parent, cust.gst_category, cust.export_type)
        .where(link.parenttype == 'Address' )
        .where(link.link_doctype == 'Customer')
        .limit(3)).run(as_dict = True)

    supp_addr = (frappe.qb.from_(link)
        .join(supp)
        .on(link.link_name == supp.name)
        .select(link.parent, supp.gst_category, supp.export_type)
        .where(link.parenttype == 'Address' )
        .where(link.link_doctype == 'Supplier')
        .limit(3)).run(as_dict = True)

    address = cust_addr + supp_addr


    for addr in address:
        frappe.db.set_value('Address', addr.parent, {
            'gst_category': addr.gst_category,
            'export_type': addr.export_type
        })
    frappe.db.commit()

    # delete custom fields
    cf = frappe.qb.DocType('Custom Field')
    field_to_delete = (frappe.qb.from_(cf)
        .select(cf.name, cf.dt, cf.fieldname)
        .where((cf.dt == 'Customer') | (cf.dt == 'Supplier'))
        .where((cf.fieldname == 'export_type') | (cf.fieldname == 'gst_category'))
        ).run(as_dict = True)

    for field in field_to_delete:
        frappe.delete_doc('Custom Field', field.name)
    frappe.db.commit()