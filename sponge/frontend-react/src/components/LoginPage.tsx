import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '@/services/taskService';
import { useAuthStore } from '@/store';
import { Button, Input, Card } from './common';
import toast from 'react-hot-toast';

export function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await authApi.login({ username, password });
      login(response.username, response.access_token);
      toast.success('登录成功！');
      navigate('/');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || '登录失败，请检查用户名和密码');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100 dark:from-gray-900 dark:to-gray-800">
      <Card className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-primary-600 mb-2">🧽 Sponge</h1>
          <p className="text-gray-600 dark:text-gray-400">多智能体协作系统</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            label="用户名"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="请输入用户名"
            required
          />

          <Input
            label="密码"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="请输入密码"
            required
          />

          <Button
            type="submit"
            variant="primary"
            size="lg"
            isLoading={isLoading}
            className="w-full"
          >
            登录
          </Button>
        </form>

        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            💡 默认账号：admin / admin123
          </p>
        </div>
      </Card>
    </div>
  );
}
