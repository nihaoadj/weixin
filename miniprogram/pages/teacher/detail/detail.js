// detail.js
Page({
  data: {
    report: {},
    teacherScore: '',
    teacherFeedback: ''
  },

  onLoad(options) {
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

    const reportId = options.reportId;
    if (reportId) {
      this.loadReport(reportId);
    }
  },

  // 加载报告详情
  loadReport(reportId) {
    wx.showLoading({ title: '正在加载报告...' });

    try {
      // 直接从本地存储加载报告详情
      const reports = wx.getStorageSync('reports') || [];
      const report = reports.find((r) => r.conversationId === reportId);
      
      if (report) {
        this.setData({
          report,
          // 加载已存在的评分和反馈
          teacherScore: report.teacherScore || '',
          teacherFeedback: report.teacherFeedback || ''
        });
        console.log('从本地存储加载报告详情成功');
      } else {
        throw new Error('报告不存在');
      }
    } catch (error) {
      console.error('获取报告详情失败:', error);
      wx.showToast({
        title: '报告不存在',
        icon: 'none',
        duration: 2000
      });
      wx.navigateBack();
    } finally {
      wx.hideLoading();
    }
  },

  // 评分变化
  onScoreChange(e) {
    this.setData({
      teacherScore: e.detail.value
    });
  },

  // 反馈内容变化
  onFeedbackChange(e) {
    this.setData({
      teacherFeedback: e.detail.value
    });
  },

  // 提交评分和反馈
  submitFeedback() {
    const { report, teacherScore, teacherFeedback } = this.data;
    
    if (!teacherScore) {
      wx.showToast({
        title: '请输入评分',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 验证评分范围
    const score = parseInt(teacherScore);
    if (isNaN(score) || score < 0 || score > 100) {
      wx.showToast({
        title: '评分必须在0-100之间',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    wx.showLoading({ title: '正在提交评分...' });

    try {
      // 直接更新本地存储中的报告状态
      const updatedReport = {
        ...report,
        status: '已批阅',
        teacherScore: score,
        teacherFeedback
      };

      const reports = wx.getStorageSync('reports') || [];
      const updatedReports = reports.map((r) => 
        r.conversationId === report.conversationId ? updatedReport : r
      );
      wx.setStorageSync('reports', updatedReports);

      console.log('提交评分和反馈成功，已更新本地存储');

      wx.hideLoading();
      wx.showToast({
        title: '评分和反馈已提交',
        icon: 'success',
        duration: 2000
      });

      // 跳转回报告列表页面
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
    } catch (error) {
      console.error('提交评分失败:', error);
      wx.hideLoading();
      wx.showToast({
        title: '提交评分失败，请重试',
        icon: 'none',
        duration: 2000
      });
    }
  }
});