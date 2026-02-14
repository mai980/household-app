/**
 * main.js — カップル家計簿 フロントエンドロジック
 *
 * - localStorage による支払人の記憶
 * - フラッシュメッセージの自動消去
 */

document.addEventListener('DOMContentLoaded', function () {

  // ========================================
  // フラッシュメッセージを 4 秒後に自動フェードアウト
  // ========================================
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 4000);
  });

  // ========================================
  // 金額フィールド: マイナス値を防止
  // ========================================
  const amountInput = document.getElementById('amount');
  if (amountInput) {
    amountInput.addEventListener('input', function () {
      if (this.value && parseInt(this.value) < 0) {
        this.value = Math.abs(parseInt(this.value));
      }
    });
  }

});
