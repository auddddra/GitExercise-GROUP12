const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');
const welcomeText = document.getElementById('welcome-text');
const forgotLink = document.querySelector('.forgot-link a');
const backBtn = document.querySelector('.back-btn');

registerBtn.addEventListener('click', () => {
  container.classList.add('active');
  container.classList.remove('forgot-active');
  welcomeText.textContent = "Already have an account?";
  registerBtn.style.display = "none";
  loginBtn.style.display = "inline-block";
});

loginBtn.addEventListener('click', () => {
  container.classList.remove('active');
  container.classList.remove('forgot-active');
  welcomeText.textContent = "Don't have an account yet?";
  loginBtn.style.display = "none";
  registerBtn.style.display = "inline-block";
});

forgotLink.addEventListener('click', (e) => {
  e.preventDefault();
  container.classList.add('forgot-active');
});

backBtn.addEventListener('click', () => {
  container.classList.remove('forgot-active');
});
