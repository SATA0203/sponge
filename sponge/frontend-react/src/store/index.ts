import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  isAuthenticated: boolean;
  user: string | null;
  accessToken: string | null;
  login: (username: string, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      user: null,
      accessToken: null,
      login: (username, token) => set({ 
        isAuthenticated: true, 
        user: username, 
        accessToken: token 
      }),
      logout: () => set({ 
        isAuthenticated: false, 
        user: null, 
        accessToken: null 
      }),
    }),
    {
      name: 'auth-storage',
    }
  )
);

interface TaskState {
  tasks: any[];
  currentTask: any | null;
  selectedTaskId: string | null;
  setTasks: (tasks: any[]) => void;
  setCurrentTask: (task: any) => void;
  setSelectedTaskId: (id: string | null) => void;
  addTask: (task: any) => void;
  updateTask: (taskId: string, updates: Partial<any>) => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  currentTask: null,
  selectedTaskId: null,
  setTasks: (tasks) => set({ tasks }),
  setCurrentTask: (task) => set({ currentTask: task }),
  setSelectedTaskId: (id) => set({ selectedTaskId: id }),
  addTask: (task) => set((state) => ({ tasks: [task, ...state.tasks] })),
  updateTask: (taskId, updates) => set((state) => ({
    tasks: state.tasks.map(task => 
      task.id === taskId || task.uuid === taskId 
        ? { ...task, ...updates } 
        : task
    ),
    currentTask: state.currentTask?.id === taskId || state.currentTask?.uuid === taskId
      ? { ...state.currentTask, ...updates }
      : state.currentTask,
  })),
}));

interface UIState {
  isDarkMode: boolean;
  sidebarOpen: boolean;
  toggleDarkMode: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  isDarkMode: false,
  sidebarOpen: true,
  toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
