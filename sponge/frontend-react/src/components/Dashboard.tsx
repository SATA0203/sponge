import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { taskService, Task, CreateTaskDTO } from '@/services/taskService';
import { useAuthStore } from '@/store';
import { Card, Button, Input, Select, Badge, Spinner, EmptyState } from './common';

// Task Stats Component
function TaskStats({ tasks }: { tasks: Task[] }) {
  const stats = {
    total: tasks.length,
    pending: tasks.filter(t => t.status === 'pending').length,
    running: tasks.filter(t => t.status === 'running').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    failed: tasks.filter(t => t.status === 'failed').length,
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
      <Card className="p-4">
        <div className="text-sm text-gray-500 dark:text-gray-400">总计</div>
        <div className="text-2xl font-bold">{stats.total}</div>
      </Card>
      <Card className="p-4">
        <div className="text-sm text-gray-500 dark:text-gray-400">等待中</div>
        <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
      </Card>
      <Card className="p-4">
        <div className="text-sm text-gray-500 dark:text-gray-400">运行中</div>
        <div className="text-2xl font-bold text-blue-600">{stats.running}</div>
      </Card>
      <Card className="p-4">
        <div className="text-sm text-gray-500 dark:text-gray-400">已完成</div>
        <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
      </Card>
      <Card className="p-4">
        <div className="text-sm text-gray-500 dark:text-gray-400">失败</div>
        <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
      </Card>
    </div>
  );
}

