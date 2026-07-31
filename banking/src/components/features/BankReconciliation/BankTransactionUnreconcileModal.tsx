import {
	AlertDialog,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { useAtom } from "jotai"
import { Loader2Icon } from "lucide-react"
import { lazy, Suspense } from "react"
import { bankRecUnreconcileModalAtom } from "./bankRecAtoms"
import _ from "@/lib/translate"

const BankTransactionUnreconcileModalBody = lazy(() => import('./BankTransactionUnreconcileModalBody'))

const BankTransactionUnreconcileModalFallback = () => (
	<div className="flex items-center justify-center py-16">
		<Loader2Icon className="size-6 animate-spin text-muted-foreground" />
	</div>
)

const BankTransactionUnreconcileModal = () => {
	const [unreconcileModal, setBankRecUnreconcileModal] = useAtom(bankRecUnreconcileModalAtom)

	const onOpenChange = (v: boolean) => {
		if (!v) {
			setBankRecUnreconcileModal('')
		}
	}

	if (!unreconcileModal) {
		return null
	}

	return (
		<AlertDialog open onOpenChange={onOpenChange}>
			<AlertDialogContent className="min-w-2xl">
				<AlertDialogHeader>
					<AlertDialogTitle>{_("Undo Transaction Reconciliation")}</AlertDialogTitle>
					<AlertDialogDescription>
						{_("Are you sure you want to unreconcile this transaction?")}
					</AlertDialogDescription>
				</AlertDialogHeader>
				<Suspense fallback={<BankTransactionUnreconcileModalFallback />}>
					<BankTransactionUnreconcileModalBody />
				</Suspense>
			</AlertDialogContent>
		</AlertDialog>
	)
}

export default BankTransactionUnreconcileModal
