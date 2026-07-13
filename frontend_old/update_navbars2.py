import os
import glob

standard_navbar = """    <!-- Global Navbar -->
    <nav class="global-navbar" aria-label="Main Navigation">
      <div class="logo-text">
        <img src="./ganesha.webp" alt="Ganesha Logo" class="navbar-ganesha"> Shree Lakshmi <span class="highlight">Astro</span>
      </div>
      <div class="nav-links">
        <a href="/index.html" id="nav-home" class="nav-btn" style="text-decoration: none;">Home</a>
        <a href="/consultation" id="nav-consultant" class="nav-btn" style="text-decoration: none;">Consultant</a>
        <a href="/index.html#pricing" id="nav-pricing" class="nav-btn" style="text-decoration: none;">Pricing</a>
        <a href="/about.html" id="nav-about" class="nav-btn" style="text-decoration: none;">About</a>
        <a href="/astro-community" id="nav-community" class="nav-btn" style="text-decoration: none;" target="_blank">Astro Community</a>
      </div>
      <div class="nav-auth">
        <button type="button" id="btn-login-header" class="nav-btn">Sign In</button>
        <button type="button" id="btn-profile" class="nav-btn hidden" onclick="window.location.href='/profile.html'">Profile</button>
        <button type="button" id="btn-logout" class="small-btn hidden">Sign Out</button>
      </div>
    </nav>
    <script>
      document.addEventListener("DOMContentLoaded", () => {
        const path = window.location.pathname;
        if (path === '/' || path.includes('index.html')) {
          document.getElementById('nav-home')?.classList.add('active');
        } else if (path.includes('consultation')) {
          document.getElementById('nav-consultant')?.classList.add('active');
        } else if (path.includes('about')) {
          document.getElementById('nav-about')?.classList.add('active');
        } else if (path.includes('community')) {
          document.getElementById('nav-community')?.classList.add('active');
        }
      });
    </script>"""

def replace_navbar(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    if '<nav class="global-navbar' in content:
        start_idx = content.find('<nav class="global-navbar')
        if start_idx != -1:
            end_idx = content.find('</nav>', start_idx) + 6
            new_content = content[:start_idx-4] + standard_navbar + content[end_idx:]
            with open(filepath, 'w') as f:
                f.write(new_content)
            print(f"Updated global-navbar in {filepath}")


for f in glob.glob('/Users/riteshkumarsingh/Desktop/Kundali/frontend_old/*.html'):
    replace_navbar(f)
