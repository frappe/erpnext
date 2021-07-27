submit_so = () => {
    frappe.call({
        method: 'nextsales.www.shipping_details.make_so',
        args : {
            item_list : 'test'
        },
        callback: function(r) {
            if (!r.exc) {
                // console.log("msg: ",r.message )
                frappe.msgprint(__(`Sales Order ${r.message.so_name} submitted successfully`));
                $("#submit_so").hide()
            }
        }
    });
}

handleCustomerAddress = (e) => {
    frappe.call({
        method: 'nextsales.www.shipping_details.handle_address',
        args : {
            name : {key: "custom_add" ,value: e.target.value}
        },
        callback: function(r) {
            if (!r.exc) {
                let addressElement = []
                if(r.message.address_line1) {
                    addressElement.push(r.message.address_line1)
                }
                if(r.message.address_line2) {
                    addressElement.push(r.message.address_line2)
                }
                if(r.message.city) {
                    addressElement.push("<br/>"+r.message.city)
                }
                if(r.message.county) {
                    addressElement.push(r.message.county)
                }
                if(r.message.state) {
                    addressElement.push("<br/>"+r.message.state)
                }
                if(r.message.country) {
                    addressElement.push(r.message.country+"<br/>")
                }
                if(r.message.pincode) {
                    addressElement.push("<b>Pincode : </b>"+r.message.pincode)
                }
                 let addressString = addressElement.toString().split(',')
    
                document.getElementById("bill_add_gst").innerHTML = r.message.gstin;
                document.getElementById("cust_add").innerHTML = addressString;
            }
        }
    });

}

handleShippingAddress = e => {
    frappe.call({
        method: 'nextsales.www.shipping_details.handle_address',
        args : {
            name : {key: "ship_add" ,value: e.target.value}
        },
        callback: function(r) {
            if (!r.exc) {
                let addressElement = []
                if(r.message.address_line1) {
                    addressElement.push(r.message.address_line1)
                }
                if(r.message.address_line2) {
                    addressElement.push(r.message.address_line2)
                }
                if(r.message.city) {
                    addressElement.push("<br/>"+r.message.city)
                }
                if(r.message.county) {
                    addressElement.push(r.message.county)
                }
                if(r.message.state) {
                    addressElement.push("<br/>"+r.message.state)
                }
                if(r.message.country) {
                    addressElement.push(r.message.country+"<br/>")
                }
                if(r.message.pincode) {
                    addressElement.push("<b>Pincode : </b>"+r.message.pincode)
                }
                 let addressString = addressElement.toString().split(',')
                document.getElementById("ship_add_gst").innerHTML = r.message.gstin;
                document.getElementById("shipping_add").innerHTML = addressString;
                document.getElementById("place_of_supply").innerHTML = r.message.gst_state;
            }
        }
    });
}
