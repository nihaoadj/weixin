// list.js
Page({
  data: {
    reports: []
  },

  onLoad() {
    // 权限检查
    const role = wx.getStorageSync('role');
    if (role !== 'teacher') {
      wx.showToast({
        title: '无权限访问此页面',
        icon: 'none',
        duration: 2000
      });
      wx.navigateBack();
      return;
    }

    // 加载报告列表
    this.loadReports();
  },

  onShow() {
    // 页面显示时重新加载报告列表
    this.loadReports();
  },

  // 加载报告列表
  loadReports() {
    const openid = wx.getStorageSync('openid');
    const role = wx.getStorageSync('role');
    
    wx.showLoading({ title: '正在加载报告...' });

    // 直接从本地存储加载报告列表，绕过云函数调用
    try {
      const reports = wx.getStorageSync('reports') || [];
      this.setData({
        reports
      });
      console.log('从本地存储加载报告列表成功:', reports.length, '条报告');
    } catch (error) {
      console.error('获取报告列表失败:', error);
      this.setData({
        reports: []
      });
    } finally {
      wx.hideLoading();
    }
  },

  // 查看报告详情
  viewReport(e) {
    const reportId = e.currentTarget.dataset.reportId;
    
    // 跳转到报告详情页面
    wx.navigateTo({
      url: `/pages/teacher/detail/detail?reportId=${reportId}`
    });
  }
});