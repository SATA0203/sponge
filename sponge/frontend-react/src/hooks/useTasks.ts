import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { taskApi, healthApi, type Task, type CreateTaskRequest } from '@/services/taskService';

// Query keys
export const queryKeys = {
  tasks: {
    all: ['tasks'] as const,
    list: () => [...queryKeys.tasks.all, 'list'] as const,
    detail: (taskId: string) => [...queryKeys.tasks.all, 'detail', taskId] as const,
  },
  health: ['health'] as const,
};

// Hooks for Tasks
export function useTasks() {
  return useQuery({
    queryKey: queryKeys.tasks.list(),
    queryFn: taskApi.getAll,
  });
}

export function useTask(taskId: string) {
  return useQuery({
    queryKey: queryKeys.tasks.detail(taskId),
    queryFn: () => taskApi.getById(taskId),
    enabled: !!taskId,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateTaskRequest) => taskApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks.list() });
    },
  });
}

export function useExecuteWorkflow() {
  return useMutation({
    mutationFn: taskApi.executeWorkflow,
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: taskApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks.list() });
    },
  });
}

// Hook for Health Check
export function useHealthCheck() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: healthApi.check,
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: false,
  });
}
