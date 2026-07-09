const fs = require('fs');
let code = fs.readFileSync('frontend/community.js', 'utf8');

// Replace loadCommunity to check for profile and trigger onboarding
const loadCommunityReplacement = `
    async function loadCommunity() {
        try {
            showStatus('Checking Astro Community membership...');
            const profile = await getCurrentProfile();
            state.memberName = profile?.display_name || profile?.name || state.session?.user?.user_metadata?.full_name || 'Astrologer';
            
            // Check if community profile exists, if not trigger onboarding
            try {
                const commProfile = await apiGet('/api/community/profile');
                if (!commProfile) {
                    showOnboarding();
                    return; // Pause loading until onboarding finishes
                } else {
                    state.memberName = commProfile.display_name || state.memberName;
                }
            } catch (e) {
                console.error("Profile check failed, assuming no profile.", e);
                showOnboarding();
                return;
            }
            
            await finalizeCommunityLoad();
        } catch (error) {
            console.error(error);
            showLanding(error.message.includes('verified astrologer')
                ? 'Astro Community is available only to approved astrologers. Apply to join or check your application status.'
                : error.message);
        }
    }

    async function finalizeCommunityLoad() {
        state.channels = normalizeChannels(await apiGet('/api/community/channels'));
        if (!state.channels.length) throw new Error('No channels are available yet.');
        state.currentChannel = state.channels[0].slug;
        renderChannels();
        showWorkspace();
        await loadPosts(state.currentChannel);
        connectWebSocket(state.currentChannel);
    }

    let currentStep = 1;
    function showOnboarding() {
        document.getElementById('onboarding-overlay').classList.remove('hidden');
        document.querySelectorAll('.btn-next-step').forEach(btn => {
            btn.onclick = () => {
                document.getElementById('step-' + currentStep).classList.remove('active');
                currentStep++;
                const nextEl = document.getElementById('step-' + currentStep);
                if (nextEl) {
                    nextEl.classList.add('active');
                }
            };
        });
        document.getElementById('btn-finish-onboarding').onclick = async () => {
            const username = document.getElementById('ob-username').value;
            const displayName = document.getElementById('ob-displayname').value;
            const bio = document.getElementById('ob-bio').value;
            const systems = document.getElementById('ob-systems').value.split(',').map(s => s.trim()).filter(Boolean);
            
            try {
                const response = await fetch('/api/community/profile', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Authorization': \`Bearer \${state.session.access_token}\`
                    },
                    body: JSON.stringify({
                        username: username || 'user_' + Math.floor(Math.random()*10000),
                        display_name: displayName || state.memberName,
                        bio: bio,
                        state: '',
                        country: '',
                        experience_years: '',
                        specializations: [],
                        languages: [],
                        systems_practiced: systems
                    })
                });
                
                if (response.ok) {
                    document.getElementById('onboarding-overlay').classList.add('hidden');
                    await finalizeCommunityLoad();
                } else {
                    alert("Failed to save profile. Please try again.");
                }
            } catch (e) {
                console.error(e);
                alert("An error occurred saving profile.");
            }
        };
    }
`;

code = code.replace(/async function loadCommunity\(\) \{[\s\S]*?async function getCurrentProfile\(\)/, loadCommunityReplacement + '\n    async function getCurrentProfile()');

fs.writeFileSync('frontend/community.js', code);
console.log('patched');
