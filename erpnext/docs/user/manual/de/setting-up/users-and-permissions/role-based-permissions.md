# Rollenbasierte Berechtigungen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

ERPNext arbeitet mit einem rollenbasierten Berechtigungssystem. Das heißt, dass Sie Benutzern Rollen zuordnen können und Rollen Berechtigungen erteilen können. Die Struktur der Berechtigungen erlaubt es Ihnen weiterhin verschiedene Berechtigungsregeln für unterschiedliche Felder zu definieren, wobei das **Konzept der Berechtigungsebenen** für Felder verwendet wird. Wenn einem Kunden einmal Rollen zugeordnet worden sind, haben Sie darüber die Möglichkeit, den Zugriff eines Benutzers auf bestimmte Dokumente zu beschränken.

Wenn Sie das tun wollen, gehen Sie zu:

> Einstellungen > Berechtigungen > Rollenberechtigungen-Manager

<img alt="Berechtigungen für Lesen, Schreiben, Erstellen, Übertragen und Abändern mit Hilfe des Rollenberechtigungen-Managers einstellen" class="screenshot" src="{{docs_base_url}}/assets/img/users-and-permissions/setting-up-permissions-leave-application.png">

Berechtigungen werden angewandt auf einer Kombination von:

* **Rollen:** Wie wir schon angesprochen haben, werden Benutzern Rollen zugeordnet, und auf diese wiederum werden Berechtigungsregeln angewandt.

_Beispiele für Rollen sind der "Kontenmanager", der "Mitarbeiter" und der "Nutzer Personalabteilung"._

* **Dokumenttypen:** Jeder Dokumententyp, jede Vorlage und jede Transaktion hat eine eigene Liste von rollenbasierten Berechtigungen.

_Beispiele für Dokumententypen sind: "Ausgangsrechnung", "Urlaubsantrag", "Lagerbuchung", usw._

* **Berechtigungs"ebenen":** Sie können in jedem Dokument Felder nach "Ebenen" gruppieren. Jede Gruppierung von Feldern wird mit einer eindeutigen Nummer (0, 1, 2, 3, usw.) versehen. Auf jede Feldgruppierung kann ein eigenständiger Satz von Berechtigungsregeln angewandt werden. Standardmäßig haben alle Felder die Ebene 0.

_Die Berechtigungsebene verbindet die Gruppierung der Felder der Ebene X mit einer Berechtigungsregel der Ebene X._

* **Dokumentenphasen:** Berechtigungen werden zu jeder Phase eines Dokumentes angewandt, wie z. B. Erstellung, Speicherung, Übetragung, Stornierung und Änderung. Eine Rolle kann die Berechtigung haben zu drucken, per E-Mail zu versenden, Daten zu importieren oder zu exportieren, auf Berichte zuzugreifen oder Benutzerberechtigungen zu definieren.

* **Benutzerberechtigungen anwenden:** Dieser Schalter entscheidet, ob für eine Rolle in einer bestimmten Dokumentenphase Benutzerberechtigungen gültig sind.

Wenn dieser Punkt aktiviert ist, kann ein Benutzer mit dieser Rolle nur auf bestimmte Dokumente dieses Dokumententyps zugreifen. Dieser spezielle Dokumentenzugriff wird über die Liste der Benutzerberechtigungen definiert. Zusätzlich werden Benutzerberechtigungen, die für andere Dokumententypen definiert wurden, ebenfalls angewandt, wenn Sie mit dem aktuellen Dokumententyp über Verknüpfungsfelder verbunden sind.

Um Benutzerberechtigungen zu setzen, gehen Sie zu:

> Einstellungen > Berechtigungen > [Benutzerrechte-Manager]({{docs_base_url}}/user/manual/de/setting-up/users-and-permissions/user-permissions.html)



---

**Um eine neue Regel hinzuzufügen**, klicken Sie auf die Schaltfläche "Benutzereinschränkung hinzufügen". Es öffnet sich ein Popup-Fenster und bittet Sie eine Rolle und eine Berechtigungsebene auszuwählen. Wenn Sie diese Auswahl treffen und auf "Hinzufügen" klicken, wird in der Tabelle der Regeln eine neue Zeile eingefügt.

---

Der Urlaubsantrag ist ein gutes **Beispiel**, welches alle Bereiche des Berechtigungssystems abdeckt.

<img class="screenshot" alt="Der Urlaubsantrag sollte von einem Mitarbeiter erstellt werden, und von einem Urlaubsgenehmiger oder Mitarbeiter des Personalwesens genehmigt werden." src="{{docs_base_url}}/assets/img/users-and-permissions/setting-up-permissions-leave-application-form.png">

