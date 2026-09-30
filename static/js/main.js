/* CCM Main JavaScript Utility & Interactive Behaviors */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Theme Switcher (Light / Dark Mode)
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const savedTheme = localStorage.getItem('ccm_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('ccm_theme', newTheme);
      updateThemeIcon(newTheme);
    });
    updateThemeIcon(savedTheme);
  }

  function updateThemeIcon(theme) {
    if (!themeToggleBtn) return;
    if (theme === 'dark') {
      themeToggleBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m4.93 19.07 1.41-1.41"/><path d="m17.66 6.34 1.41-1.41"/></svg>`;
    } else {
      themeToggleBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>`;
    }
  }

  // 2. Sidebar Mobile Drawer Toggle & Backdrop
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');

  function toggleSidebar(forceState) {
    if (!sidebar) return;
    const shouldShow = forceState !== undefined ? forceState : !sidebar.classList.contains('show');
    if (shouldShow) {
      sidebar.classList.add('show');
      if (sidebarBackdrop) sidebarBackdrop.classList.add('show');
    } else {
      sidebar.classList.remove('show');
      if (sidebarBackdrop) sidebarBackdrop.classList.remove('show');
    }
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleSidebar();
    });
  }
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', () => {
      toggleSidebar(false);
    });
  }

  // 3. Notification Dropdown Toggle
  const notifBtn = document.getElementById('notifBtn');
  const notifDropdown = document.getElementById('notifDropdown');
  if (notifBtn && notifDropdown) {
    notifBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notifDropdown.classList.toggle('active');
    });
    document.addEventListener('click', () => {
      notifDropdown.classList.remove('active');
    });
    notifDropdown.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  }

  // 4. Confirmation for Destructive Actions
  const confirmActions = document.querySelectorAll('[data-confirm]');
  confirmActions.forEach(element => {
    element.addEventListener('click', (e) => {
      const message = element.getAttribute('data-confirm') || 'Are you sure you want to perform this action?';
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });
});
