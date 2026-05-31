<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'

onLaunch(() => {
  console.log('张雪峰 AI 咨询 App Launch')
})
</script>

<style>
/* 全局样式 */
page {
  background: #f5f0e8;
  font-family: 'Noto Serif SC', 'Source Han Serif CN', serif;
  color: #1a1a2e;
}

/* 报纸风格基础类 */
.stamp {
  font-size: 20rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: monospace;
  border: 2rpx solid #1a1a2e;
  padding: 4rpx 12rpx;
  text-transform: uppercase;
}

/* 安全区适配 */
.safe-area-bottom {
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}
</style>
