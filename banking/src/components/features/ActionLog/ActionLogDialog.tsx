import { Button } from '@/components/ui/button'
import { DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import _ from '@/lib/translate'
import { Loader2Icon } from 'lucide-react'
import { lazy, Suspense } from 'react'

const ActionLogDialogBody = lazy(() => import('./ActionLogDialogBody'))

const ActionLogDialogFallback = () => (
	<div className="flex flex-1 items-center justify-center min-h-[40vh]">
		<Loader2Icon className="size-6 animate-spin text-muted-foreground" />
	</div>
)

const ActionLogDialog = ({ onClose }: { onClose: () => void }) => {
	return (
		<DialogContent className='min-w-[90vw]'>
			<DialogHeader>
				<DialogTitle>{_("Reconciliation History")}</DialogTitle>
				<DialogDescription>{_("View all reconciliation actions taken in this session.")}</DialogDescription>
			</DialogHeader>
			<Suspense fallback={<ActionLogDialogFallback />}>
				<ActionLogDialogBody />
			</Suspense>
			<DialogFooter>
				<DialogClose asChild>
					<Button variant={'outline'} size='md' onClick={onClose}>{_("Close")}</Button>
				</DialogClose>
			</DialogFooter>
		</DialogContent>
	)
}

export default ActionLogDialog
