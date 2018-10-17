from frappe import _

doctype_list = [
    'Purchase Receipt',
    'Purchase Invoice',
    'Quotation',
    'Sales Order',
    'Delivery Note',
    'Sales Invoice'
]

def get_message(doctype):
    return _("{0} has been submitted successfully".format(_(doctype)))

def get_first_success_message(doctype):
    return _("{0} has been submitted successfully".format(_(doctype)))

def get_default_success_action():
    return [{
        'doctype': 'Success Action',
        'ref_doctype': doctype,
        'message': get_message(doctype),
        'first_success_message': get_first_success_message(doctype),
        'next_actions': 'new\nprint\nemail'
    } for doctype in doctype_list]

