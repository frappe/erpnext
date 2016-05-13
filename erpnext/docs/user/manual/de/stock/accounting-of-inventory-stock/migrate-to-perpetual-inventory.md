# Zur Ständigen Inventur wechseln
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Bestehende Benutzer müssen sich an folgende Schritte halten um das neue System der Ständigen Inventur zu aktivieren. Da die Ständige Inventur immer auf einer Synchronisation zwischen Lager und Kontostand aufbaut, ist es nicht möglich diese Option in einer bestehenden Lagereinstellung zu übernehmen. Sie müssen einen komplett neuen Satz von Lagern erstellen, jedes davon verbunden mit dem betreffenden Konto.

Schritte:


  * Heben Sie die Salden der Konten, die Sie zur Pflege des verfügbaren Lagerwertes verwenden, (Warenbestände/Anlagevermögen) durch eine Journalbuchung auf.

  * Da bereits angelegte Lager mit Lagertransaktionen verbunden sind, es aber keine verknüpften Buchungssätze gibt, können diese Lager nicht in einer ständigen Inventur genutzt werden. Sie müssen für zukünftige Lagertransaktionen neue Lager anlegen, die dann mit den zutreffenden Konten verknüpft sind. Wählen Sie bei der Erstellung neuer Lager eine Artikelgruppe unter der das Unterkonto für das Lager erstellt wird.

  * Erstellen Sie folgende Standardkonten für jede Firma: 

    * Ware erhalten aber noch nicht abgerechnet
    * Lagerabgleichskonto
    * Aufwendungen in Bewertung enthalten
    * Kostenstelle
    
  * Aktivieren Sie die Ständige Inventur

> Einstellungen > Rechnungswesen > Konteneinstellungen > Eine  Buchung für jede Lagerbewegung erstellen

![Aktivierung]({{docs_base_url}}/assets/old_images/erpnext/accounting-for-stock-1.png)  

* Erstellen Sie Lagerbuchungen (Materialübertrag) um verfügbare Lagerbestände von einem existierenden Lager auf ein neues Lager zu übertragen. Sobald im neuen Lager der Lagerbestand verfügbar wird, sollten Sie für zukünftige Transaktionen nur noch das neue Lager verwenden.

Das System wird für bereits existierende Lagertransaktionen keine Buchungssätze erstellen, wenn sie vor der Aktivierung der Ständigen Inventur übertragen wurden, da die alten Lager nicht mit Konten verknüpft werden. Wenn Sie eine neue Transaktion mit einem alten Lager erstellen oder eine existierende Transaktion ändern, gibt es keine korrespondierenden Buchungssätze. Sie müssen Lager und Kontostände manuell über das Journal synchronisieren.

> Anmerkung: Wenn Sie bereits das alte System der Ständigen Inventur nutzen, wird dieses automatisch deaktiviert. Sie müssen den Schritten oben folgen um es wieder zu aktivieren.
