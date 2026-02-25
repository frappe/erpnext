To add an **Address Template** for your country, place a new file in this directory:

  * File name: `your_country.html` (lower case with underscores)
  * File content: a [Jinja Template](http://jinja.pocoo.org/docs/templates/).

All the fields of **Address** (including Custom Fields, if any) will be available to the template. Example:

```jinja
{{ address_line1 }}<br>
{% if address_line2 %}{{ address_line2 }}<br>{% endif -%}
{{ city }}<br>
{% if state %}{{ state }}<br>{% endif -%}
{% if pincode %} PIN:  {{ pincode }}<br>{% endif -%}
{{ country }}<br>
{% if phone %}Phone: {{ phone }}<br>{% endif -%}
{% if fax %}Fax: {{ fax }}<br>{% endif -%}
{% if email_id %}Email: {{ email_id }}<br>{% endif -%}
```
