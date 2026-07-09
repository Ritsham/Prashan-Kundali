import { initAuth } from './auth.js';
import { AppState } from './state.js';
import { API } from './api.js';

let session = null;
let maxProofs = 5;

document.addEventListener("DOMContentLoaded", async () => {
    // Initialize auth
    await initAuth();
    
    // Subscribe to auth changes
    document.addEventListener('astro:authChanged', async (e) => {
        session = e.detail;
        if (!session) {
            // Not logged in -> redirect to home/login
            window.location.href = `/?redirect=${encodeURIComponent(window.location.pathname)}`;
            return;
        }

        document.getElementById("email_field").value = session.user.email;
        
        // Check application status
        try {
            const statusRes = await API.get("/api/community/application/status");
            if (statusRes.status === "APPROVED") {
                window.location.href = "/astro-community";
                return;
            } else if (statusRes.status !== "NOT_APPLIED" && statusRes.status !== "REJECTED" && !statusRes.reapply_allowed) {
                // If pending, needs more info, suspended
                window.location.href = "/community/application-status";
                return;
            }
            
            // Allow applying
            setupWizard();
        } catch (err) {
            console.error("Failed to check status", err);
            alert("Error checking application status. Please try again later.");
        }
    });
});

function setupWizard() {
    document.getElementById("btn-start-apply").addEventListener("click", () => {
        document.getElementById("intro-section").style.display = "none";
        document.getElementById("form-container").style.display = "block";
        addProofField(); // Add first proof field by default
    });

    // Navigation
    document.querySelectorAll(".btn-next").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const currentStep = e.target.closest(".form-section");
            if (validateStep(currentStep)) {
                navigateToStep(e.target.dataset.next);
            }
        });
    });

    document.querySelectorAll(".btn-prev").forEach(btn => {
        btn.addEventListener("click", (e) => {
            navigateToStep(e.target.dataset.prev);
        });
    });

    // Proofs logic
    document.getElementById("btn-add-proof").addEventListener("click", addProofField);

    // Form submit
    document.getElementById("communityApplyForm").addEventListener("submit", submitApplication);
}

function navigateToStep(stepNum) {
    document.querySelectorAll(".form-section").forEach(sec => sec.classList.remove("active"));
    document.querySelectorAll(".step").forEach(st => st.classList.remove("active"));
    
    document.getElementById(`step-${stepNum}`).classList.add("active");
    document.querySelector(`.step[data-step="${stepNum}"]`).classList.add("active");
}

function validateStep(stepEl) {
    const inputs = stepEl.querySelectorAll("input[required], select[required], textarea[required]");
    let valid = true;
    inputs.forEach(input => {
        if (!input.checkValidity()) {
            input.reportValidity();
            valid = false;
        }
    });
    
    // Step 2 systems input
    if (valid && stepEl.id === "step-2") {
        const systemsInput = stepEl.querySelector("input[name='systems']");
        if (!systemsInput.value.trim()) {
            alert("Please enter at least one astrology system.");
            valid = false;
        }
    }
    
    // Step 3 proofs
    if (valid && stepEl.id === "step-3") {
        const proofItems = document.querySelectorAll(".proof-item");
        if (proofItems.length === 0) {
            alert("Please provide at least one supporting proof.");
            valid = false;
        }
        proofItems.forEach(item => {
            const url = item.querySelector(".proof-url").value.trim();
            const file = item.querySelector(".proof-file").files[0];
            const errorEl = item.querySelector(".proof-error");
            if (!url && !file) {
                errorEl.textContent = "Please provide either a link or upload a file.";
                errorEl.style.display = "block";
                valid = false;
            } else {
                errorEl.style.display = "none";
            }
        });
    }

    return valid;
}

function addProofField() {
    const container = document.getElementById("proofs-container");
    if (container.children.length >= maxProofs) {
        alert("Maximum 5 proofs allowed.");
        return;
    }
    const template = document.getElementById("proof-template");
    const clone = template.content.cloneNode(true);
    
    clone.querySelector(".remove-proof").addEventListener("click", (e) => {
        e.target.closest(".proof-item").remove();
        document.getElementById("btn-add-proof").style.display = "inline-block";
    });
    
    container.appendChild(clone);
    
    if (container.children.length >= maxProofs) {
        document.getElementById("btn-add-proof").style.display = "none";
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    
    const token = session.access_token;
    const res = await fetch("/api/community/application/upload-proof", {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${token}`
        },
        body: formData
    });
    
    if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to upload file");
    }
    return await res.json();
}

async function submitApplication(e) {
    e.preventDefault();
    const form = e.target;
    
    const submitBtn = document.getElementById("btn-final-submit");
    const errorMsg = document.getElementById("error-message");
    
    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting...";
    errorMsg.style.display = "none";
    
    try {
        const systemsInputValue = form.querySelector("input[name='systems']").value;
        const systems = systemsInputValue.split(',').map(s => s.trim()).filter(s => s.length > 0);
        
        // Process proofs (upload files if any)
        const proofItems = document.querySelectorAll(".proof-item");
        const processedProofs = [];
        
        for (let item of proofItems) {
            const type = item.querySelector(".proof-type").value;
            const url = item.querySelector(".proof-url").value.trim();
            const file = item.querySelector(".proof-file").files[0];
            
            let proofData = { type, external_url: url || null };
            
            if (file) {
                const uploaded = await uploadFile(file);
                proofData.file_url = uploaded.file_url;
                proofData.original_file_name = uploaded.original_file_name;
                proofData.mime_type = uploaded.mime_type;
                proofData.file_size = uploaded.file_size;
            }
            processedProofs.push(proofData);
        }
        
        const payload = {
            full_name: form.querySelector("input[name='full_name']").value,
            email: form.querySelector("input[name='email']").value,
            mobile_number: form.querySelector("input[name='mobile_number']").value,
            state: form.querySelector("input[name='state']").value,
            country: form.querySelector("input[name='country']").value,
            applicant_type: form.querySelector("select[name='applicant_type']").value,
            experience_range: form.querySelector("select[name='experience_range']").value,
            systems: systems,
            background_description: form.querySelector("textarea[name='background_description']").value,
            additional_information: form.querySelector("textarea[name='additional_information']").value,
            proofs: processedProofs
        };
        
        await API.post("/api/community/application", payload);
        
        // Success -> Redirect to status page
        window.location.href = "/community/application-status";
        
    } catch (err) {
        console.error(err);
        errorMsg.textContent = err.message || "An error occurred during submission.";
        errorMsg.style.display = "block";
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit Application";
    }
}
