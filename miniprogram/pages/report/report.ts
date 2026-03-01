// pages/report/report.ts
Page({
  data: {
    report: {} as any,
    previewMessages: [] as Array<any>
  },

  onLoad(options: any) {
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

    const conversationId = options.conversationId;
    if (conversationId) {
      this.loadReport(conversationId);
    }
  },

  // 加载报告详情
  loadReport(conversationId: string) {
    // 从本地存储加载报告
    const reports = wx.getStorageSync('reports') || [];
    const report = reports.find((r: any) => r.conversationId === conversationId);
    
    if (report) {
      // 生成对话预览（最多显示5条消息）
      const previewMessages = report.messages.slice(0, 5);
      
      this.setData({
        report,
        previewMessages
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
  async submitToTeacher() {
    const { report } = this.data;
    const openid = wx.getStorageSync('openid');
    const role = wx.getStorageSync('role');
    
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
      // 调用云函数提交报告
      const cloudRes = await wx.cloud.callFunction({
        name: 'submitReport',
        data: {
          openid,
          role,
          reportData: {
            conversationId: report.conversationId,
            messages: report.messages,
            analysis: report.analysis
          }
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
        status: '待批阅'
      };

      const reports = wx.getStorageSync('reports') || [];
      const updatedReports = reports.map((r: any) => 
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