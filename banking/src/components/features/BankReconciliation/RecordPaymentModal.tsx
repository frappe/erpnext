import { useAtom } from "jotai"
import { bankRecRecordPaymentModalAtom } from "./bankRecAtoms"
import { Dialog, DialogContent, DialogTitle, DialogDescription, DialogHeader } from "@/components/ui/dialog"
import { ModalContentFallback } from "@/components/ui/modal-content-fallback"
import _ from "@/lib/translate"
import { lazy, Suspense } from "react"

const RecordPaymentModalContent = lazy(() => import('./RecordPaymentModalContent'))

const RecordPaymentModal = () => {
	const [isOpen, setIsOpen] = useAtom(bankRecRecordPaymentModalAtom)

	return (
		<Dialog open={isOpen} onOpenChange={setIsOpen}>
			<DialogContent className='min-w-[95vw]'>
				<DialogHeader>
					<DialogTitle>{_("Record Payment")}</DialogTitle>
					<DialogDescription>
						{_("Record a payment entry against a customer or supplier")}
					</DialogDescription>
				</DialogHeader>
				{isOpen && (
					<Suspense fallback={<ModalContentFallback />}>
						<RecordPaymentModalContent />
					</Suspense>
				)}
			</DialogContent>
		</Dialog>
	)
}

export default RecordPaymentModal
