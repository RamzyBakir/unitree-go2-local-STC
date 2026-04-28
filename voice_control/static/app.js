(function () {
    const pttBtn = document.getElementById("ptt-btn");
    const pttLabel = document.getElementById("ptt-label");
    const wsStatusEl = document.getElementById("ws-status");
    const robotStatusEl = document.getElementById("robot-status");
    const modelInfoEl = document.getElementById("model-info");
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
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;

    function hideAll() {
        [transcriptionEl, commandMatchedEl, commandResultEl, errorMessageEl].forEach(
            (el) => el.classList.add("hidden")
        );
    }

    function showTranscription(text) {
        transcriptionText.textContent = text;
        transcriptionEl.classList.remove("hidden");
    }

    function showCommandMatched(cmd) {
        matchedCommand.textContent = cmd;
        commandMatchedEl.classList.remove("hidden");
    }

    function showResult(success, msg) {
        resultIcon.textContent = success ? "✓" : "✗";
        resultMessage.textContent = msg;
        commandResultEl.classList.remove("hidden");
        commandResultEl.className = "feedback-card " + (success ? "success" : "error");
    }

    function showError(msg) {
        errorText.textContent = msg;
        errorMessageEl.classList.remove("hidden");
    }

    function connect() {
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        ws = new WebSocket(`${proto}//${location.host}/ws/audio`);

        ws.onopen = () => {
            wsStatusEl.textContent = "Connected";
            wsStatusEl.className = "status-indicator connected";
            pttBtn.disabled = false;
        };

        ws.onclose = () => {
            wsStatusEl.textContent = "Disconnected";
            wsStatusEl.className = "status-indicator disconnected";
            pttBtn.disabled = true;
            setTimeout(connect, 2000);
        };

        ws.onerror = () => {};

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch (data.type) {
                case "transcription":
                    if (data.text) showTranscription(data.text);
                    break;
                case "command_matched":
                    showCommandMatched(data.command);
                    break;
                case "command_result":
                    showResult(
                        data.success,
                        data.success ? `${data.command} — OK` : `${data.command} — Error (code ${data.code})`
                    );
                    break;
                case "no_match":
                    showTranscription(data.text);
                    showError(data.message);
                    break;
                case "command_error":
                    showError(data.message);
                    break;
                case "error":
                    showError(data.message);
                    break;
            }
        };
    }

    function getSupportedMimeType() {
        const types = [
            "audio/webm;codecs=opus",
            "audio/webm",
            "audio/ogg;codecs=opus",
            "audio/mp4",
        ];
        for (const t of types) {
            if (MediaRecorder.isTypeSupported(t)) return t;
        }
        return "";
    }

    async function startRecording() {
        if (isRecording) return;
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mimeType = getSupportedMimeType();
            const options = mimeType ? { mimeType } : {};
            mediaRecorder = new MediaRecorder(stream, options);
            audioChunks = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
                if (blob.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                    blob.arrayBuffer().then((buf) => ws.send(buf));
                }
                stream.getTracks().forEach((t) => t.stop());
            };

            mediaRecorder.start();
            isRecording = true;
            pttBtn.classList.add("recording");
            pttLabel.textContent = "Listening...";
            hideAll();
        } catch (err) {
            showError("Microphone access denied");
        }
    }

    function stopRecording() {
        if (!isRecording || !mediaRecorder) return;
        mediaRecorder.stop();
        isRecording = false;
        pttBtn.classList.remove("recording");
        pttLabel.textContent = "Processing...";
        pttBtn.disabled = true;
    }

    pttBtn.addEventListener("mousedown", startRecording);
    pttBtn.addEventListener("mouseup", stopRecording);
    pttBtn.addEventListener("mouseleave", () => {
        if (isRecording) stopRecording();
    });

    pttBtn.addEventListener("touchstart", (e) => {
        e.preventDefault();
        startRecording();
    });
    pttBtn.addEventListener("touchend", (e) => {
        e.preventDefault();
        stopRecording();
    });

    function setPttEnabled(enabled) {
        if (!isRecording) {
            pttBtn.disabled = !enabled;
            pttLabel.textContent = enabled ? "Press & hold to talk" : "Connecting...";
        }
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

    ws.addEventListener("message", function restoreBtn() {
        if (!isRecording) {
            pttBtn.disabled = false;
            pttLabel.textContent = "Press & hold to talk";
        }
    });

    loadStatus();
    loadCommands();
    connect();
})();
