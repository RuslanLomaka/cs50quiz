// ------------------------------------------------------------
// Utility: Get CSRF token from cookies
// ------------------------------------------------------------
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + "=")) {
                cookieValue = cookie.substring(name.length + 1);
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener("DOMContentLoaded", function () {

    // ------------------------------------------------------------
    // LIKE BUTTONS
    // ------------------------------------------------------------
    const likeButtons = document.querySelectorAll(".like-btn");

    likeButtons.forEach(btn => {
        btn.addEventListener("click", async function () {
            const postId = this.dataset.postId;

            const response = await fetch(`/posts/${postId}/like/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                }
            });

            const data = await response.json();
            if (data.error) return;

            // Update button text
            this.innerHTML = data.liked ? "❤️ Unlike" : "🤍 Like";

            // Update like count
            document.getElementById(`like-count-${postId}`).innerText = data.like_count;
        });
    });


    // ------------------------------------------------------------
    // EDIT BUTTONS
    // ------------------------------------------------------------
    const editButtons = document.querySelectorAll(".edit-btn");

    editButtons.forEach(btn => {
        btn.addEventListener("click", function () {
            const postId = this.dataset.postId;
            const contentDiv = document.getElementById(`post-content-${postId}`);

            if (contentDiv.dataset.editing === "true") return;
            contentDiv.dataset.editing = "true";

            const originalText = contentDiv.innerText.trim();

            const textarea = document.createElement("textarea");
            textarea.className = "form-control";
            textarea.value = originalText;

            const saveBtn = document.createElement("button");
            saveBtn.textContent = "Save";
            saveBtn.className = "btn btn-sm btn-primary mt-1";

            const cancelBtn = document.createElement("button");
            cancelBtn.textContent = "Cancel";
            cancelBtn.className = "btn btn-sm btn-secondary mt-1 ml-1";

            // Replace content with editor
            contentDiv.innerHTML = "";
            contentDiv.appendChild(textarea);
            contentDiv.appendChild(saveBtn);
            contentDiv.appendChild(cancelBtn);

            // Cancel edit
            cancelBtn.addEventListener("click", function () {
                contentDiv.dataset.editing = "false";
                contentDiv.innerText = originalText;
            });

            // Save edit
            saveBtn.addEventListener("click", async function () {
                const newContent = textarea.value.trim();
                if (!newContent) {
                    alert("Content cannot be empty.");
                    return;
                }

                const response = await fetch(`/posts/${postId}/edit/`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken"),
                    },
                    body: JSON.stringify({ content: newContent })
                });

                const data = await response.json();
                if (!response.ok) {
                    alert(data.error || "Error saving post.");
                    return;
                }

                // Update DOM
                contentDiv.dataset.editing = "false";
                contentDiv.textContent = data.content;

                const dateEl = document.getElementById(`post-date-${postId}`);
                if (dateEl && data.updated_at) {
                    dateEl.textContent = data.updated_at;
                }
            });
        });
    });

});
