<b>Material Request Type</b>: {{ doc.material_request_type }}<br>
<b>Company</b>: {{ doc.company }}

<h3>Order Summary</h3>

<table border=2 >
    <tr align="center">
        <th>Item Name</th>
        <th>Received Quantity</th>
    </tr>
    {% for item in doc.items %}
        {% if frappe.utils.flt(item.received_qty, 2) > 0.0 %}
            <tr align="center">
                <td>{{ item.item_code }}</td>
                <td>{{ frappe.utils.flt(item.received_qty, 2) }}</td>
            </tr>
        {% endif %}
    {% endfor %}
</table>