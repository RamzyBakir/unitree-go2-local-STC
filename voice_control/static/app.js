(function () {
    const wsStatusEl = document.getElementById("ws-status");
    const robotStatusEl = document.getElementById("robot-status");
    const modelInfoEl = document.getElementById("model-info");
    const stateCard = document.getElementById("state-card");
    const stateIcon = document.getElementById("state-icon");
    const stateText = document.getElementById("state-text");
    const transcriptionEl = document.getElementById("transcription");
    const transcriptionText = document.getElementById("transcription-text");
    const commandMatchedEl = document.getElementById("command-matched");
    const matchedCommand = document.getElementById("matched-command");
    const commandResultEl = document.getElementById("command-result");
    const resultIcon = document.getElementById("result-icon");
    const resultMessage = document.getElementById("result-message");
    const errorMessageEl = document.getElementById("error-message");
    const errorText = document.getElementById("error-text");
    const commandsList = document.getElementById("commands-list");

    let ws = null;
    let reconnectTimer = null;

    function setState(status, icon, text) {
        stateCard.className = "status-card " + status;
        stateIcon.textContent = icon;
        stateText.textContent = text;
    }

    function hideAll() {
        [transcriptionEl, commandMatchedEl, commandResultEl, errorMessageEl].forEach(
            (el) => el.classList.add("hidden")
        );
    }

    function showTranscription(text) {
        transcriptionText.textContent = text ? `"${text}"` : "";
        transcriptionEl.classList.remove("hidden");
    }

    function showCommandMatched(cmd) {
        matchedCommand.textContent = cmd;
        commandMatchedEl.classList.remove("hidden");
    }

    function showResult(success, cmd, code) {
        resultIcon.textContent = success ? "✅" : "❌";
        resultMessage.textContent = success ? `${cmd} — OK` : `${cmd} — Error (code ${code})`;
        commandResultEl.classList.remove("hidden");
        commandResultEl.className = "feedback-card " + (success ? "success" : "error");
    }

    function showError(msg) {
        errorText.textContent = msg;
        errorMessageEl.classList.remove("hidden");
    }

    function connect() {
        if (reconnectTimer) clearTimeout(reconnectTimer);
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        ws = new WebSocket(`${proto}//${location.host}/ws/status`);

        ws.onopen = () => {
            wsStatusEl.textContent = "Connected";
            wsStatusEl.className = "status-indicator connected";
        };

        ws.onclose = () => {
            wsStatusEl.textContent = "Disconnected";
            wsStatusEl.className = "status-indicator disconnected";
            reconnectTimer = setTimeout(connect, 2000);
        };

        ws.onerror = () => {};

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch (data.type) {
                case "ready":
                    setState("idle", "⏸️", "Standby — hold Spacebar to talk");
                    break;
                case "listening_started":
                    setState("listening", "🔴", "Listening...");
                    hideAll();
                    break;
                case "listening_stopped":
                    setState("processing", "⏳", "Processing...");
                    break;
                case "transcription":
                    showTranscription(data.text);
                    break;
                case "command_matched":
                    showCommandMatched(data.command);
                    break;
                case "command_result":
                    showResult(data.success, data.command, data.code);
                    setState(data.success ? "success" : "error", data.success ? "✅" : "❌", data.success ? "Done" : "Failed");
                    break;
                case "no_match":
                    showTranscription(data.text);
                    showError(data.message);
                    setState("error", "⚠️", "No match");
                    break;
                case "command_error":
                    showError(data.message);
                    setState("error", "💥", "Error");
                    break;
                case "error":
                    showError(data.message);
                    setState("error", "💥", "Error");
                    break;
            }
        };
    }

    async function loadStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            robotStatusEl.textContent = `Robot: ${data.robot_connected ? "Connected" : "Not Connected"}`;
            robotStatusEl.className = "status-indicator " + (data.robot_connected ? "connected" : "disconnected");
            modelInfoEl.textContent = `Whisper: ${data.whisper_model}`;
        } catch {
            robotStatusEl.textContent = "Robot: —";
        }
    }

    async function loadCommands() {
        try {
            const res = await fetch("/api/commands");
            const cmds = await res.json();
            commandsList.innerHTML = "";
            for (const c of cmds) {
                const div = document.createElement("div");
                div.className = "cmd-item" + (c.is_movement ? " movement" : "");
                div.innerHTML = `<div class="cmd-name">${c.display}</div><div class="cmd-triggers">${c.triggers.slice(0, 3).join(", ")}</div>`;
                commandsList.appendChild(div);
            }
        } catch {}
    }

    loadStatus();
    loadCommands();
    connect();
    setState("idle", "⏸️", "Standby");
})();
