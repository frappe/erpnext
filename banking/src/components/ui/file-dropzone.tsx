import _ from '@/lib/translate'
import { Dispatch, SetStateAction, useCallback } from 'react'
import { Accept, useDropzone } from 'react-dropzone'
import { cn } from '@/lib/utils'
import { formatBytes, getFileExtension } from '@/lib/file'
import { Button } from './button'
import { Trash2Icon } from 'lucide-react'

type Props = {
    files: File[],
    setFiles?: Dispatch<SetStateAction<File[]>>
    accept?: Accept,
    multiple?: boolean
    onDrop?: (acceptedFiles: File[]) => void,
    onUpdate?: VoidFunction
    className?: string
}

export const FileDropzone = ({ files, setFiles, accept, multiple = true, onDrop, className, onUpdate }: Props) => {

    const onFileDrop = useCallback((acceptedFiles: File[]) => {
        // Do something with the files
        if (multiple) {
            setFiles?.((prev) => [...prev, ...acceptedFiles])
        } else {
            setFiles?.(acceptedFiles)
        }
        onDrop?.(acceptedFiles)
        onUpdate?.()

    }, [setFiles, onDrop, multiple, onUpdate])
    const { getRootProps, getInputProps } = useDropzone({ onDrop: onFileDrop, accept, multiple })
    return (
        <div {...getRootProps()} className={cn('border border-border border-dashed p-4 rounded-sm bg-muted/20', className)}>
            <input {...getInputProps()} />
            {files.length === 0 ? <p className='text-sm text-muted-foreground text-center h-8 flex items-center justify-center'>{multiple ? _("Drop some files here, or click to select files") : _("Drop a file here, or click to select a file")}</p> : null}
            <div className='flex flex-col gap-4'>
                {files.map(f => <div key={f.name} className='flex justify-between items-center'>
                    <div className='flex items-center gap-2'>
                        <FileTypeIcon fileType={getFileExtension(f.name)} size='sm' />
                        <div className='flex flex-col gap-0.5'>
                            <span className='text-gray-800 text-sm'>{f.name}</span>
                            <span className='text-muted-foreground text-xs'>{formatBytes(f.size)}</span>
                        </div>
                    </div>
                    <Button type='button' variant='ghost' size='icon'
                        className='text-muted-foreground hover:text-gray-900 hover:bg-transparent'
                        onClick={(e) => {
                            e.stopPropagation()
                            setFiles?.(files.filter(file => file.name !== f.name))
                            onUpdate?.()
                        }}>
                        <Trash2Icon className='w-4 h-4' />
                    </Button>
                </div>)}
            </div>
        </div>
    )
}

interface FileTypeIconProps {
    fileType: string
    size?: 'sm' | 'md' | 'lg' | 'xl'
    className?: string
    showBackground?: boolean
}

const sizeClasses = {
    sm: 'h-8 w-8',
    md: 'h-10 w-10',
    lg: 'h-12 w-12',
    xl: 'h-16 w-16'
}

const iconSizeClasses = {
    sm: 'h-5 w-5',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
    xl: 'h-10 w-10'
}

// Special sizing for PowerPoint icon due to different viewBox
const pptIconSizeClasses = {
    sm: 'h-3.5 w-3.5',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
    xl: 'h-6 w-6'
}

