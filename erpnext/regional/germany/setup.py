import frappe, os

def setup(company=None, patch=True):
    if not patch:
        update_address_template()


def update_address_template():
    with open(os.path.join(os.path.dirname(__file__), 'address_template.html'), 'r') as f:
        html = f.read()

    address_template = frappe.db.get_value('Address Template', 'Germany')
    if address_template:
        frappe.db.set_value('Address Template', 'Germany', 'template', html)
    else:
        # make new html template for Germany
        frappe.get_doc(dict(
            doctype='Address Template',
            country='Germany',
            template=html
        )).insert()
