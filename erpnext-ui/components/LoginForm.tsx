import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuth } from '../context/AuthContext';
import { useHistory } from 'react-router-dom';

interface LoginFormData {
  username: string;
  password: string;
}

export function LoginForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormData>();
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const history = useHistory();

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data.username, data.password);
      history.push('/dashboard');
    } catch (err) {
      setError('Invalid username or password');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Input
        {...register('username', { required: true })}
        placeholder="Username"
      />
      <Input
        {...register('password', { required: true })}
        type="password"
        placeholder="Password"
      />
      <Button type="submit">Login</Button>
      {error && <p>{error}</p>}
    </form>
  );
}