// ---------- Helpers ----------
const $ = (id) => document.getElementById(id);

function showMessage(text, type) {
    const msg = $("form-message");
    msg.textContent = text;
    msg.className = type; // "success" or "error"
}

// ---------- Table ----------
async function loadUsers() {
    const res = await fetch("/api/users");
    const users = await res.json();
    const tbody = $("users-tbody");
    tbody.innerHTML = "";

    users.forEach((u) => {
        const tr = document.createElement("tr");
        tr.setAttribute("data-testid", `user-row-${u.id}`);
        tr.innerHTML = `
            <td>${u.id}</td>
            <td>${u.name}</td>
            <td>${u.city}</td>
            <td>${u.role}</td>
            <td><button class="delete-btn" data-testid="delete-btn-${u.id}" data-id="${u.id}">Delete</button></td>
        `;
        tbody.appendChild(tr);
    });
    $("user-count").textContent = users.length;
}

// Delete button (event delegation)
$("users-tbody").addEventListener("click", async (e) => {
    if (!e.target.classList.contains("delete-btn")) return;
    const id = e.target.dataset.id;
    await fetch(`/api/users/${id}`, { method: "DELETE" });
    loadUsers();
});

$("refresh-table-btn").addEventListener("click", loadUsers);

// ---------- Form ----------
$("user-form").addEventListener("submit", async (e) => {
    e.preventDefault(); // stop page reload

    if (!$("terms").checked) {
        showMessage("Please accept the terms.", "error");
        return;
    }

    const payload = {
        name: $("name").value,
        city: $("city").value,
        role: $("role").value,
    };

    const res = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (res.ok) {
        showMessage(`User "${data.name}" added successfully!`, "success");
        $("user-form").reset();
        loadUsers();
    } else {
        showMessage(data.error, "error");
    }
});

// ---------- Alerts ----------
$("alert-btn").addEventListener("click", () => {
    alert("Hello! This is an alert.");
    $("dialog-result").textContent = "Alert was closed.";
});

$("confirm-btn").addEventListener("click", () => {
    const ok = confirm("Do you want to continue?");
    $("dialog-result").textContent = ok ? "You clicked OK." : "You clicked Cancel.";
});

$("prompt-btn").addEventListener("click", () => {
    const name = prompt("What is your name?");
    $("dialog-result").textContent = name ? `Hello, ${name}!` : "You cancelled the prompt.";
});

// ---------- Other buttons ----------
$("enable-btn").addEventListener("click", () => {
    $("disabled-btn").disabled = false;
    $("dialog-result").textContent = "Disabled button is now enabled.";
});

$("disabled-btn").addEventListener("click", () => {
    $("dialog-result").textContent = "You clicked the (previously disabled) button!";
});

$("dblclick-btn").addEventListener("dblclick", () => {
    $("dialog-result").textContent = "Double-click detected!";
});

// ---------- Show / hide & delayed ----------
$("toggle-btn").addEventListener("click", () => {
    $("secret-text").classList.toggle("hidden");
});

$("delayed-btn").addEventListener("click", () => {
    $("delayed-text").textContent = "Loading...";
    setTimeout(() => {
        $("delayed-text").textContent = "Data loaded after 3 seconds!";
    }, 3000);
});

// Load the table when the page opens
loadUsers();
