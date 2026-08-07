// pages/teacher/list/list.ts
Page({
  data: {
    reports: [] as Array<{
      conversationId: string;
      messages: Array<{
        role: string;
        content: string;
        timestamp: string;
      }>;
      analysis: any;
      createdAt: string;
      status?: string;
    }>
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
  async loadReports() {
    const openid = wx.getStorageSync('openid');
    const role = wx.getStorageSync('role');
    
    wx.showLoading({ title: '正在加载报告...' });

    try {
      // 调用云函数获取报告列表
      const cloudRes = await wx.cloud.callFunction({
        name: 'getReport',
        data: {
          openid,
          role
        }
      });

      // 检查云函数调用是否成功
      if (!cloudRes || !cloudRes.result) {
        throw new Error('云函数调用失败');
      }

      // 确保result是一个对象
      const result = cloudRes.result as any;

      if (!result.success) {
        throw new Error(result.message || '获取失败');
      }

      // 更新本地存储
      const reports = result.reports || [];
      wx.setStorageSync('reports', reports);

      this.setData({
        reports
      });
    } catch (error) {
      console.error('获取报告列表失败:', error);
      // 失败时从本地存储加载
      const reports = wx.getStorageSync('reports') || [];
      this.setData({
        reports
      });
    } finally {
      wx.hideLoading();
    }
  },

  // 查看报告详情
  viewReport(e: any) {
    const reportId = e.currentTarget.dataset.reportId;
    
    // 跳转到报告详情页面
    wx.navigateTo({
      url: `/pages/teacher/detail/detail?reportId=${reportId}`
    });
  }
});