export const FileTypeIcon = ({
    fileType,
    size = 'md',
    className,
    showBackground = true
}: FileTypeIconProps) => {


    const containerClass = cn(sizeClasses[size], className)

    const RenderIcon = ({ className }: { className?: string }) => {
        switch (fileType.toLowerCase()) {
            case 'pdf':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" className={cn("text-white", iconSizeClasses[size], className)}>
                        <path d="M7 22.9c.1-.6.5-1 .9-1.4.5-.5 1.1-.8 1.8-1.2.7-.4 1.4-.7 2.1-1 .1 0 .2-.1.2-.2.6-1.2 1.2-2.4 1.7-3.6.3-.7.5-1.4.8-2.1v-.1c-.3-.7-.6-1.5-.7-2.3-.2-.8-.2-1.6-.1-2.4.1-.5.4-.9.8-1.3.1-.1.3-.1.5-.1h.8c.2 0 .4.1.5.3.3.2.5.5.7.8.2.4.2.8.3 1.2 0 1.2-.2 2.3-.4 3.4-.1.4-.2.7-.3 1.1v.1c.6 1.1 1.4 2.1 2.2 3 .1.1.1.1.3.1 1.1-.2 2.2-.2 3.2-.2.6 0 1.3.1 1.9.4.3.2.6.4.8.7.1.2.2.4.2.6v.7c0 .2-.1.4-.3.5-.2.2-.4.5-.8.5-.2 0-.5.1-.7.1-1.6.1-2.9-.4-4.2-1.3-.2-.2-.5-.4-.7-.6-.1 0-.1-.1-.2-.1-.6.1-1.2.2-1.8.4-.8.2-1.6.5-2.4.7-.1 0-.1.1-.2.1-.5.9-1.1 1.8-1.7 2.6-.5.6-1.1 1.2-1.7 1.7-.3.2-.7.4-1.1.5h-.8c-.2 0-.3 0-.5-.1-.5-.2-.9-.6-1-1.1-.1 0-.1-.2-.1-.4zm8.8-7c-.3.8-.7 1.6-1 2.4l2.4-.6c-.5-.6-1-1.3-1.4-1.8zm4.3 2.6c.6.4 1.3.7 2 .9.3.1.5 0 .7-.1.2-.1.3-.4.1-.5 0-.1-.1-.1-.2-.1-.2-.1-.5-.1-.8-.2-.6-.1-1.2-.1-1.8 0zm-9.4 2.8s-.1 0 0 0c-.6.3-1.2.7-1.7 1.1-.3.2-.5.5-.7.8v.2c.1.1.1.1.2.1.3-.2.5-.4.7-.5.6-.5 1-1.1 1.5-1.7zM15 11.2c.1 0 .1 0 0 0 .2-.6.3-1.2.3-1.7 0-.3 0-.6-.1-.9 0-.1-.1-.1-.2-.1s-.1.1-.2.1c-.2.3-.2.6-.2 1 0 .3 0 .5.1.8.2.2.2.5.3.8z" fill="currentColor" />
                    </svg>
                )
            case 'doc':
            case 'docx':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" className={cn("text-white", iconSizeClasses[size], className)}>
                        <path d="M26 11.4V8.8c0-.4-.3-.8-.8-.8h-7.3V6.2h-1.4c-.2 0-.3.1-.5.1-.7.1-1.4.3-2.1.4-.7.1-1.4.2-2 .4-.7.1-1.4.2-2.2.4-.8.1-1.5.2-2.2.3-.5.1-1 .2-1.4.2H6v15.9c.8.1 1.6.3 2.4.4.8.1 1.7.3 2.5.4.8.1 1.6.3 2.4.4.8.1 1.7.3 2.5.5.3.1.7.1 1 .1h.9V24c0-.1 0-.1.1-.1h7.3c.1 0 .3 0 .4-.1.2 0 .3-.1.3-.3 0-.2.1-.3.1-.5V11.4c.1.1.1.1.1 0zm-11 1.5l-.9 3.9c-.2.7-.3 1.4-.5 2.2 0 .1-.1.1-.1.1-.2.1-.4 0-.6 0h-.6c-.1 0-.1 0-.1-.1-.1-.6-.3-1.3-.4-1.9-.2-.8-.3-1.6-.5-2.4 0 .2-.1.4-.1.6l-.6 3c0 .2-.1.5-.1.7 0 .1 0 .1-.1.1-.4 0-.8-.1-1.2-.1-.1 0-.1 0-.1-.1-.3-1.6-.6-3.2-1-4.9-.1-.3-.1-.7-.2-1v-.1h1.2c.2 1.4.5 2.8.7 4.3 0-.2.1-.4.1-.6.3-1.2.5-2.5.8-3.7 0-.1 0-.1.1-.1h1c.2 0 .2 0 .3.2.3 1.4.6 2.8.9 4.3v.1c.1-.8.3-1.6.4-2.4.1-.7.3-1.5.4-2.2 0 0 0-.1.1-.1.4 0 .8 0 1.3-.1h.1c-.2 0-.3.2-.3.3zm10.3-4.1s0 .1 0 0v14.5h-7.5v-1.8h5.9v-.9H18c-.1 0-.1 0-.1-.1v-.9c0-.1 0-.1.1-.1h5.8v-.9h-5.9v-1.1h5.8v-.9h-5.9v-1h5.8c.1 0 .1 0 .1-.1v-.7c0-.1 0-.1-.1-.1H18c-.1 0-.1 0-.1-.1v-1h5.9v-.9h-5.7c-.1 0-.1 0-.1-.1v-.9c0-.1 0-.1.1-.1h5.7v-.9h-5.9v-1.2h5.8c.1 0 .1 0 .1-.1v-.7c0-.1 0-.1-.1-.1h-5.9V9c0-.1 0-.1.1-.1h7.3c.1-.2.1-.2.1-.1z" fill="currentColor" />
                    </svg>
                )
            case 'xls':
            case 'xlsx':
            case 'csv':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" className={cn("text-white", iconSizeClasses[size], className)}>
                        <path d="M26 9.3v13.6c0 .1-.1.2-.1.3-.2.3-.5.5-.8.5h-7.7v2c-.3-.1-.7-.1-1-.2-.7-.1-1.5-.3-2.2-.4-.8-.1-1.6-.3-2.4-.4-.8-.1-1.6-.3-2.4-.4-.7-.1-1.5-.3-2.2-.4-.4-.1-.7-.1-1.1-.2V9c.1 0 .3-.1.4-.1.7-.5 1.5-.7 2.3-.8.7-.1 1.4-.3 2-.4.6-.1 1.3-.2 1.9-.4.7-.1 1.5-.3 2.2-.4.8-.1 1.5-.3 2.3-.4h.1v1.9h7.8c.4 0 .8.3.9.7v.2zm-.8-.1h-7.9v1.2H20v1.7h-2.7v.6H20v1.7h-2.7v.6H20v1.7h-2.7v.7h2.8v1.7h-2.8v.6H20v1.7h-2.7v1.2h7.9V9.2zM14.7 20.7s0-.1-.1-.1c-.7-1.4-1.5-2.8-2.2-4.2v-.2c.7-1.4 1.4-2.7 2.2-4.1V12h-.1c-.2 0-.5 0-.7.1-.3 0-.6 0-1 .1-.1 0-.1 0-.1.1-.3.6-.5 1.1-.8 1.7-.2.5-.4.9-.6 1.4-.1-.2-.1-.5-.2-.7-.3-.7-.6-1.5-.9-2.2-.1-.2-.1-.2-.3-.2-.4 0-.8.1-1.2.1h-.4v.1c.1.2.2.5.3.7l1.5 3v.1c-.6 1.2-1.3 2.4-1.9 3.6 0 .1-.1.1-.1.2h.6c.4 0 .7.1 1.1.1.1 0 .1 0 .1-.1.3-.6.6-1.2.9-1.9.1-.3.3-.6.4-.9 0-.1 0-.2.1-.3v.1c.1.2.1.4.2.5.4.8.7 1.6 1.1 2.5.1.1.1.2.3.2.5 0 1 .1 1.5.1.1.3.2.3.3.3z" fill="currentColor" />
                        <path d="M23.9 10.4v1.7h-3.1v-1.7h3.1zm-3.1 11.2v-1.7h3.1v1.7h-3.1zm0-4.7v-1.7h3.1v1.7h-3.1zm3.1-4.1v1.7h-3.1v-1.7h3.1zm0 4.8v1.7h-3.1v-1.7h3.1z" fill="currentColor" />
                    </svg>
                )
            case 'ppt':
            case 'pptx':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122.88 116.03" className={cn("text-white", pptIconSizeClasses[size], className)}>
                        <g>
                            <path d="M0.38,12.11L69.16,0.09L69.69,0v0.54v114.96v0.53l-0.53-0.09L0.38,104.63L0,104.57v-0.38V12.55v-0.38L0.38,12.11 L0.38,12.11z M76.29,17.01h43.79c0.77,0,1.47,0.32,1.98,0.82c0.51,0.51,0.82,1.21,0.82,1.98v76.75c0,0.78-0.32,1.5-0.84,2.01 s-1.23,0.84-2.01,0.84H76.29h-0.45v-0.45v-9.16v-0.45h0.45h33.62v-6.15H76.29h-0.45v-0.45v-7.17V75.1h0.45h33.62v-6.15H76.29h-0.45 v-0.45v-8.49v-0.88l0.71,0.51c1.32,0.94,2.79,1.68,4.36,2.18c1.52,0.48,3.14,0.74,4.82,0.74c4.38,0,8.34-1.78,11.21-4.64 c2.82-2.82,4.59-6.7,4.64-11H85.83h-0.45v-0.45V30.86c-1.56,0.03-3.06,0.29-4.47,0.74c-1.57,0.5-3.04,1.24-4.36,2.18l-0.71,0.51 v-0.88V17.46v-0.45H76.29L76.29,17.01z M99.26,32.75c-2.76-2.77-6.54-4.52-10.73-4.65v15.48h15.36 C103.79,39.35,102.04,35.53,99.26,32.75L99.26,32.75z M30.91,80.41V63.97v-0.45h0.45h6.22c2.41,0,4.56-0.35,6.45-1.05 c1.87-0.7,3.49-1.75,4.86-3.15c1.37-1.4,2.39-3.04,3.08-4.91c0.69-1.88,1.03-4,1.03-6.37c0-1.61-0.16-3.12-0.48-4.55 c-0.32-1.42-0.79-2.76-1.43-4.01c-0.63-1.25-1.4-2.36-2.29-3.32c-0.89-0.96-1.91-1.78-3.06-2.45c-2.31-1.35-4.97-2.03-7.98-2.03 H22.07v48.75H30.91L30.91,80.41z M37.76,55.2h-6.39h-0.45v-0.45V40.43v-0.45h0.45h6.51l0.01,0c0.95,0.01,1.81,0.21,2.57,0.59 c0.76,0.38,1.41,0.95,1.96,1.71h0c0.54,0.74,0.95,1.6,1.21,2.58c0.27,0.97,0.4,2.05,0.4,3.24c0,1.1-0.13,2.08-0.39,2.94h0 c-0.27,0.88-0.67,1.63-1.21,2.26c-0.54,0.63-1.21,1.11-2,1.43C39.65,55.05,38.76,55.2,37.76,55.2L37.76,55.2z" fill="currentColor" />
                        </g>
                    </svg>
                )
            case 'video':
            case 'mp4':
            case 'mov':
            case 'mkv':
            case 'avi':
            case 'webm':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" className={cn("text-white", iconSizeClasses[size], className)}>
                        <path d="M16 4c-6.6 0-12 5.4-12 12s5.4 12 12 12 12-5.4 12-12S22.6 4 16 4zm-2 16.5V9.5l8 5.5-8 5.5z" fill="currentColor" />
                    </svg>
                )
            case 'audio':
            case 'mp3':
            case 'wav':
            case 'ogg':
            case 'flac':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" className={cn("text-white", iconSizeClasses[size], className)}>
                        <path d="M16 4c-6.6 0-12 5.4-12 12s5.4 12 12 12 12-5.4 12-12S22.6 4 16 4zm-2 16.5V9.5l8 5.5-8 5.5z" fill="currentColor" />
                    </svg>
                )
            case 'image':
            case 'jpg':
            case 'jpeg':
            case 'png':
            case 'gif':
            case 'webp':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" className={cn("text-white", iconSizeClasses[size], className)}>
                        <path d="M26 4H6c-1.1 0-2 .9-2 2v20c0 1.1.9 2 2 2h20c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM6 26V6h20v20H6z" fill="currentColor" />
                        <path d="M10 12c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm12 8H10l4-6 3 4 2-3 7 5z" fill="currentColor" />
                    </svg>
                )
            case 'zip':
            case 'rar':
            case '7z':
            case 'tar':
            case 'gz':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" className={cn("text-white", iconSizeClasses[size], className)}>
                        <path d="M26 4H6c-1.1 0-2 .9-2 2v20c0 1.1.9 2 2 2h20c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM6 26V6h20v20H6z" fill="currentColor" />
                        <path d="M10 8h12v2H10V8zm0 4h12v2H10v-2zm0 4h12v2H10v-2z" fill="currentColor" />
                    </svg>
                )
            default:
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className={cn("text-white", iconSizeClasses[size], className)}>
                        <path d="M18 22a2 2 0 0 0 2-2V8l-6-6H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12zM13 4l5 5h-5V4zM7 8h3v2H7V8zm0 4h10v2H7v-2zm0 4h10v2H7v-2z" fill="currentColor" />
                    </svg>
                )
        }
    }

    const getBackgroundColor = () => {
        switch (fileType.toLowerCase()) {
            case 'pdf':
                return 'bg-red-700'
            case 'doc':
            case 'docx':
                return 'bg-[#1A5CBD]'
            case 'xls':
            case 'xlsx':
            case 'csv':
                return 'bg-green-700'
            case 'ppt':
            case 'pptx':
                return 'bg-[#ED6C47]'
            case 'video':
            case 'mp4':
            case 'mov':
            case 'mkv':
            case 'avi':
            case 'webm':
                return 'bg-purple-600'
            case 'audio':
            case 'mp3':
            case 'wav':
            case 'ogg':
            case 'flac':
                return 'bg-purple-600'
            case 'image':
            case 'jpg':
            case 'jpeg':
            case 'png':
            case 'gif':
            case 'webp':
                return 'bg-blue-600'
            case 'zip':
            case 'rar':
            case '7z':
            case 'tar':
            case 'gz':
                return 'bg-yellow-600'
            default:
                return 'bg-gray-500'
        }
    }

    const getTextColor = () => {
        switch (fileType.toLowerCase()) {
            case 'pdf':
                return 'text-red-700'
            case 'doc':
            case 'docx':
                return 'text-[#1A5CBD]'
            case 'xls':
            case 'xlsx':
            case 'csv':
                return 'text-green-700'
            case 'ppt':
            case 'pptx':
                return 'text-[#ED6C47]'
            case 'video':
            case 'mp4':
            case 'mov':
            case 'mkv':
            case 'avi':
            case 'webm':
                return 'text-purple-600'
            case 'audio':
            case 'mp3':
            case 'wav':
            case 'ogg':
            case 'flac':
                return 'text-purple-600'
            case 'image':
            case 'jpg':
            case 'jpeg':
            case 'png':
            case 'gif':
            case 'webp':
                return 'text-blue-600'
            case 'zip':
            case 'rar':
            case '7z':
            case 'tar':
            case 'gz':
                return 'text-yellow-600'
            default:
                return 'text-gray-50'
        }
    }

    if (showBackground) {
        return (
            <div className={cn("rounded-md flex items-center justify-center", getBackgroundColor(), containerClass)}>
                <RenderIcon />
            </div>
        )
    }

    return (
        <div className={cn("flex items-center justify-center")}>
            <RenderIcon className={getTextColor()} />
        </div>
    )
}