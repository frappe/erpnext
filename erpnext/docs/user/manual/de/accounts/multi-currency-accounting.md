# Buchungen in unterschiedlichen Währungen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

In ERPNext können Sie Buchungen in unterschiedlichen Währungen erstellen. Beispiel: Wenn Sie ein Bankkonto in einer Fremdwährung haben, dann können Sie Transaktionen in dieser Währung durchführen und das System zeigt Ihnen den Kontostand der Bank nur in dieser speziellen Währung an.

### Einrichtung

Um mit Buchungen in unterschiedlichen Währungen zu beginnen, müssen Sie die Buchungswährung im Datensatz des Kontos einstellen. Sie können bei der Anlage eine Währung aus dem Kontenplan auswählen.

<img class="screenshot" alt="Währung über den Kontenplan einstellen"  	src="/docs/assets/img/accounts/multi-currency/chart-of-accounts.png">

Sie können die Währung auch zuordnen oder bearbeiten, indem Sie den jeweiligen Datensatz für bereits angelegte Konten öffnen. 

<img class="screenshot" alt="Kontenwährung anpassen"  	src="/docs/assets/img/accounts/multi-currency/account.png">

Für Kunden/Lieferanten können Sie die Buchungswährung auch im Gruppendatensatz einstellen. Wenn sich die Buchungswährung der Gruppe von der Firmenwährung unterscheidet, müssen Sie die Standardkonten für Forderungen und Verbindlichkeiten auf diese Währung einstellen.

<img class="screenshot" alt="Währung des Kundenkontos"  	src="/docs/assets/img/accounts/multi-currency/customer.png">

Wenn Sie die Buchungswährung für einen Artikel oder eine Gruppe eingestellt haben, können Sie Buchungen zu ihnen erstellen. Wenn sich die Buchungswährung der Gruppe von der Firmenwährung unterscheidet, dann beschränkt das System beim Erstellen von Transaktionen für diese Gruppe Buchungen auf diese Währung. Wenn die Buchungswährung die selbe wie die Firmenwährung ist, können Sie Transaktionen für diese Guppe in jeder beliebigen Währung erstellen. Aber die Hauptbuch-Buchungen werden immer in der Buchungswährung der Gruppe vorliegen. In jedem Fall ist die Wärung des Verbindlichkeitenkontos immer gleich der Buchungswährung der Gruppe.

Sie können die Buchungswährung im Datensatz für die Gruppe/das Konto verändern, solange bis Sie Transaktionen für sie erstellen. Nach dem Buchen erlaubt es das System nicht die Buchungswährung für einen Konto- oder Gruppendatensatz zu ändern.

Wenn Sie mehrere Firmen verwalten muss die Buchungswährung der Gruppe für alle Firmen gleich sein.

### Transaktionen

#### Ausgangsrechnung

In einer Ausgangsrechnung muss die Währung der Transaktion gleich der Buchungswährung des Kunden sein, wenn die Buchungswährung des Kunden anders als die Firmenwährung ist. Andernfalls können sie in der Rechnung jede beliebige Währung auswählen. Bei der Auswahl des Kunden zieht das System das Verbindlichkeitenkonto aus dem Kunden/aus der Firma. Die Währung des Verbindlichkeitenkontos muss die selbe sein wie die Buchungswährung des Kunden.

Nun wird im POS der gezahlte Betrag in der Transaktionswährung eingegeben, im Gegensatz zur vorherigen Firmenwährung. Auch der Ausbuchungsbetrag wird in der Transaktionswährung eingegeben.

Der ausstehende Betrag und Anzahlungsbeträge werden immer in der Währung des Kundenkontos kalkuliert und angezeigt.

<img class="screenshot" alt="Offene Ausgangsrechnung"  	src="/docs/assets/img/accounts/multi-currency/sales-invoice.png">

#### Eingangsrechnung

In ähnlicher Art und Weise werden in Eingangsrechnungen Buchungen basierend auf der Buchungswährung des Lieferanten durchgeführt. Der ausstehende Betrag und Anzahlungen werden ebenfalls in der Buchungswährung des Lieferanten angezeigt. Abschreibungsbeträge werden nun in der Transaktionswährung eingegeben.

#### Buchungssatz

In einer Journalbuchung können Sie Transaktionen in unterschiedlichen Währungen erstellen. Es gibt ein Auswahlfeld "Unterschiedliche Währungen" um Buchungen in mehreren Währungen zu aktivieren. Wenn die Option "Unterschiedliche Währungen" ausgewählt wurde, können Sie Konten mit unterschiedlichen Währungen auswählen.

<img class="screenshot" alt="Wechselkurs im Buchungssatz"  	src="/docs/assets/img/accounts/multi-currency/journal-entry-multi-currency.png">

