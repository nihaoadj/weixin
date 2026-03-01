// report.js
Page({
  data: {
    report: null
  },

  onLoad(options) {
    // 权限检查
    const role = wx.getStorageSync('role');
    if (!role) {
      wx.showToast({
        title: '请先登录',
        icon: 'none',
        duration: 2000
      });
      wx.navigateBack();
      return;
    }

    const conversationId = options.conversationId;
    if (conversationId) {
      this.loadReport(conversationId);
    } else {
      wx.showToast({
        title: '报告不存在',
        icon: 'none',
        duration: 2000
      });
      wx.navigateBack();
    }
  },

  // 加载报告
  loadReport(conversationId) {
    // 从本地存储加载报告
    const reports = wx.getStorageSync('reports') || [];
    const report = reports.find((r) => r.conversationId === conversationId);
    
    if (report) {
      this.setData({
        report
      });
    } else {
      wx.showToast({
        title: '报告不存在',
        icon: 'none',
        duration: 2000
      });
      wx.navigateBack();
    }
  },

  // 提交给教师批阅
  submitToTeacher() {
    const { report } = this.data;
    
    if (!report) {
      wx.showToast({
        title: '报告不存在',
        icon: 'none',
        duration: 2000
      });
      return;
    }
    
    wx.showLoading({ title: '正在提交报告...' });

    try {
      // 直接更新本地存储中的报告状态
      const updatedReport = {
        ...report,
        status: '待批阅'
      };

      const reports = wx.getStorageSync('reports') || [];
      const updatedReports = reports.map((r) => 
        r.conversationId === report.conversationId ? updatedReport : r
      );
      wx.setStorageSync('reports', updatedReports);

      wx.hideLoading();
      wx.showToast({
        title: '报告已提交给教师',
        icon: 'success',
        duration: 2000
      });

      // 跳转回聊天页面
      setTimeout(() => {
        wx.navigateTo({
          url: '/pages/student/chat/chat'
        });
      }, 1500);
    } catch (error) {
      console.error('提交报告失败:', error);
      wx.hideLoading();
      wx.showToast({
        title: '提交报告失败，请重试',
        icon: 'none',
        duration: 2000
      });
    }
  },

  // 返回聊天页面
  backToChat() {
    wx.navigateBack();
  }
});