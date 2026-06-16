import { useAtom } from 'jotai'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ModalContentFallback } from '@/components/ui/modal-content-fallback'
import _ from '@/lib/translate'
import { lazy, Suspense } from 'react'
import { bankRecTransferModalAtom } from './bankRecAtoms'

const TransferModalContent = lazy(() => import('./TransferModalContent'))

const TransferModal = () => {
	const [isOpen, setIsOpen] = useAtom(bankRecTransferModalAtom)

	return (
		<Dialog open={isOpen} onOpenChange={setIsOpen}>
			<DialogContent className='min-w-7xl'>
				<DialogHeader>
					<DialogTitle>{_("Transfer")}</DialogTitle>
					<DialogDescription>
						{_("Record an internal transfer to another bank/credit card/cash account.")}
					</DialogDescription>
				</DialogHeader>
				{isOpen && (
					<Suspense fallback={<ModalContentFallback />}>
						<TransferModalContent />
					</Suspense>
				)}
			</DialogContent>
		</Dialog>
	)
}

export default TransferModal
