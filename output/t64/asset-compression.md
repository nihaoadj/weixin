# 2026-10-03 代码包资源压缩

用户上传失败提示source size 4694KB exceeds 4MB。此次只压缩两张顶部PNG插画，原有文件名、引用、页面尺寸、RGBA透明背景及功能保持；属于不改变行为的展示维护，不新增完整计划，不上传或发布代码。

- `src\static\insights-hero.png`：1,284,069 → 131,805 bytes，[1536, 1024] → [640, 427]。使用Pillow Lanczos缩至640px宽、PNG optimize/compress_level=9，无调色板量化。
- `src\static\content-reference-hero.png`：840,401 → 184,755 bytes，[1484, 1060] → [640, 457]。使用Pillow Lanczos缩至640px宽、PNG optimize/compress_level=9，无调色板量化。

原图保存在`output/t64/asset-compression-originals/`，不在小程序包中，可按文件恢复。压缩后图片均已打开审阅，透明边缘及图形完整。

显式Demo生产构建exit 0，见[构建记录](asset-compression-build.log)。源图与开发/生产生成图SHA256一致。全目录文件合计（并非微信服务器最终计费/上传包量）：

- `dist/dev/mp-weixin`：3,617,658 bytes，3.45 MiB，小于4,000,000 bytes。
- `dist/build/mp-weixin`：2,744,878 bytes，2.618 MiB，小于4,000,000 bytes。

指定开发目录普通刷新后，教师登录真实tap进入PBL，再运行时导航至内容/学情；SDK 3.17.2、548×1182的[内容页](asset-compression-content.jpg)与[学情页](asset-compression-insights.jpg)均已审阅，插画正常显示，无明显边缘或清晰度异常。运行时导航不计作底栏真实点击。

未改变模板/样式/事件，复用既有类型与原生模板/WXSS证据，无需新增逻辑测试。实际上传需开发者工具重新编译后重试，未以本次构建声称上传成功。此前内容区点击故障属于另一个未确认恢复的问题，本次资源压缩不证明点击修复。
