import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useHistory } from 'react-router-dom';
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import api from '../utils/api';
import { uploadFile } from '../utils/fileUpload';

interface LeadFormData {
  lead_name: string;
  company_name: string;
  status: string;
  email: string;
  phone: string;
  attachment?: File;
}

export function LeadForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<LeadFormData>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const history = useHistory();

  const onSubmit = async (data: LeadFormData) => {
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      let attachmentUrl = null;
      if (data.attachment) {
        const fileName = `leads/${Date.now()}_${data.attachment.name}`;
        attachmentUrl = await uploadFile(data.attachment, 'leads', fileName);
      }

      const leadData = {
        ...data,
        attachment_url: attachmentUrl
      };

      await api.post('/crm/leads/', leadData);
      setSuccess(true);
      setTimeout(() => history.push('/crm/leads'), 2000);
    } catch (error) {
      setError('Failed to create lead. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Lead</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <Input 
            {...register('lead_name', { required: 'Lead Name is required' })} 
            placeholder="Lead Name" 
            className="mb-2" 
          />
          {errors.lead_name && <p className="text-red-500">{errors.lead_name.message}</p>}
          
          <Input 
            {...register('company_name', { required: 'Company Name is required' })} 
            placeholder="Company Name" 
            className="mb-2" 
          />
          {errors.company_name && <p className="text-red-500">{errors.company_name.message}</p>}
          
          <Select 
            {...register('status', { required: 'Status is required' })} 
            className="mb-2"
          >
            <option value="">Select Status</option>
            <option value="New">New</option>
            <option value="Contacted">Contacted</option>
            <option value="Qualified">Qualified</option>
            <option value="Lost">Lost</option>
          </Select>
          {errors.status && <p className="text-red-500">{errors.status.message}</p>}
          
          <Input 
            {...register('email', { 
              required: 'Email is required', 
              pattern: { 
                value: /^\S+@\S+$/i, 
                message: 'Invalid email address'
              } 
            })} 
            placeholder="Email" 
            className="mb-2" 
          />
          {errors.email && <p className="text-red-500">{errors.email.message}</p>}
          
          <Input 
            {...register('phone', { required: 'Phone is required' })} 
            placeholder="Phone" 
            className="mb-2" 
          />
          {errors.phone && <p className="text-red-500">{errors.phone.message}</p>}
          
          <Input 
            type="file"
            {...register('attachment')} 
            className="mb-2" 
          />
          
          {error && <Alert variant="destructive"><AlertTitle>Error</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
          {success && <Alert><AlertTitle>Success</AlertTitle><AlertDescription>Lead created successfully!</AlertDescription></Alert>}
          
          <Button type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create Lead'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}