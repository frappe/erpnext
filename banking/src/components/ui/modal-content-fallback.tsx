import { Loader2Icon } from 'lucide-react'

export const ModalContentFallback = () => (
	<div className="flex items-center justify-center py-16">
		<Loader2Icon className="size-6 animate-spin text-muted-foreground" />
	</div>
)