In der Kontenübersicht zeigt das System den Abschnitt Währung an und holt sich die Kontenwährung und den Wechselkurs automatisch, wenn Sie ein Konto mit ausländischer Währung auswählen. Sie können den Wechselkurs später manuell ändern/anpassen.

In einem einzelnen Buchungssatz können Sie nur Konten mit einer alternativen Währung auswählen, abweichend von Konten in der Firmenwährung. Die Beträge für Soll und Haben sollten in der Kontenwährung eingegeben werden, das System berechnet und zeigt dann den Betrag für Soll und Haben automatisch in der Firmenwährung.

<img class="screenshot" alt="Buchungssatz mit verschiedenen Währungen"  	src="/docs/assets/img/accounts/multi-currency/journal-entry-row.png">

#### Beispiel 1: Zahlungsbuchung eines Kunden in alternativer Währung

Nehmen wir an, dass die Standardwährung einer Firma Indische Rupien ist, und die Buchungswährung des Kunden US-Dollar. Der Kunde zahlt den vollen Rechnungsbetrag zu einer offenen Rechnung in Höhe von 100 US-Dollar. Der Wechselkurs (US-Dollar in Indische Rupien) in der Ausgangsrechnung war mit 60 angegeben.

Der Wechselkurs in der Zahlungsbuchung sollte immer der selbe wie auf der Rechnung (60) sein, auch dann, wenn der Wechselkurs am Tag der Zahlung 62 beträgt. Dem Bankkonto wird der Betrag mit einem Wechselkurs von 62 gut geschrieben. Deshalb wird ein Wechelkursgewinn bzw. -verlust basierend auf dem Unterschied im Wechselkurs gebucht.

<img class="screenshot" alt="Zahlungsbuchung"  	src="/docs/assets/img/accounts/multi-currency/payment-entry.png">

#### Beispiel 2: Überweisung zwischen Banken (US-Dollar -> Indische Rupien)

Nehmen wir an, dass die Standardwährung der Firma Indische Rupien ist. Sie haben ein Paypal-Konto in der Währung US-Dollar. Sie erhalten auf das Paypal-Konto Zahlungen und wir gehen davon aus, dass Paypal einmal in der Woche Beträge auf Ihr Bankkonto, mit der Währung Indische Rupien, überweist.

Das Paypal-Konto wird an einem anderen Datum mit einem anderen Wechselkurs belastet, als die Gutschrift auf das Bankkonto erfolgt. Aus diesem Grund gibt es normalerweise einen Wechselkursgewinn oder -verlust zur Überweisungsbuchung. In der Überweisungsbuchung stellt das System den Wechselkurs basierend auf dem durchschnittlichen Wechselkurs für eingehende Zahlungen des Paypal-Kontos ein. Sie müssen den Wechelkursgewinn oder -verlust basierend auf dem durchschnittlichen Wechselkurs und dem Wechselkurs am Überweisungstag berechnen und eingeben.

Nehmen wir an, dass das Paypal-Konto folgende Beträge, die noch nicht auf Ihr anderes Bankkonto überwiesen wurden, in einer Woche als Gutschrift erhalten hat.

<table class="table table-bordered">
	<thead>
		<tr>
			<td>Datum</td>
			<td>Konto</td>
			<td>Soll (USD)</td>
			<td>Wechselkurs</td>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>02.09.2015</td>
			<td>Paypal</td>
			<td>100</td>
			<td>60</td>
		</tr>
		<tr>
			<td>02.09.2015</td>
			<td>Paypal</td>
			<td>100</td>
			<td>61</td>
		</tr>
		<tr>
			<td>02.09.2015</td>
			<td>Paypal</td>
			<td>100</td>
			<td>64</td>
		</tr>
	</tbody>
</table>

Angenommen, der Wechselkurs am Zahlungstag ist 62, dann schaut die Buchung zur Banküberweisung wie folgt aus:

<img class="screenshot" alt="Übertrag zwischen den Banken"  	src="/docs/assets/img/accounts/multi-currency/bank-transfer.png">

### Berichte

#### Hauptbuch

Im Hauptbuch zeigt das System den Betrag einer Gutschrift/Lastschrift in beiden Währungen an, wenn nach Konto gefiltert wurde, und wenn die Kontenwährung unterschiedlich zur Firmenwährung ist.

<img class="screenshot" alt="Bericht zum Hauptbuch"  	src="/docs/assets/img/accounts/multi-currency/general-ledger.png">

#### Forderungs- und Verbindlichkeitenkonten

Im Bericht zu den Konten Forderungen und Verbindlichkeiten zeigt das System alle Beträge in der Währung der Gruppe/in der Kontenwährung an.

<img class="screenshot" alt="Bericht zu den Forderungen"  	src="/docs/assets/img/accounts/multi-currency/accounts-receivable.png">

{next}
