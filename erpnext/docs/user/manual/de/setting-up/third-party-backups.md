# Drittpartei-Datensicherungen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Wenn Sie Ihre Daten regelmäßig auf Dropbox sichern möchten, können Sie das direkt über ERPNext tun.

> Einstellungen > Einbindungen > Dropbox-Datensicherung

**Schritt 1:** Klicken Sie auf Einstellungen, dann auf Einbindungen

**Schritt 2:** Klicken Sie auf Dropbox-Datensicherung

### Abbildung 1: Dropbox-Datensicherung

![Drittparteien-Datensicherung]({{docs_base_url}}/assets/old_images/erpnext/third-party-backups.png)

Geben Sie auf der Seite "Dropbox-Datensicherung" die E-Mail-Adressen der Menschen ein, die über den Sicherungsstatus informiert werden sollen. Unter dem Punkt "Häufigkeit des Hochladens" geben Sie an, ob die Daten täglich oder wöchentlich gesichert werden sollen.

**Schritt 3:** Klicken Sie auf **Dropbox-Zugang zulassen**

> Tipp: Wenn Sie in der Zukunft keine Datensicherungen mehr auf Dropbox sichern wollen, dann demarkieren Sie das Feld "Datensicherungen zur Dropbox senden".

### Abbildung 2: "Dropbox-Zugang zulassen"

![Backup Manager]({{docs_base_url}}/assets/old_images/erpnext/backup-manager.png)

Sie müssen sich mit Ihrer ID und Ihrem Passwort an Ihrem Dropbox-Konto anmelden.

![Dropbox-Zugriff]({{docs_base_url}}/assets/old_images/erpnext/dropbox-access.png)

## Für OpenSource-Nutzer

Voreinstellungen:

pip install dropbox

pip install google-api-python-client

### Erstellen Sie in der Dropbox eine Anwendung

Legen Sie zuerst ein Dropbox-Konto an und erstellen Sie dann eine neue Anwendung (https://www.dropbox.com/developers/apps). Wenn Sie das Konto erfolgreich angelegt haben, erhalten Sie app_key, app_secret und access_type. Bearbeiten Sie nun site_config.json Ihrer Seite (/frappe-bench/sites/your-site/) und fügen Sie die folgenden Zeilen hinzu: 

* "dropbox_access_key": "app_key", und
* "dropbox_secret_key": "app_secret"

Dann können Sie zum Modul "Einbindungen" gehen und "Dropbox-Zugang zulassen".

> Hinweis: Bitte stellen Sie sicher, dass Ihr Browser Popups zulässt.

{next}
