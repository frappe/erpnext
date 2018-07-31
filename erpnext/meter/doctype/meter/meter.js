// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.ui.form.on('Meter', {

    onload: function (frm) {
alert('meter');

    },


});


cur_frm.cscript.on_save = function (doc, dt, dn) { 
alert("meter on sve")
}

cur_frm.cscript.on_submit = function (doc, dt, dn) {



    create_sales_invoices();
    if (cur_frm.doc.external_meter_id == null) {
        api_add_meter();
        add_customer_meter();
    }

}




function create_sales_invoices() {
    var meter_recharge = cur_frm.doc.meter_recharge;
    var name_meter = name = cur_frm.doc.name;
    var items = [];
    var meter_recharge_names = [];


    for (var i in cur_frm.doc.meter_recharge) {
        if (cur_frm.doc.meter_recharge[i].sales_invoice == null) {

            item_code = "1";
            rate = cur_frm.doc.meter_recharge[i].recharge_amount;
            item = { "item_code": item_code, "rate": rate,"description": name_meter+"-"+cur_frm.meter_read.total_units_consumed};
            items.push({ "item_code": item_code, "rate": rate, "description":name_meter+"-"+cur_frm.meter_read.total_units_consumed });


            name_meter_recharge = cur_frm.doc.meter_recharge[i].name;
            meter_recharge_names.push(name_meter_recharge);







        }
    }



    if (meter_recharge_names != "" && items != "") {
        frappe.call({
            method: "meter_erp.meter.doctype.meter.meter.create_invoice",
            args: { "customer": cur_frm.doc.customer, "items": items, "name": name_meter, "meter_recharge_names": meter_recharge_names },

            callback: function (r) {


                for (var i in cur_frm.doc.meter_recharge) {
                    if (cur_frm.doc.meter_recharge[i].sales_invoice == null) {

                        cur_frm.doc.meter_recharge[i].sales_invoice = r.message;



                    }
                }

                cur_frm.refresh();



            }
        });
    }

}


frappe.ui.form.on("METER READ", "add_invoice", function (frm) {
    var meter_recharge = cur_frm.doc.meter_read;
    var name_meter = cur_frm.doc.name;
    var items = [];
    var meter_recharge_names = [];
    
    for (var i in cur_frm.doc.meter_read) {
        if (cur_frm.doc.meter_read[i].sales_invoice == null) {
            item_code = "1";
            
            rate = 0.1 * parseInt(cur_frm.doc.meter_read[i].total_units_consumed);
            item = { "item_code": item_code, "rate": rate,"description":name_meter+"-"+cur_frm.doc.meter_read[i].total_units_consumed };
            items.push({ "item_code": item_code, "rate": rate ,"description":name_meter +"-"+cur_frm.doc.meter_read[i].total_units_consumed });
            name_meter_recharge = cur_frm.doc.meter_read[i].name;
            meter_recharge_names.push(name_meter_recharge);
        }
    }
    if (meter_recharge_names != "" && items != "") {
        frappe.call({
            method: "meter_erp.meter.doctype.meter.meter.create_invoice",
            args: { "customer": cur_frm.doc.customer, "items": items, "name": name_meter, "meter_recharge_names": meter_recharge_names },

            callback: function (r) {

                cur_frm.doc.meter_read[i].sales_invoice = r.message;
                cur_frm.refresh();



            }
        });
    }


});






function api_add_meter() {
    var data = {
        "key": cur_frm.doc.key,
        "logKey": cur_frm.doc.lon_gkey,
        "latitude": cur_frm.doc.latitude,
        "longitude": cur_frm.doc.lo_gitude,
        "createdAt": convert_datetime_to_timestamp(cur_frm.doc.creation),
        "createdBy": (frappe.user).toString(),
        "updatedAt": convert_datetime_to_timestamp(cur_frm.doc.modified),
        "updatedby": (frappe.user).toString(),
        "model": cur_frm.doc.model,
        "type": cur_frm.doc.type,
        "purchaseDate": 1511679448000,
        "installDate": convert_datetime_to_timestamp(cur_frm.doc.install_date),
        "collector": {
            "id": 3,
            "key": 123456,
            "logKey": 123456,
            "latitude": "update latitude",
            "longitude": "update longitude ",
            "createdAt": 1516197019000,
            "createdBy": "sm_user",
            "updatedAt": 1516197078000,
            "updatedby": "sm_user"
        },
        "mainMeter": {
            "id": 3,
            "key": 123456,
            "logKey": 123456,
            "latitude": "update latitude",
            "longitude": "update longitude ",
            "createdAt": 1516197123000,
            "createdBy": "sm_user",
            "updatedAt": 1516197154000,
            "updatedby": "sm_user"
        }
    };



    frappe.call({

        method: "meter_erp.meter.doctype.meter.meter.add_meter",
        args: { "data": data, "name_meter": cur_frm.doc.name },

        callback: function (r) {
            cur_frm.doc.external_meter_id = r.message.id;
            cur_frm.refresh_field("external_meter_id");
            cur_frm.refresh();
            console.log(r.message);

            if (cur_frm.doc.external_meter_id != null && cur_frm.doc.meter_recharge.length > 0) {
                api_add_meterrecharge();
            }

            if (cur_frm.doc.external_meter_id != null && cur_frm.doc.meter_read.length > 0) {
                api_add_meterread();
            }

        }
    });

}




