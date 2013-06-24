---
{
	"_label": "Download ERPNext",
	"_icon": "download"
}
---
### Download a pre-installed Virtual Box Image

#### How To Install

> You will need Oracle's Virtual Box to use the image:

[https://www.virtualbox.org/](https://www.virtualbox.org/)

Import the .ova file into VirtualBox. Though the default settings of the appliance should be good enough for most users, you may need to change them if you face performace issues.

Also, you will need to change its timezone to match yours, once the Virtual Machine boots up.

The virtual appliance uses Elementary OS.

The credentials of the virtual image are:

- username: erpnext
- password: erpnext
- mysql root password: erpnext
- erpnext database name: erpnext
- erpnext database password: erpnext

Once the Virtual Machine boots, you need to start firefox, go to:

http://localhost:8080

and login using:

- user: Administrator
- password: admin

#### Download Image

[https://erpnext.com/downloads/erpnext-1305.ova](https://erpnext.com/downloads/erpnext-1305.ova) (~1.6 GB, MD5 Checksum - 60fe727f3a7a689edb6b2d4bd0ff55ad)

Created on 15th May 2013.

---

### Get the Source

#### wnframework

The web application framework that powers ERPNext:

- [https://github.com/webnotes/wnframework](https://github.com/webnotes/wnframework)

#### erpnext

ERPNext modules:

- [https://github.com/webnotes/erpnext](https://github.com/webnotes/erpnext)