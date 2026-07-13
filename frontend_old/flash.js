export function showFlash(message, type = 'error') {
  let container = document.querySelector('.astro-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'astro-toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `astro-toast ${type}`;
  
  let icon = '🕉️';
  if (type === 'error') icon = '⚠️';
  else if (type === 'success') icon = '✨';

  toast.innerHTML = `
    <span class="astro-toast-icon">${icon}</span>
    <span class="astro-toast-message">${message}</span>
  `;

  container.appendChild(toast);

  // Trigger reflow to animate
  toast.offsetHeight;

  toast.classList.add('show');

  // Remove after 3 seconds
  setTimeout(() => {
    toast.classList.remove('show');
    toast.addEventListener('transitionend', () => {
      toast.remove();
      if (container.children.length === 0) {
        container.remove();
      }
    });
  }, 3000);
}

// Bind to window for non-module script access if needed
window.showFlash = showFlash;
