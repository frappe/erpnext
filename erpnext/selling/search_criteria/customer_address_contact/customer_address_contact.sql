select
    `tabCustomer`.name,
    `tabCustomer`.customer_name,
    `tabAddress`.address_line1,
    `tabAddress`.address_line2,
    `tabAddress`.city,
    `tabAddress`.state,
    `tabAddress`.pincode,
    `tabAddress`.country,
    `tabContact`.first_name,
    `tabContact`.last_name,
    `tabContact`.phone,
    `tabContact`.mobile_no,
    `tabContact`.email_id
from
    `tabCustomer`
    left join `tabAddress` on (
        `tabAddress`.customer=`tabCustomer`.name and
        ifnull(`tabAddress`.is_primary_address, 0)=1
    )
    left join `tabContact` on (
        `tabContact`.customer=`tabCustomer`.name and 
        ifnull(`tabContact`.is_primary_contact, 0)=1
    )
order by
    `tabCustomer`.customer_name asc