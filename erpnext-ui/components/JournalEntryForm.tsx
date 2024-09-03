import React, { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { DatePicker } from "@/components/ui/date-picker"
import api from '../utils/api';

interface JournalEntryFormData {
  posting_date: Date;
  company: string;
  accounts: Array<{ account: string; debit: number; credit: number }>;
}

export function JournalEntryForm() {
  const { register, control, handleSubmit, formState: { errors } } = useForm<JournalEntryFormData>();
  const { fields, append, remove } = useFieldArray({
    control,
    name: "accounts"
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (data: JournalEntryFormData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post('/journal-entries/', data);
      console.log('Journal Entry created:', response.data);
      // Handle success (e.g., show success message, reset form)
    } catch (error) {
      console.error('Error creating journal entry:', error);
      setError('Failed to create journal entry. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <DatePicker {...register('posting_date', { required: true })} />
      <Input {...register('company', { required: true })} placeholder="Company" />
      {fields.map((field, index) => (
        <div key={field.id}>
          <Input {...register(`accounts.${index}.account`, { required: true })} placeholder="Account" />
          <Input {...register(`accounts.${index}.debit`, { required: true, min: 0 })} type="number" placeholder="Debit" />
          <Input {...register(`accounts.${index}.credit`, { required: true, min: 0 })} type="number" placeholder="Credit" />
          <Button type="button" onClick={() => remove(index)}>Remove</Button>
        </div>
      ))}
      <Button type="button" onClick={() => append({ account: '', debit: 0, credit: 0 })}>
        Add Account
      </Button>
      {error && <p className="error">{error}</p>}
      <Button type="submit" disabled={loading}>
        {loading ? 'Submitting...' : 'Submit'}
      </Button>
    </form>
  );
}