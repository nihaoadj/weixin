Page({
  data: {
    currentTab: 'list',
    pendingReportCount: 0,
    pendingProblemCount: 0
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

    this.loadCounts();
    this.updateNavigationBarTitle('list');
  },

  onShow() {
    this.loadCounts();
  },

  loadCounts() {
    try {
      const reports = wx.getStorageSync('reports') || [];
      const pendingReports = reports.filter(r => !r.status || r.status === '待批阅');
      
      const problems = wx.getStorageSync('problems') || [];
      const pendingProblems = problems.filter(p => p.status === '待审核');
      
      this.setData({
        pendingReportCount: pendingReports.length,
        pendingProblemCount: pendingProblems.length
      });
    } catch (error) {
      console.error('加载数量失败:', error);
    }
  },

  updateNavigationBarTitle(tab) {
    const title = tab === 'list' ? '待批阅报告' : '问题发布';
    wx.setNavigationBarTitle({
      title: title
    });
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({
      currentTab: tab
    });
    this.updateNavigationBarTitle(tab);
  }
});