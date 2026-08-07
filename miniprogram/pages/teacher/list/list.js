// teacher/list/list.js
Component({
  data: {
    reports: []
  },

  lifetimes: {
    attached() {
      // 组件挂载时加载数据
      this.loadReports();
    }
  },

  pageLifetimes: {
    show() {
      // 所在页面显示时加载数据
      this.loadReports();
    }
  },

  methods: {
    // 加载报告列表
    loadReports() {
      wx.showLoading({ title: '正在加载报告...' });

      try {
        const reports = wx.getStorageSync('reports') || [];
        
        // 为每个报告添加固定的原始编号
        const reportsWithIndex = reports.map((report, index) => ({
          ...report,
          originalIndex: index + 1
        }));
        
        // 排序逻辑：先判断是否批阅，再判断编号
        const sortedReports = reportsWithIndex.sort((a, b) => {
          const aStatus = a.status || '待批阅';
          const bStatus = b.status || '待批阅';
          
          if (aStatus === '待批阅' && bStatus !== '待批阅') {
            return -1;
          }
          if (aStatus !== '待批阅' && bStatus === '待批阅') {
            return 1;
          }
          
          return a.originalIndex - b.originalIndex;
        });
        
        this.setData({
          reports: sortedReports
        });
        console.log('从本地存储加载报告列表成功:', sortedReports.length, '条报告');
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
      
      wx.navigateTo({
        url: `/pages/teacher/detail/detail?reportId=${reportId}`
      });
    },

    // 刷新方法（供父组件调用）
    refresh() {
      this.loadReports();
    }
  }
});