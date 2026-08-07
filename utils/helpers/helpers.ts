// 工具函数

import { STORAGE_KEYS, USER_ROLES, SCORE_RANGE } from '../constants/constants';

// 检查用户权限
export function checkPermission(requiredRole: string): boolean {
  const role = wx.getStorageSync(STORAGE_KEYS.ROLE);
  return role === requiredRole;
};

// 获取用户信息
export function getUserInfo() {
  return wx.getStorageSync(STORAGE_KEYS.USER_INFO);
}

// 获取用户角色
export function getUserRole() {
  return wx.getStorageSync(STORAGE_KEYS.ROLE);
}

// 获取用户openid
export function getUserOpenid() {
  return wx.getStorageSync(STORAGE_KEYS.OPENID);
}

// 格式化时间
export function formatTime(date: Date): string {
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
}

// 格式化日期时间
export function formatDateTime(date: Date): string {
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

// 验证评分范围
export function validateScore(score: number): boolean {
  return !isNaN(score) && score >= SCORE_RANGE.MIN && score <= SCORE_RANGE.MAX;
}

// 显示加载提示
export function showLoading(title: string = '加载中...') {
  wx.showLoading({ title });
}

// 隐藏加载提示
export function hideLoading() {
  wx.hideLoading();
}

// 显示成功提示
export function showSuccessToast(title: string, duration: number = 2000) {
  wx.showToast({
    title,
    icon: 'success',
    duration
  });
}

// 显示错误提示
export function showErrorToast(title: string, duration: number = 2000) {
  wx.showToast({
    title,
    icon: 'none',
    duration
  });
}

// 显示普通提示
export function showNormalToast(title: string, icon: string = 'none', duration: number = 2000) {
  wx.showToast({
    title,
    icon,
    duration
  });
}

// 获取对话历史记录
export function getConversationHistory() {
  return wx.getStorageSync(STORAGE_KEYS.CONVERSATION_HISTORY) || [];
}

// 保存对话历史记录
export function saveConversationHistory(history: any[]) {
  wx.setStorageSync(STORAGE_KEYS.CONVERSATION_HISTORY, history);
}

// 获取报告列表
export function getReports() {
  return wx.getStorageSync(STORAGE_KEYS.REPORTS) || [];
}

// 保存报告列表
export function saveReports(reports: any[]) {
  wx.setStorageSync(STORAGE_KEYS.REPORTS, reports);
}

// 生成对话ID
export function generateConversationId(): string {
  return `conv_${Date.now()}`;
}

// 生成消息ID
export function generateMessageId(index: number): string {
  return `msg_${index}`;
}