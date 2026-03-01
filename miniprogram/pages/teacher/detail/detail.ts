// pages/teacher/detail/detail.ts
Page({
  data: {
    report: {} as any,
    teacherScore: '',
    teacherFeedback: ''
  },

  onLoad(options: any) {
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
  async loadReport(reportId: string) {
    const openid = wx.getStorageSync('openid');
    const role = wx.getStorageSync('role');
    
    wx.showLoading({ title: '正在加载报告...' });

    try {
      // 调用云函数获取报告详情
      const cloudRes = await wx.cloud.callFunction({
        name: 'getReport',
        data: {
          openid,
          role,
          reportId
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

      const report = result.report;
      if (!report) {
        throw new Error('报告不存在');
      }

      this.setData({
        report
      });
    } catch (error) {
      console.error('获取报告详情失败:', error);
      // 失败时从本地存储加载
      const reports = wx.getStorageSync('reports') || [];
      const report = reports.find((r: any) => r.conversationId === reportId);
      
      if (report) {
        this.setData({
          report
        });
      } else {
        wx.hideLoading();
        wx.showToast({
          title: '报告不存在',
          icon: 'none',
          duration: 2000
        });
        wx.navigateBack();
      }
    } finally {
      wx.hideLoading();
    }
  },

  // 评分变化
  onScoreChange(e: any) {
    this.setData({
      teacherScore: e.detail.value
    });
  },

  // 反馈内容变化
  onFeedbackChange(e: any) {
    this.setData({
      teacherFeedback: e.detail.value
    });
  },

  // 提交评分和反馈
  async submitFeedback() {
    const { report, teacherScore, teacherFeedback } = this.data;
    const openid = wx.getStorageSync('openid');
    const role = wx.getStorageSync('role');
    
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
      // 调用云函数提交评分和反馈
      const cloudRes = await wx.cloud.callFunction({
        name: 'submitReport',
        data: {
          openid,
          role,
          reportId: report.conversationId,
          teacherScore: score,
          teacherFeedback
        }
      });

      // 检查云函数调用是否成功
      if (!cloudRes || !cloudRes.result) {
        throw new Error('云函数调用失败');
      }

      // 确保result是一个对象
      const result = cloudRes.result as any;

      if (!result.success) {
        throw new Error(result.message || '提交失败');
      }

      // 更新本地存储中的报告状态
      const updatedReport = {
        ...report,
        status: '已批阅',
        teacherScore: score,
        teacherFeedback
      };

      const reports = wx.getStorageSync('reports') || [];
      const updatedReports = reports.map((r: any) => 
        r.conversationId === report.conversationId ? updatedReport : r
      );
      wx.setStorageSync('reports', updatedReports);

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