import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://wlzfsdrvxtvzatimgcba.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndsemZzZHJ2eHR2emF0aW1nY2JhIiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODY4NzI4NTgsImV4cCI6MjAwMjQ0ODg1OH0.GBPHJRPLnXKLxLHVqZXXXXXXXXXXXXXXXXXXXXXXXXXX'
)

export const uploadFile = async (file: File, bucket: string, path: string) => {
  try {
    const { data, error } = await supabase.storage
      .from(bucket)
      .upload(path, file)

    if (error) {
      throw error
    }

    const { publicURL, error: urlError } = supabase.storage
      .from(bucket)
      .getPublicUrl(path)

    if (urlError) {
      throw urlError
    }

    return publicURL
  } catch (error) {
    console.error('Error uploading file:', error)
    throw error
  }
}

export const deleteFile = async (bucket: string, path: string) => {
  try {
    const { data, error } = await supabase.storage
      .from(bucket)
      .remove([path])

    if (error) {
      throw error
    }

    return data
  } catch (error) {
    console.error('Error deleting file:', error)
    throw error
  }
}