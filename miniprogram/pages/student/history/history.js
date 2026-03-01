// history.js
Page({
  data: {
    history: []
  },

  onLoad() {
    // 权限检查
    const role = wx.getStorageSync('role');
    if (role !== 'student') {
      wx.showToast({
        title: '无权限访问此页面',
        icon: 'none',
        duration: 2000
      });
      wx.navigateBack();
      return;
    }

    // 加载历史记录
    this.loadHistory();
  },

  onShow() {
    // 页面显示时重新加载历史记录
    this.loadHistory();
  },

  // 加载历史记录
  loadHistory() {
    try {
      // 从本地存储加载历史记录
      const history = wx.getStorageSync('conversationHistory') || [];
      
      // 从本地存储加载报告信息
      const reports = wx.getStorageSync('reports') || [];
      
      // 合并报告信息到历史记录
      const historyWithReport = history.map((item) => {
        const report = reports.find((r) => r.conversationId === item.conversationId);
        return {
          ...item,
          report
        };
      });
      
      this.setData({
        history: historyWithReport
      });
    } catch (error) {
      console.error('加载历史记录失败:', error);
      this.setData({
        history: []
      });
    }
  },

  // 查看历史记录
  viewHistory(e) {
    const conversationId = e.currentTarget.dataset.conversationId;
    
    // 跳转到聊天页面并传递对话ID
    wx.navigateTo({
      url: `/pages/student/chat/chat?conversationId=${conversationId}`
    });
  }
});