// Task List Component
function TaskList({ 
  tasks, 
  onSelect, 
  selectedId,
  onDelete 
}: { 
  tasks: Task[]; 
  onSelect: (id: string) => void;
  selectedId: string | null;
  onDelete: (id: string) => void;
}) {
  if (tasks.length === 0) {
    return (
      <EmptyState
        title="暂无任务"
        description="创建一个新任务开始使用"
      />
    );
  }

  return (
    <div className="space-y-3">
      {tasks.map((task) => (
        <Card
          key={task.id}
          className={`p-4 cursor-pointer transition-all hover:shadow-md ${
            selectedId === task.id ? 'ring-2 ring-blue-500' : ''
          }`}
          onClick={() => onSelect(task.id)}
        >
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className="font-semibold text-lg">{task.name}</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {task.description || '无描述'}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <Badge status={task.status} />
                <span className="text-xs text-gray-400">
                  {new Date(task.created_at).toLocaleString()}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="danger"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(task.id);
                }}
              >
                删除
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

// New Task Form Component
function NewTaskForm({ onSuccess }: { onSuccess: () => void }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high'>('medium');
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: CreateTaskDTO) => taskService.createTask(data),
    onSuccess: () => {
      toast.success('任务创建成功');
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setName('');
      setDescription('');
      setPriority('medium');
      onSuccess();
    },
    onError: (error: Error) => {
      toast.error(`创建失败：${error.message}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error('请输入任务名称');
      return;
    }
    createMutation.mutate({ name, description, priority });
  };

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold mb-4">创建新任务</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">任务名称 *</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="输入任务名称"
            disabled={createMutation.isPending}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">描述</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="可选的任务描述"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700"
            rows={3}
            disabled={createMutation.isPending}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">优先级</label>
          <Select
            value={priority}
            onChange={(e) => setPriority(e.target.value as 'low' | 'medium' | 'high')}
            options={[
              { value: 'low', label: '低' },
              { value: 'medium', label: '中' },
              { value: 'high', label: '高' },
            ]}
            disabled={createMutation.isPending}
          />
        </div>
        <Button
          type="submit"
          variant="primary"
          disabled={createMutation.isPending}
          className="w-full"
        >
          {createMutation.isPending ? <Spinner size="sm" /> : '创建任务'}
        </Button>
      </form>
    </Card>
  );
}

// Task Detail Component
function TaskDetail({ taskId, onBack }: { taskId: string; onBack: () => void }) {
  const { data: task, isLoading, error } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => taskService.getTask(taskId),
  });

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center">
          <Spinner size="lg" />
        </div>
      </Card>
    );
  }

  if (error || !task) {
    return (
      <Card className="p-6">
        <EmptyState
          title="任务不存在"
          description="该任务可能已被删除"
        />
        <Button onClick={onBack} variant="secondary" className="mt-4">
          返回列表
        </Button>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">{task.name}</h2>
        <Button onClick={onBack} variant="secondary" size="sm">
          ← 返回
        </Button>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">状态</label>
          <div className="mt-1">
            <Badge status={task.status} />
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">优先级</label>
          <div className="mt-1">
            <Badge 
              status={task.priority === 'high' ? 'failed' : task.priority === 'medium' ? 'running' : 'pending'}
              label={task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}
            />
          </div>
        </div>
        
        {task.description && (
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">描述</label>
            <p className="mt-1">{task.description}</p>
          </div>
        )}
        
        <div>
          <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">创建时间</label>
          <p className="mt-1">{new Date(task.created_at).toLocaleString()}</p>
        </div>
        
        {task.updated_at && (
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">更新时间</label>
            <p className="mt-1">{new Date(task.updated_at).toLocaleString()}</p>
          </div>
        )}
        
        {task.result && (
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">结果</label>
            <pre className="mt-1 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-auto text-sm">
              {JSON.stringify(task.result, null, 2)}
            </pre>
          </div>
        )}
        
        {task.error && (
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">错误信息</label>
            <pre className="mt-1 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg overflow-auto text-sm text-red-600">
              {task.error}
            </pre>
          </div>
        )}
      </div>
    </Card>
  );
}

// Main Dashboard Component
export function Dashboard() {
  const navigate = useNavigate();
  const params = useParams();
  const { logout } = useAuthStore();
  const [showNewTask, setShowNewTask] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(params.taskId || null);

  const { data: tasks = [], isLoading, error } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => taskService.getTasks(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => taskService.deleteTask(id),
    onSuccess: () => {
      toast.success('任务已删除');
    },
    onError: (error: Error) => {
      toast.error(`删除失败：${error.message}`);
    },
  });

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleSelectTask = (id: string) => {
    setSelectedTaskId(id);
    navigate(`/tasks/${id}`);
  };

  const handleDeleteTask = (id: string) => {
    if (confirm('确定要删除这个任务吗？')) {
      deleteMutation.mutate(id);
      if (selectedTaskId === id) {
        setSelectedTaskId(null);
        navigate('/');
      }
    }
  };

  // Show task detail if taskId is in URL
  if (params.taskId) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <header className="bg-white dark:bg-gray-800 shadow">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <h1 className="text-2xl font-bold">Sponge 任务管理</h1>
            <div className="flex items-center gap-4">
              <Button onClick={() => navigate('/')} variant="secondary" size="sm">
                返回列表
              </Button>
              <Button onClick={handleLogout} variant="outline" size="sm">
                退出登录
              </Button>
            </div>
          </div>
        </header>
        <main className="max-w-4xl mx-auto px-4 py-6">
          <TaskDetail taskId={params.taskId} onBack={() => navigate('/')} />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Sponge 任务管理</h1>
          <div className="flex items-center gap-4">
            <Button 
              onClick={() => setShowNewTask(!showNewTask)} 
              variant="primary" 
              size="sm"
            >
              {showNewTask ? '取消创建' : '+ 新建任务'}
            </Button>
            <Button onClick={handleLogout} variant="outline" size="sm">
              退出登录
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {showNewTask && (
          <div className="mb-6">
            <NewTaskForm onSuccess={() => setShowNewTask(false)} />
          </div>
        )}

        <TaskStats tasks={tasks} />

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h2 className="text-lg font-semibold mb-4">任务列表</h2>
            {isLoading ? (
              <Card className="p-6">
                <div className="flex items-center justify-center">
                  <Spinner size="lg" />
                </div>
              </Card>
            ) : error ? (
              <Card className="p-6">
                <EmptyState
                  title="加载失败"
                  description={error instanceof Error ? error.message : '未知错误'}
                />
              </Card>
            ) : (
              <TaskList
                tasks={tasks}
                onSelect={handleSelectTask}
                selectedId={selectedTaskId}
                onDelete={handleDeleteTask}
              />
            )}
          </div>

          <div>
            <h2 className="text-lg font-semibold mb-4">快速操作</h2>
            <Card className="p-6">
              <div className="space-y-3">
                <Button
                  onClick={() => setShowNewTask(true)}
                  variant="primary"
                  className="w-full"
                >
                  创建新任务
                </Button>
                <Button
                  onClick={() => window.location.reload()}
                  variant="secondary"
                  className="w-full"
                >
                  刷新列表
                </Button>
              </div>
              
              <div className="mt-6 pt-6 border-t">
                <h3 className="font-medium mb-2">提示</h3>
                <ul className="text-sm text-gray-500 dark:text-gray-400 space-y-1">
                  <li>• 点击任务查看详情</li>
                  <li>• 支持暗色模式切换</li>
                  <li>• 实时任务状态更新</li>
                </ul>
              </div>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
