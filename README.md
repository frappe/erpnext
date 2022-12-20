<div align="center">
    <a href="https://erpnext.com">
        <img src="https://raw.githubusercontent.com/frappe/erpnext/develop/erpnext/public/images/erpnext-logo.png" height="128">
    </a>
    <h2>ERPNext</h2>
    <p align="center">
        <p>ERP made simple</p>
    </p>

[![CI](https://github.com/frappe/erpnext/actions/workflows/server-tests.yml/badge.svg?branch=develop)](https://github.com/frappe/erpnext/actions/workflows/server-tests.yml)
[![UI](https://github.com/erpnext/erpnext_ui_tests/actions/workflows/ui-tests.yml/badge.svg?branch=develop&event=schedule)](https://github.com/erpnext/erpnext_ui_tests/actions/workflows/ui-tests.yml)
[![Open Source Helpers](https://www.codetriage.com/frappe/erpnext/badges/users.svg)](https://www.codetriage.com/frappe/erpnext)
[![codecov](https://codecov.io/gh/frappe/erpnext/branch/develop/graph/badge.svg?token=0TwvyUg3I5)](https://codecov.io/gh/frappe/erpnext)
[![docker pulls](https://img.shields.io/docker/pulls/frappe/erpnext-worker.svg)](https://hub.docker.com/r/frappe/erpnext-worker)

[https://erpnext.com](https://erpnext.com)

</div>

ERPNext as a monolith includes the following areas for managing businesses:

1. [Accounting](https://erpnext.com/open-source-accounting)
1. [Warehouse Management](https://erpnext.com/distribution/warehouse-management-system)
1. [CRM](https://erpnext.com/open-source-crm)
1. [Sales](https://erpnext.com/open-source-sales-purchase)
1. [Purchase](https://erpnext.com/open-source-sales-purchase)
1. [HRMS](https://erpnext.com/open-source-hrms)
1. [Project Management](https://erpnext.com/open-source-projects)
1. [Support](https://erpnext.com/open-source-help-desk-software)
1. [Asset Management](https://erpnext.com/open-source-asset-management-software)
1. [Quality Management](https://erpnext.com/docs/user/manual/en/quality-management)
1. [Manufacturing](https://erpnext.com/open-source-manufacturing-erp-software)
1. [Website Management](https://erpnext.com/open-source-website-builder-software)
1. [Customize ERPNext](https://erpnext.com/docs/user/manual/en/customize-erpnext)
1. [And More](https://erpnext.com/docs/user/manual/en/)

ERPNext is built on the [Frappe Framework](https://github.com/frappe/frappe), a full-stack web app framework built with Python & JavaScript.

## Installation

<div align="center" style="max-height: 40px;">
    <a href="https://frappecloud.com/erpnext/signup">
        <img src=".github/try-on-f-cloud-button.svg" height="40">
    </a>
    <a href="https://labs.play-with-docker.com/?stack=https://raw.githubusercontent.com/frappe/frappe_docker/main/pwd.yml">
      <img src="https://raw.githubusercontent.com/play-with-docker/stacks/master/assets/images/button.png" alt="Try in PWD" height="37"/>
    </a>
</div>

> Login for the PWD site: (username: Administrator, password: admin)

### Containerized Installation using install script

The Easy Install script should get you going with a Frappe/ERPNext setup with minimal manual intervention and effort.

This script uses Docker with the [Frappe/ERPNext Docker Repository](https://github.com/frappe/frappe_docker) and can be used for both Development setup and Production setup.

#### Setup

Download the Easy Install script and execute it:

```sh
$ wget https://raw.githubusercontent.com/frappe/bench/develop/easy-install.py
$ python3 easy-install.py --prod
```

This script will install docker on your system and will fetch the required containers, setup bench and a default ERPNext instance.

The script will generate MySQL root password and an Administrator password for the Frappe/ERPNext instance, which will then be saved under `$HOME/passwords.txt` of the user used to setup the instance.
It will also generate a new compose file under `$HOME/<project-name>-compose.yml`.

When the setup is complete, you will be able to access the system at `http://<your-server-ip>`, wherein you can use the Administrator password to login.

#### Usage

Here are the arguments for the easy-install script

```txt
usage: easy-install.py [-h] [-p] [-d] [-s SITENAME] [-n PROJECT] [--email EMAIL]

Install Frappe with Docker

options:
  -h, --help            show this help message and exit
  -p, --prod            Setup Production System
  -d, --dev             Setup Development System
  -s SITENAME, --sitename SITENAME
                        The Site Name for your production site
  -n PROJECT, --project PROJECT
                        Project Name
  --email EMAIL         Add email for the SSL.
```


## Learning and community

1. [Frappe School](https://frappe.school) - Learn Frappe Framework and ERPNext from the various courses by the maintainers or from the community.
2. [Official documentation](https://docs.erpnext.com/) - Extensive documentation for ERPNext.
3. [Discussion Forum](https://discuss.erpnext.com/) - Engage with community of ERPNext users and service providers.
4. [Telegram Group](https://t.me/erpnexthelp) - Get instant help from huge community of users.


## Contributing

1. [Issue Guidelines](https://github.com/frappe/erpnext/wiki/Issue-Guidelines)
1. [Report Security Vulnerabilities](https://erpnext.com/security)
1. [Pull Request Requirements](https://github.com/frappe/erpnext/wiki/Contribution-Guidelines)
1. [Translations](https://translate.erpnext.com)


## License

GNU/General Public License (see [license.txt](license.txt))

The ERPNext code is licensed as GNU General Public License (v3) and the Documentation is licensed as Creative Commons (CC-BY-SA-3.0) and the copyright is owned by Frappe Technologies Pvt Ltd (Frappe) and Contributors.

By contributing to ERPNext, you agree that your contributions will be licensed under its GNU General Public License (v3).

## Logo and Trademark Policy

Please read our [Logo and Trademark Policy](TRADEMARK_POLICY.md).
