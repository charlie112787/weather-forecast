const bgSelect = document.getElementById('bg-select');

bgSelect.addEventListener('change', (e) => {
  document.body.className = ''; // 清除現有 class
  const value = e.target.value;
  document.body.classList.add(value);
});
