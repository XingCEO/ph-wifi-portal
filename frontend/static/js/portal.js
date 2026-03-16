// PH WiFi Portal — Captive Portal Script
// Handles countdown, progress bar, and access grant API call

(function () {
  'use strict';

  const SESSION_ID = window.__PORTAL_SESSION_ID__;
  const REDIRECT_URL = window.__PORTAL_REDIRECT_URL__;
  const AD_DURATION = window.__PORTAL_AD_DURATION__ || 30;

  let secondsLeft = AD_DURATION;
  let granted = false;

  const $number = document.getElementById('countdown-number');
  const $fill = document.getElementById('progress-fill');
  const $hint = document.getElementById('countdown-hint');
  const $tagalog = document.getElementById('tagalog-hint');
  const $btn = document.getElementById('btn-connect');
  const $error = document.getElementById('error-msg');

  function updateDisplay(s) {
    $number.textContent = s;
    const pct = ((AD_DURATION - s) / AD_DURATION * 100).toFixed(1);
    $fill.style.width = pct + '%';
  }

  function onComplete() {
    $number.classList.add('done');
    $hint.textContent = 'Your free WiFi is ready!';
    $hint.classList.add('success');
    $tagalog.textContent = 'Handa na ang iyong libreng internet!';
    $btn.classList.add('visible');
  }

  const timer = setInterval(function () {
    if (secondsLeft <= 0) {
      clearInterval(timer);
      onComplete();
      return;
    }
    secondsLeft--;
    updateDisplay(secondsLeft);
  }, 1000);

  async function grantAccess() {
    if (granted) return;
    granted = true;

    $btn.disabled = true;
    $btn.classList.add('loading');
    $btn.textContent = 'Connecting...';
    $error.classList.remove('visible');

    try {
      const resp = await fetch('/api/grant-access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: SESSION_ID })
      });

      const data = await resp.json();

      if (resp.ok && data.status === 'granted') {
        $btn.textContent = 'Connected!';
        $btn.style.background = '#22c55e';
        setTimeout(function () {
          window.location.href = '/thanks?to=' + encodeURIComponent(REDIRECT_URL || 'https://google.com');
        }, 800);
      } else {
        throw new Error(data.detail || 'Connection failed');
      }
    } catch (err) {
      granted = false;
      $btn.disabled = false;
      $btn.classList.remove('loading');
      $btn.textContent = 'Get Free WiFi';
      $error.textContent = err.message || 'Connection failed. Please try again.';
      $error.classList.add('visible');
    }
  }

  document.getElementById('btn-connect').addEventListener('click', grantAccess);

  var paidLink = document.getElementById('paid-option-link');
  if (paidLink) {
    paidLink.addEventListener('click', function (e) {
      e.preventDefault();
      alert('Paid option coming soon — ₱5 for 30 min');
    });
  }

  // Init display
  updateDisplay(AD_DURATION);
})();