1\. **Er sollte von einem "Mitarbeiter" erstellt werden.** Aus diesem Grund sollte die Rolle "Mitarbeiter" Berechtigungen zum Lesen, Schreiben und Erstellen haben.

<img class="screenshot" alt="Einem Mitarbeiter Lese-, Schreib- und Erstellrechte für einen Urlaubsantrag geben."  src="{{docs_base_url}}/assets/img/users-and-permissions/setting-up-permissions-employee-role.png">

2\. **Ein Mitarbeiter sollte nur auf seine/Ihre eigenen Urlaubsanträge zugreifen können.** Daher sollte der Punkt "Benutzerberechtigungen anwenden" für die Rolle "Mitarbeiter" aktiviert sein und es sollte ein Datensatz "Benutzerberechtigung" für jede Kombination von Benutzer und Mitarbeiter erstellt werden. (Dieser Aufwand reduziert sich für den Dokumententyp, indem über das Programm Datensätze für Benutzerberechtigungen erstellt werden.)

<img class="screenshot" alt="Den Zugriff für einen Benutzer mit der Rolle Mitarbeiter auf Urlaubsanträge über den Benutzerberechtigungen-Manager einschränken." src="{{docs_base_url}}/assets/old_images/erpnext/setting-up-permissions-employee-user-permissions.png">

3\. **Der Personalmanager sollte alle Urlaubsanträge sehen können.** Erstellen Sie für den Personalmanager eine Berechtigungsregel auf der Ebene 0 mit Lese-Rechten. Die Option "Benutzerberechtigungen anwenden" sollte deaktiviert sein.

<img class="screenshot" alt="Einem Personalmanager Rechte für Übertragen und Stornieren für Urlaubsanträge geben. 'Benutzerberechtigungen anwenden' ist demarkiert um vollen Zugriff zu ermöglichen." src="{{docs_base_url}}/assets/img/users-and-permissions/setting-up-permissions-hr-manager-role.png">

4\. **Der Urlaubsgenehmiger sollte die ihn betreffenden Urlaubsanträge lesen und aktualisieren können.** Der Urlaubsgenehmiger erhält Lese- und Schreibzugriff auf Ebene 0, und die Option "Benutzerberechtigungen anwenden" wird aktiviert. Zutreffende Mitarbeiter-Dokumente sollten in den Benutzerberechtigungen des Urlaubsgenehmigers aufgelistet sein. (Dieser Aufwand reduziert sich für Urlaubsgenehmiger, die in Mitarbeiterdokumenten aufgeführt werden, indem über das Programm Datensätze für Benutzerberechtigungen erstellt werden.)

<img class="screenshot" alt="Rechte für Schreiben, Lesen und Übertragen an einen Urlaubsgenehmiger zum Genehmigen von Urlauben geben. 'Benutzerberechtigungen anwenden' ist markiert, um den Zugriff basierend auf dem Mitarbeitertyp einzuschränken." src="{{docs_base_url}}/assets/img/users-and-permissions/setting-up-permissions-leave-approver-role.png">

5\. **Ein Urlaubsantrag sollte nur von einem Mitarbeiter der Personalverwaltung oder einem Urlaubsgenehmiger bestätigt oder abgelehnt werden können.** Das Statusfeld des Urlaubsantrags wird auf Ebene 1 gesetzt. Mitarbeiter der Personalverwaltung und Urlaubsgenehmiger bekommen Lese- und Schreibrechte für Ebene 1, während allen anderen Leserechte für Ebene 1 gegeben werden.

<img class="screenshot" alt="Leserechte auf einen Satz von Feldern auf bestimmte Rollen beschränken." src="{{docs_base_url}}/assets/old_images/erpnext/setting-up-permissions-level-1.png">

6\. **Der Mitarbeiter der Personalverwaltung sollte die Möglichkeit haben Urlaubsanträge an seine Untergebenen zu delegieren.** Er erhält die Erlaubis Benutzerberechtigungen einzustellen. Ein Nutzer mit der Rolle "Benutzer Personalverwaltung" wäre dann also in der Lage Benutzer-Berechtigungen und Urlaubsanträge für andere Benutzer zu definieren.

<img class="screenshot" alt="Es dem Benutzer der Personalverwaltung ermöglichen, den Zugriff auf Urlaubsanträge zu delegieren, indem er 'Benutzerberechtigungen einstellen' markiert. Dies erlaubt es dem Benutzer der Personalverwaltung auf den Benutzerberechtigungen-Manager für 'Urlaubsanträge' zuzugreifen" src="{{docs_base_url}}/assets/img/users-and-permissions/setting-up-permissions-hr-user-role.png">

{next}
