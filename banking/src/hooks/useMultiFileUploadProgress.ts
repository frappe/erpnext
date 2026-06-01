import { useCallback, useRef, useState } from "react"

/** Tracks per-file upload progress (0–1) and exposes their average. */
export function useMultiFileUploadProgress() {
    const [uploadProgress, setUploadProgress] = useState(0)
    const fileProgressesRef = useRef<number[]>([])

    const startTracking = useCallback((fileCount: number) => {
        fileProgressesRef.current = new Array(fileCount).fill(0)
        setUploadProgress(0)
    }, [])

    const updateFileProgress = useCallback((fileIndex: number, progress: number) => {
        if (fileIndex >= fileProgressesRef.current.length) {
            return
        }
        fileProgressesRef.current[fileIndex] = progress
        const total =
            fileProgressesRef.current.reduce((sum, p) => sum + p, 0) /
            fileProgressesRef.current.length
        setUploadProgress(total)
    }, [])

    const resetProgress = useCallback(() => {
        fileProgressesRef.current = []
        setUploadProgress(0)
    }, [])

    return { uploadProgress, startTracking, updateFileProgress, resetProgress }
}
