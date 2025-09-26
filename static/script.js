const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');
const forgotLink = document.querySelector('.forgot-link a');
const backBtn = document.querySelector('.back-btn');

// Switch to Register
registerBtn.addEventListener('click', () => {
  container.classList.add('active');
  loginBtn.style.display = 'block';
  registerBtn.style.display = 'none';
});

// Switch back to Login
loginBtn.addEventListener('click', () => {
  container.classList.remove('active');
  loginBtn.style.display = 'none';
  registerBtn.style.display = 'block';
});

// Show Forgot Password
forgotLink.addEventListener('click', (e) => {
  e.preventDefault();
  container.classList.add('forgot-active');
});

// Back to Login from Forgot
backBtn.addEventListener('click', () => {
  container.classList.remove('forgot-active');
});

// Admin passcode toggle
function togglePasscode() {
  const check = document.getElementById('adminCheck');
  const passDiv = document.getElementById('passcodeDiv');
  passDiv.style.display = check.checked ? 'block' : 'none';
}
