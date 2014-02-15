# ERPNext - Open Source ERP for small, medium sized businesses

[https://erpnext.com](https://erpnext.com)

Includes Accounting, Inventory, CRM, Sales, Purchase, Projects, HRMS. Built on Python / MySQL.

ERPNext is built on [frappe](https://github.com/frappe/frappe)

- [User Guide](http://erpnext.org/user-guide.html)
- [Getting Help](http://erpnext.org/getting-help.html)
- [Developer Forum](http://groups.google.com/group/erpnext-developer-forum)
- [User Forum](http://groups.google.com/group/erpnext-user-forum)

---

### Development install

#### Pre-requisites

1. MySQL
1. Python-2.7
1. Python Setuptools (Python Package Manager)
1. Memcache
1. libxslt

#### Steps

1. Start MySQL and memcache
1. Setup Python Virtualenv (optional - only if you are running multiple python projects requiring different versions of libraries)
1. Install pip: `sudo easy_install pip`
1. Create a `bench` directory
1. Clone `frappe` in the `bench` : `git clone https://github.com/frappe/frappe`
1. Install python libraries `sudo pip install webnotes/requirements.txt`
1. Clone `erpnext` in the `bench`: `git clone https://github.com/frappe/erpnext.git`
1. Clone `shopping-cart` in the `bench`: `git clone https://github.com/frappe/shopping-cart.git`
1. Install the packages: `pip install -e frappe/ erpnext/ shopping-cart/`
1. Create `sites` directory
1. Create `apps.txt`: `echo erpnext\nshopping_cart >> sites/apps.txt`
1. Change to `sites` directory
1. Setup a site: `frappe erpnext.local --install erpnext`
1. Install erpnext app: `frappe erpnext.local --install_app erpnext`
1. Start serving: `frappe erpnext.local --serve`
1. Start a browser and go to `http://localhost:8000`

Putting it all together:

```
sudo easy_install pip
mkdir bench
cd bench
git clone https://github.com/frappe/frappe.git
git clone https://github.com/frappe/erpnext.git
git clone https://github.com/frappe/shopping-cart.git
sudo pip install -e frappe/ erpnext/ shopping-cart/
mkdir sites
echo erpnext\nshopping_cart >> sites/apps.txt
cd sites
frappe erpnext.local --install erpnext
frappe erpnext.local --install_app erpnext
frappe erpnext.local --install_app shopping-cart
frappe erpnext.local --serve
```

#### Pulling Latest Updates

1. Update your git repositories
1. Go to `bench/sites` directory
1. Run `frappe erpnext.local --latest`
1. Run `frappe erpnext.local --build`
1. Run `frappe erpnext.local --flush`

#### Admin Login

1. go to "/login"
1. Administrator user name: "Administrator"
1. Administrator passowrd "admin"

### Download and Install

##### Virtual Image:

- [ERPNext Download](http://erpnext.com/erpnext-download)

---

## License

GNU/General Public License (see LICENSE.txt)

The ERPNext code is licensed as GNU General Public License (v3) and the Documentation is licensed as Creative Commons (CC-BY-SA-3.0) and the copyright is owned by Web Notes Technologies Pvt Ltd (Web Notes) and Contributors. 

---

## Logo and Trademark

The brand name ERPNext and the logo are trademarks of Web Notes Technologies Pvt. Ltd.

### Introduction

Web Notes Technologies Pvt. Ltd. (Web Notes) owns and oversees the trademarks for the ERPNext name and logos. We have developed this trademark usage policy with the following goals in mind:

- We’d like to make it easy for anyone to use the ERPNext name or logo for community-oriented efforts that help spread and improve ERPNext.
- We’d like to make it clear how ERPNext-related businesses and projects can (and cannot) use the ERPNext name and logo.
- We’d like to make it hard for anyone to use the ERPNext name and logo to unfairly profit from, trick or confuse people who are looking for official ERPNext resources.

### Web Notes Trademark Usage Policy

Permission from Web Notes is required to use the ERPNext name or logo as part of any project, product, service, domain or company name.

We will grant permission to use the ERPNext name and logo for projects that meet the following criteria:

- The primary purpose of your project is to promote the spread and improvement of the ERPNext software.
- Your project is non-commercial in nature (it can make money to cover its costs or contribute to non-profit entities, but it cannot be run as a for-profit project or business).
Your project neither promotes nor is associated with entities that currently fail to comply with the GPL license under which ERPNext is distributed.
- If your project meets these criteria, you will be permitted to use the ERPNext name and logo to promote your project in any way you see fit with one exception: Please do not use ERPNext as part of a domain name. 

Use of the ERPNext name and logo is additionally allowed in the following situations:

All other ERPNext-related businesses or projects can use the ERPNext name and logo to refer to and explain their services, but they cannot use them as part of a product, project, service, domain, or company name and they cannot use them in any way that suggests an affiliation with or endorsement by the ERPNext or WebNotes or the ERPNext open source project. For example, a consulting company can describe its business as “123 Web Services, offering ERPNext consulting for small businesses,” but cannot call its business “The ERPNext Consulting Company.”

Similarly, it’s OK to use the ERPNext logo as part of a page that describes your products or services, but it is not OK to use it as part of your company or product logo or branding itself. Under no circumstances is it permitted to use ERPNext as part of a top-level domain name.

We do not allow the use of the trademark in advertising, including AdSense/AdWords.

Please note that it is not the goal of this policy to limit commercial activity around ERPNext. We encourage ERPNext-based businesses, and we would love to see hundreds of them.

When in doubt about your use of the ERPNext name or logo, please contact the Web Notes Technologies for clarification.

(inspired from Wordpress)
