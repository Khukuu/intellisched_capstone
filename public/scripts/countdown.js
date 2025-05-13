const form = document.querySelector("form");
const button = document.getElementById("resetButton");

form.addEventListener("submit", function (e) {
  e.preventDefault();

  let countdown = 30;
  button.disabled = true;
  button.classList.add("countdown-active");
  button.innerText = `Resend in ${countdown}s`;

  const interval = setInterval(() => {
    countdown--;
    button.innerText = `Resend in ${countdown}s`;

    if (countdown <= 0) {
      clearInterval(interval);
      button.disabled = false;
      button.classList.remove("countdown-active");
      button.innerText = "Send Reset Link";
    }
  }, 1000);
});