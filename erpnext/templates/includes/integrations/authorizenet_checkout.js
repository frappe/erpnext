$('#submit').on("click", function(e) {

    let data = context.replace(/'/g, '"');
    e.preventDefault();

    let cardNumber = document.getElementById('card-number').value;
    let expirationDate = document.getElementById('card-expiry').value;
    let cardCode = document.getElementById('card-code').value;

    if(cardNumber.length < 13 || cardNumber.length > 16){
        frappe.throw(__("Card number length should be between 13 and 16 characters"))
    }

    $('#submit').prop('disabled', true);
    $('#submit').html(__('Processing...'));

    frappe.call({
        method: "erpnext.erpnext_integrations.doctype.authorizenet_settings.authorizenet_settings.charge_credit_card",
        freeze: true,
        args: {
            "card_number": cardNumber,
            "expiration_date": expirationDate,
            "card_code": cardCode,
            "data": data
        },

        callback: function(r) {
            if (r.message.status === "Completed") {
                window.location.href = "/integrations/payment-success";
            } else {
                frappe.throw(__(`${r.message.description}`));
            }
        }
    })
});