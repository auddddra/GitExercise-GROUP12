const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');

registerBtn.addEventListener('click',()=>{
    container.classList.add('active');
})

loginBtn.addEventListener('click',()=>{
    container.classList.remove('active');
})

function togglePasscode() {
  const check = document.getElementById('adminCheck');
  const passDiv = document.getElementById('passcodeDiv');
  passDiv.style.display = check.checked ? 'block' : 'none';
}