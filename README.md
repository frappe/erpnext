<div align="center">

<!-- TODO: add link to website once it is ready -->
<h1>India Compliance</h1>

Simple, yet powerful compliance solutions for Indian businesses

[![Server Tests](https://github.com/resilient-tech/india-compliance/actions/workflows/server-tests.yml/badge.svg)](https://github.com/resilient-tech/india-compliance/actions/workflows/server-tests.yml)

</div>



## Introduction

India Compliance has been designed to make compliance with Indian rules and regulations simple, swift and reliable. To this end, it has been carefully integrated with GST APIs to simplify recurring compliance processes.

India Compliance builds on top of [ERPNext](https://github.com/frappe/erpnext) and the [Frappe Framework](https://github.com/frappe/frappe) - incredible FOSS projects built and maintained by the incredible folks at Frappe. Go check these out if you haven't already!

## Key Features

- End-to-end GST e-Waybill management
- Automated GST e-Invoice generation and cancellation
- Autofill Party and Address details by entering their GSTIN
- Configurable features based on business needs
- Powerful validations to ensure correct compliance

For a detailed overview of these features, please [refer to the documentation](https://docs.erpnext.com/docs/v14/user/manual/en/regional/india).

## Installation

Once you've [set up a Frappe site](https://frappeframework.com/docs/v14/user/en/installation/), installing India Compliance is simple:


1. Download the app using the Bench CLI

  ```bash
  bench get-app https://github.com/resilient-tech/india-compliance.git
  ```

2. Install the app on your site

  ```bash
  bench --site [site name] install-app india_compliance
  ```

## Planned Features

- Advanced purchase reconciliation based on GSTR-2B and GSTR-2A
- Quick and easy filing process for GSTR-1 and GSTR-3B

## Contributing

- [Issue Guidelines](https://github.com/frappe/erpnext/wiki/Issue-Guidelines)
- [Pull Request Requirements](https://github.com/frappe/erpnext/wiki/Contribution-Guidelines)

## License

[GNU General Public License (v3)](https://github.com/resilient-tech/india-compliance/blob/develop/license.txt)
