import apiClient from './api';

export interface Task {
  id: string;
  uuid: string;
  title: string;
  description: string;
  requirements?: string;
  priority: string;
  tags: string[];
  assigned_agents: string[];
  status: 'pending' | 'planning' | 'coding' | 'executing' | 'reviewing' | 'completed' | 'failed' | 'cancelled';
  current_step?: string;
  iterations: number;
  errors: any[];
  result?: any;
  created_at: string;
  updated_at: string;
  files?: FileItem[];
  agent_results?: Record<string, string>;
}

export interface FileItem {
  id: string;
  uuid: string;
  task_uuid: string;
  filename: string;
  filepath: string;
  content?: string;
  file_type?: string;
  size: number;
  created_at: string;
  updated_at: string;
}

export interface CreateTaskRequest {
  title: string;
  description: string;
  requirements?: string;
  language?: string;
  priority?: string;
  tags?: string[];
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
}

// Auth APIs
export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post('/api/v1/auth/login', data);
    return response.data;
  },
};

// Task APIs
export const taskApi = {
  getAll: async (): Promise<Task[]> => {
    const response = await apiClient.get('/api/v1/tasks');
    return response.data;
  },

  getById: async (taskId: string): Promise<Task> => {
    const response = await apiClient.get(`/api/v1/tasks/${taskId}`);
    return response.data;
  },

  create: async (data: CreateTaskRequest): Promise<Task> => {
    const response = await apiClient.post('/api/v1/tasks', data);
    return response.data;
  },

  executeWorkflow: async (taskId: string): Promise<any> => {
    const response = await apiClient.post(`/api/v1/workflow/execute/${taskId}`);
    return response.data;
  },

  updateStatus: async (taskId: string, status: string): Promise<Task> => {
    const response = await apiClient.patch(`/api/v1/tasks/${taskId}/status`, { status });
    return response.data;
  },

  delete: async (taskId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/tasks/${taskId}`);
  },
};

// File APIs
export const fileApi = {
  getByTask: async (taskUuid: string): Promise<FileItem[]> => {
    const response = await apiClient.get(`/api/v1/files/task/${taskUuid}`);
    return response.data;
  },

  download: async (fileUuid: string): Promise<Blob> => {
    const response = await apiClient.get(`/api/v1/files/${fileUuid}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// Health API
export const healthApi = {
  check: async (): Promise<any> => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};
