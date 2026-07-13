import os
import glob

standard_navbar = """    <!-- Global Navbar -->
    <nav class="global-navbar" aria-label="Main Navigation">
      <div class="logo-text">
        <img src="./ganesha.png" alt="Ganesha Logo" class="navbar-ganesha"> Shree Lakshmi <span class="highlight">Astro</span>
      </div>
      <div class="nav-links">
        <a href="/index.html" id="nav-home" class="nav-btn" style="text-decoration: none;">Home</a>
        <a href="/consultation" id="nav-consultant" class="nav-btn" style="text-decoration: none;">Consultant</a>
        <a href="/index.html#pricing" id="nav-pricing" class="nav-btn" style="text-decoration: none;">Pricing</a>
        <a href="/about.html" id="nav-about" class="nav-btn" style="text-decoration: none;">About</a>
      </div>
      <div class="nav-auth">
        <button type="button" id="btn-login-header" class="nav-btn">Sign In</button>
        <button type="button" id="btn-dashboard" class="nav-btn hidden">Dashboard</button>
        <button type="button" id="btn-logout" class="small-btn hidden">Sign Out</button>
      </div>
    </nav>"""

def replace_navbar(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Find where navbar starts and ends
    if '<nav class="global-navbar' in content:
        start_idx = content.find('<nav class="global-navbar')
        if start_idx != -1:
            end_idx = content.find('</nav>', start_idx) + 6
            new_content = content[:start_idx-4] + standard_navbar + content[end_idx:]
            with open(filepath, 'w') as f:
                f.write(new_content)
            print(f"Updated global-navbar in {filepath}")
    elif '<nav class="community-topbar' in content:
        start_idx = content.find('<nav class="community-topbar')
        if start_idx != -1:
            end_idx = content.find('</nav>', start_idx) + 6
            new_content = content[:start_idx-4] + standard_navbar + content[end_idx:]
            with open(filepath, 'w') as f:
                f.write(new_content)
            print(f"Updated community-topbar in {filepath}")


for f in glob.glob('/Users/riteshkumarsingh/Desktop/Kundali/frontend/*.html'):
    replace_navbar(f)
