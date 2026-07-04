import { showFlash } from './flash.js';

async function fetchQueue() {
  try {
    const res = await fetch("/api/consultation/queue");
    if (!res.ok) return;
    const data = await res.json();
    renderQueue(data.queue);
  } catch(e) {
    console.error(e);
    showFlash("Failed to load consultation queue: " + e.message, "error");
  }
}

let activeItem = null;
let queueData = [];

function renderQueue(queue) {
  queueData = queue;
  document.getElementById("q-count").textContent = `${queue.length}/20`;
  const list = document.getElementById("queue-list");
  list.innerHTML = "";
  
  if (queue.length === 0) {
    list.innerHTML = "<li class='text-muted' style='padding: 16px; font-size:14px;'>Queue is empty</li>";
    if (activeItem) {
      document.getElementById("main-view").innerHTML = "<div class='empty-state'>Queue is empty.</div>";
      activeItem = null;
    }
    return;
  }

  queue.forEach(item => {
    const li = document.createElement("li");
    li.className = "queue-item" + (activeItem && activeItem.id === item.id ? " active" : "");
    li.innerHTML = `
      <h4>${item.user_name}</h4>
      <p>SLA: ${new Date(item.sla_deadline).toLocaleString()}</p>
    `;
    li.addEventListener("click", () => selectItem(item.id));
    list.appendChild(li);
  });
}

function selectItem(id) {
  const item = queueData.find(i => i.id === id);
  if (!item) return;
  activeItem = item;
  renderQueue(queueData); // update active class
  
  const main = document.getElementById("main-view");
  main.innerHTML = `
    <div class="detail-card">
      <h2>Consultation for ${item.user_name}</h2>
      <p class="text-muted" style="font-size: 13px;">Deadline: ${new Date(item.sla_deadline).toLocaleString()}</p>
      
      <div class="question-box">
        <strong>Question:</strong><br/>
        ${item.question_text}
      </div>

      <div class="chart-previews">
        <div class="chart-box">
          <strong>Lagna Chart Snapshot</strong><br/>
          (Pre-calculated data available here)
          <pre style="overflow:auto; height: 100px;">${JSON.stringify(item.astrological_snapshot.houses || item.astrological_snapshot, null, 2)}</pre>
        </div>
        <div class="chart-box">
          <strong>Transits & Dashas</strong><br/>
          (Pre-calculated data available here)
        </div>
      </div>

      <h3 style="margin-top: 24px;">Your Answer</h3>
      <textarea id="answer-input" placeholder="Type your astrological reading and answer here..."></textarea>
      
      <div class="actions">
        <button class="btn-primary" onclick="submitAnswer('${item.id}')">Submit Answer</button>
        <button class="btn-danger" onclick="declineQuestion('${item.id}')">Decline (Refund User)</button>
      </div>
      <p id="action-status" style="margin-top: 12px; font-size:14px;"></p>
    </div>
  `;
}

window.submitAnswer = async function(id) {
  const answer = document.getElementById("answer-input").value.trim();
  const status = document.getElementById("action-status");
  if (answer.length < 5) {
    status.className = "status-error";
    status.textContent = "Answer too short.";
    return;
  }
  
  status.textContent = "Submitting...";
  try {
    const res = await fetch(`/api/consultation/${id}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer })
    });
    if (res.ok) {
      status.className = "status-success";
      status.textContent = "Answer submitted successfully!";
      activeItem = null;
      setTimeout(fetchQueue, 1000);
    } else {
      status.className = "status-error";
      status.textContent = "Failed to submit.";
    }
  } catch(e) {
    status.className = "status-error";
    status.textContent = "Error.";
    showFlash("Error submitting answer: " + e.message, "error");
  }
}

window.declineQuestion = async function(id) {
  if(!confirm("Are you sure you want to decline? The user will be refunded.")) return;
  const status = document.getElementById("action-status");
  status.textContent = "Declining...";
  try {
    const res = await fetch(`/api/consultation/${id}/decline`, { method: "POST" });
    if (res.ok) {
      status.className = "status-success";
      status.textContent = "Declined successfully.";
      activeItem = null;
      setTimeout(fetchQueue, 1000);
    } else {
      status.className = "status-error";
      status.textContent = "Failed to decline.";
    }
  } catch(e) {
    status.className = "status-error";
    status.textContent = "Error.";
    showFlash("Error declining case: " + e.message, "error");
  }
}

fetchQueue();
setInterval(fetchQueue, 5000);
