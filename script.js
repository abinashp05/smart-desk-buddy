
document.addEventListener("DOMContentLoaded", function() {
    const postureIndicator = document.getElementById("posture-indicator");
    const postureStatusText = document.getElementById("posture-status");
    const systemStatusText = document.getElementById("system-status");
    const postureHistoryList = document.getElementById("posture-history-list");
    const videoFeed = document.getElementById("video-feed");

    let lastPosture = "";

    function updateDashboard() {
        fetch("http://localhost:5000/status")
            .then(response => response.json())
            .then(data => {
                const { status, system } = data;

                postureStatusText.textContent = status;
                systemStatusText.textContent = system;

                if (status === "GOOD") {
                    postureIndicator.className = "posture-indicator good";
                } else if (status === "BAD") {
                    postureIndicator.className = "posture-indicator bad";
                } else {
                    postureIndicator.className = "posture-indicator";
                }

                // Update history log only if posture status changes
                if (status !== lastPosture) {
                    const now = new Date();
                    const timeString = now.toLocaleTimeString();
                    const listItem = document.createElement("li");
                    listItem.className = status.toLowerCase();
                    listItem.innerHTML = `<span>${status}</span> <span class="time">${timeString}</span>`;
                    postureHistoryList.prepend(listItem); // Add to the top

                    // Keep log clean, max 10 entries
                    if (postureHistoryList.children.length > 10) {
                        postureHistoryList.removeChild(postureHistoryList.lastChild);
                    }
                    lastPosture = status;
                }
            })
            .catch(error => {
                console.error("Error fetching status:", error);
                postureStatusText.textContent = "Error";
                systemStatusText.textContent = "Monitoring Offline";
                postureIndicator.className = "posture-indicator";
            });
    }

    // Update dashboard every 1 second
    setInterval(updateDashboard, 1000);

    // Refresh video feed image periodically to ensure it's live
    // The browser might cache the image, so appending a timestamp helps
    setInterval(() => {
        videoFeed.src = `http://localhost:5000/video_feed?timestamp=${new Date().getTime()}`;
    }, 100);

    updateDashboard(); // Initial call
});
