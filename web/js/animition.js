const btn = document.querySelector('.google-btn');
const stars = document.querySelector('.stars');

btn.addEventListener('mouseenter', () => {
  stars.style.opacity = '600'; // 鼠標靠上按鈕，星星變亮
});

btn.addEventListener('mouseleave', () => {
  stars.style.opacity = '300'; // 鼠標離開，恢復亮度
});
