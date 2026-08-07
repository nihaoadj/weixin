// pages/teacher/problem-edit/problem-edit.js
Page({
  data: {
    isEdit: false,
    problemId: '',
    typeIndex: 0,
    typeOptions: ['医学常识', '模拟诊疗', '病例分析'],
    title: '',
    description: '',
    target: 'all'
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ isEdit: true, problemId: options.id });
      
      if (options.problem) {
        try {
          const problem = JSON.parse(decodeURIComponent(options.problem));
          this.loadProblemData(problem);
        } catch (error) {
          console.error('解析问题数据失败:', error);
        }
      }
    }
  },

  loadProblemData(problem) {
    const typeIndex = this.data.typeOptions.indexOf(problem.type);
    
    this.setData({
      typeIndex: typeIndex >= 0 ? typeIndex : 0,
      title: problem.title || '',
      description: problem.description || '',
      target: problem.target || 'all'
    });
  },

  onTypeChange(e) {
    this.setData({ typeIndex: parseInt(e.detail.value) });
  },

  onTitleInput(e) {
    this.setData({ title: e.detail.value });
  },

  onDescInput(e) {
    this.setData({ description: e.detail.value });
  },

  selectTarget(e) {
    this.setData({ target: e.currentTarget.dataset.target });
  },

  saveProblem() {
    if (!this.data.title.trim()) {
      wx.showToast({ title: '请输入问题标题', icon: 'none' });
      return;
    }

    const problemData = {
      id: this.data.isEdit ? this.data.problemId : `prob_${Date.now()}`,
      type: this.data.typeOptions[this.data.typeIndex],
      title: this.data.title.trim(),
      description: this.data.description.trim(),
      target: this.data.target,
      status: '待审核',
      time: new Date().toISOString().split('T')[0]
    };

    wx.showLoading({ title: '保存中...' });

    try {
      const problems = wx.getStorageSync('problems') || [];
      
      if (this.data.isEdit) {
        const index = problems.findIndex(p => p.id === this.data.problemId);
        if (index >= 0) {
          problems[index] = { ...problems[index], ...problemData };
        }
      } else {
        problems.unshift(problemData);
      }
      
      wx.setStorageSync('problems', problems);
      
      wx.hideLoading();
      wx.showToast({
        title: '保存成功',
        icon: 'success',
        duration: 1500,
        success: () => {
          setTimeout(() => wx.navigateBack(), 1500);
        }
      });
    } catch (error) {
      console.error('保存失败:', error);
      wx.hideLoading();
      wx.showToast({ title: '保存失败', icon: 'none' });
    }
  },

  goBack() {
    wx.navigateBack();
  }
});