function add_customer_meter() {

    frappe.call({

        method: "meter_erp.meter.doctype.meter.meter.add_customer_meter",
        args: { "meter_id": cur_frm.doc.name, "customer": cur_frm.doc.customer },

        callback: function (r) {
            console.log(r.message);
        }
    });

}









function api_add_meterrecharge() {
    var meter_recharges = []




    for (var i in cur_frm.doc.meter_recharge) {

        meter_recharge = {
            "meter": {
                "id": cur_frm.doc.external_meter_id
            },
            "recharge_date": convert_datetime_to_timestamp(cur_frm.doc.meter_recharge[i].recharge_date),
            "recharge_units": cur_frm.doc.meter_recharge[i].recharge_units,
            "recharge_no": cur_frm.doc.meter_recharge[i].recharge_no
        }

        meter_recharges.push(meter_recharge);

    }


    var meter_recharge_names = [];



    for (var i in cur_frm.doc.meter_recharge) {



        name_meter_recharge = cur_frm.doc.meter_recharge[i].name;

        meter_recharge_names.push(name_meter_recharge);

    }

    frappe.call({

        method: "meter_erp.meter.doctype.meter.meter.add_meterrecharge",
        args: { "data": meter_recharges, "meter_recharge_names": meter_recharge_names },

        callback: function (r) {

            for (var i in cur_frm.doc.meter_recharge) {
                //   cur_frm.doc.meter_recharge[i].external_meter_recharge_id = r.message.id;
            }
            console.log(r.message);

        }
    });
    cur_frm.refresh();



}









function api_add_meterread() {
    var meter_reads = []

    for (var i in cur_frm.doc.meter_read) {

        meter_read = {
            "model": cur_frm.doc.model,
            "type": cur_frm.doc.type,
            "readDate": convert_datetime_to_timestamp(cur_frm.doc.meter_read[i].read_date),
            "unitsBalance": cur_frm.doc.meter_read[i].unit_is_balance,
            "totalUnitsconsumed": cur_frm.doc.meter_read[i].total_units_consumed,
            "lastRechargeDate": convert_datetime_to_timestamp(cur_frm.doc.meter_read[i].last_recharge_date),
            "lastRechargeUnits": cur_frm.doc.meter_read[i].last_recharge_unit,
            "lastRechargeNumber": cur_frm.doc.meter_read[i].last_recharge_no,
            "bateryLife": cur_frm.doc.meter_read[i].battery_life,
            "meterState": cur_frm.doc.meter_read[i].meter_states,
            "meter": {
                "id": cur_frm.doc.external_meter_id
            }
        }

        meter_reads.push(meter_read);
    }




    var meter_reads_names = [];



    for (var i in cur_frm.doc.meter_read) {



        name_meter_read = cur_frm.doc.meter_read[i].name;
        meter_reads_names.push(name_meter_read);

    }

    frappe.call({

        method: "meter_erp.meter.doctype.meter.meter.api_add_meterread",
        args: { "data": meter_reads, "meter_reads_names": meter_reads_names },

        callback: function (r) {

            console.log(r.message);

        }
    });
    cur_frm.refresh();



}



function convert_datetime_to_timestamp(datetime) {
alert("convertdate-->>");
    //datetime="2018-01-22 04:26:24.719280"
    var y = datetime.slice(0, 4);
    var M = datetime.slice(5, 7);
    var d = datetime.slice(8, 10);
    var h = datetime.slice(11, 13);
    var m = datetime.slice(14, 16);
    var s = datetime.slice(17, 19);

    var date = new Date(y, parseInt(M) - 1, d, h, m, s);

    date = date.getTime();
    return date;
}