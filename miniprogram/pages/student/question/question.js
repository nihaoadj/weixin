// question.js
Page({
  data: {
    categories: [
      {
        name: '医学常识',
        expanded: false,
        questions: [
          {
            id: '1',
            title: '肺炎的典型症状有哪些？',
            type: '医学常识',
            time: '2026-03-08',
            status: '未回答'
          },
          {
            id: '2',
            title: '高血压的诊断标准是什么？',
            type: '医学常识',
            time: '2026-03-07',
            status: '未回答'
          },
          {
            id: '3',
            title: '糖尿病的并发症有哪些？',
            type: '医学常识',
            time: '2026-03-06',
            status: '未回答'
          }
        ]
      },
      {
        name: '模拟诊疗',
        expanded: false,
        questions: [
          {
            id: '4',
            title: '医生您好，我今年65岁，从2小时前开始胸口就有点疼，像压了块石头似的，一直没缓解，我有点担心，这是怎么回事啊？',
            type: '模拟诊疗',
            time: '2026-03-05',
            status: '未回答'
          },
          {
            id: '6',
            title: '医生，我45岁，最近不知道怎么回事，总是特别渴，老想喝水，尿也特别多，而且这段时间体重掉了不少，我是不是得了什么病啊？',
            type: '模拟诊疗',
            time: '2026-03-02',
            status: '未回答'
          }
        ]
      },
      {
        name: '病例分析',
        expanded: false,
        questions: [
          {
            id: '5',
            title: '分析急性阑尾炎的诊断思路和治疗方案',
            type: '病例分析',
            time: '2026-03-04',
            status: '未回答'
          }
        ]
      }
    ],
    isLoading: false,
    page: 1,
    hasMore: true
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

    // 初始加载问题
    this.loadQuestions();
  },

  // 加载问题
  loadQuestions() {
    this.setData({ isLoading: true });

    // 模拟API请求
    setTimeout(() => {
      // 实际开发中，这里应该从服务器获取数据
      this.setData({
        isLoading: false
      });
    }, 500);
  },

  // 切换分类展开/收起
  toggleCategory(e) {
    const index = e.currentTarget.dataset.index;
    const categories = this.data.categories;
    categories[index].expanded = !categories[index].expanded;
    this.setData({ categories });
  },

  // 加载更多问题
  loadMoreQuestions() {
    if (this.data.isLoading || !this.data.hasMore) return;

    this.setData({ isLoading: true });

    // 模拟加载更多数据
    setTimeout(() => {
      this.setData({
        isLoading: false,
        page: this.data.page + 1,
        hasMore: this.data.page < 3 // 模拟只有3页数据
      });
    }, 1000);
  },

  // 返回上一页
  goBack() {
    wx.navigateBack();
  },

  // 选择问题
  selectQuestion(e) {
    const questionId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/student/question-detail/question-detail?id=${questionId}`
    });
  }
});