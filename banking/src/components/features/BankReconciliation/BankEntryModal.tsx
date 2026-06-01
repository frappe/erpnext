import { useAtom } from "jotai"
import { bankRecRecordJournalEntryModalAtom } from "./bankRecAtoms"
import { Dialog, DialogContent, DialogTitle, DialogDescription, DialogHeader } from "@/components/ui/dialog"
import { ModalContentFallback } from "@/components/ui/modal-content-fallback"
import _ from "@/lib/translate"
import { lazy, Suspense } from "react"

const RecordBankEntryModalContent = lazy(() => import('./BankEntryModalContent'))

const BankEntryModal = () => {
	const [isOpen, setIsOpen] = useAtom(bankRecRecordJournalEntryModalAtom)

	return (
		<Dialog open={isOpen} onOpenChange={setIsOpen}>
			<DialogContent className='min-w-[95vw]'>
				<DialogHeader>
					<DialogTitle>{_("Bank Entry")}</DialogTitle>
					<DialogDescription>
						{_("Record a journal entry for expenses, income or split transactions.")}
					</DialogDescription>
				</DialogHeader>
				{isOpen && (
					<Suspense fallback={<ModalContentFallback />}>
						<RecordBankEntryModalContent />
					</Suspense>
				)}
			</DialogContent>
		</Dialog>
	)
}

export default BankEntryModal
