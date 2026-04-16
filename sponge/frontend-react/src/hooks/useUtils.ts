import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return '刚刚';
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `${minutes}分钟前`;
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `${hours}小时前`;
  } else if (diffInSeconds < 604800) {
    const days = Math.floor(diffInSeconds / 86400);
    return `${days}天前`;
  } else {
    return formatDate(dateString);
  }
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'badge-pending',
    planning: 'badge-running',
    coding: 'badge-running',
    executing: 'badge-running',
    reviewing: 'badge-running',
    completed: 'badge-completed',
    failed: 'badge-failed',
    cancelled: 'badge-failed',
  };
  return colors[status.toLowerCase()] || 'badge-pending';
}

export function getStatusText(status: string): string {
  const texts: Record<string, string> = {
    pending: '等待中',
    planning: '规划中',
    coding: '编码中',
    executing: '执行中',
    reviewing: '审查中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  };
  return texts[status.toLowerCase()] || status;
}
