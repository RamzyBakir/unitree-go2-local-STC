(function () {
    const $ = (id) => document.getElementById(id);

    const wsStatusEl    = $("ws-status");
    const robotStatusEl = $("robot-status");
    const modeStatusEl  = $("mode-status");
    const stateCard     = $("state-card");
    const stateText     = $("state-text");
    const transcriptionEl    = $("transcription");
    const transcriptionText  = $("transcription-text");
    const commandMatchedEl   = $("command-matched");
    const matchedCommand     = $("matched-command");
    const commandResultEl    = $("command-result");
    const resultMessage      = $("result-message");
    const errorMessageEl     = $("error-message");
    const errorText          = $("error-text");
    const feedbackEmpty      = $("feedback-empty");
    const commandsList       = $("commands-list");
    const recordBtn          = $("record-btn");
    const recordLabel        = recordBtn.querySelector(".record-label");
    const textForm           = $("text-form");
    const textCmd            = $("text-cmd");
    const sendBtn            = $("send-btn");
    const cmdFilter          = $("cmd-filter");
    const cmdToggle          = $("cmd-toggle");
    const cmdPanel           = $("cmd-panel");
    const cmdSheetBackdrop   = $("cmd-sheet-backdrop");
    const logoutBtn          = $("logout-btn");

    let ws = null;
    let reconnectTimer = null;
    let allCommands = [];

    /* ------- UI helpers ------- */
    function setState(status, text) {
        stateCard.className = "state glass " + status;
        stateText.textContent = text;
    }
    function hideFeedback() {
        [transcriptionEl, commandMatchedEl, commandResultEl, errorMessageEl].forEach(
            (el) => el.classList.add("hidden")
        );
        feedbackEmpty.classList.remove("hidden");
    }
    function showAnyFeedback() { feedbackEmpty.classList.add("hidden"); }
    function showTranscription(text) {
        showAnyFeedback();
        transcriptionText.textContent = text || "(silence)";
        transcriptionEl.classList.remove("hidden");
    }
    function showCommandMatched(cmd) {
        showAnyFeedback();
        matchedCommand.textContent = cmd;
        commandMatchedEl.classList.remove("hidden");
    }
    function showResult(success, cmd, code) {
        showAnyFeedback();
        resultMessage.textContent = success ? `${cmd} — OK` : `${cmd} — Error (code ${code})`;
        resultMessage.className = "fb-val " + (success ? "success" : "fail");
        commandResultEl.classList.remove("hidden");
    }
    function showError(msg) {
        showAnyFeedback();
        errorText.textContent = msg;
        errorMessageEl.classList.remove("hidden");
    }
    function setPill(el, label, kind) {
        el.textContent = label;
        el.className = "pill" + (kind ? " " + kind : "");
    }

    /* ------- WebSocket ------- */
    function connect() {
        if (reconnectTimer) clearTimeout(reconnectTimer);
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        ws = new WebSocket(`${proto}//${location.host}/ws/status`);

        ws.onopen  = () => setPill(wsStatusEl, "WS · Live", "ok");
        ws.onclose = () => {
            setPill(wsStatusEl, "WS · Off", "bad");
            reconnectTimer = setTimeout(connect, 2000);
        };
        ws.onerror = () => {};
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            switch (data.type) {
                case "ready":
                    setState("idle", "Ready");
                    break;
                case "listening_started":
                    setState("listening", "Listening…");
                    hideFeedback();
                    break;
                case "listening_stopped":
                    setState("processing", "Transcribing…");
                    break;
                case "transcription":
                    showTranscription(data.text);
                    break;
                case "command_matched":
                    showCommandMatched(data.command);
                    setState("processing", "Executing…");
                    break;
                case "command_result":
                    showResult(data.success, data.command, data.code);
                    setState(data.success ? "success" : "error", data.success ? "Done" : "Failed");
                    break;
                case "no_match":
                    showTranscription(data.text);
                    showError(data.message);
                    setState("error", "No match");
                    break;
                case "command_error":
                case "error":
                    showError(data.message || "Unknown error");
                    setState("error", "Error");
                    break;
            }
        };
    }

    /* ------- Voice via browser MediaRecorder ------- */
    let mediaStream = null;
    let mediaRecorder = null;
    let recordedChunks = [];
    let recording = false;

    function micSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
    }

    function pickMime() {
        const candidates = [
            "audio/webm;codecs=opus",
            "audio/webm",
            "audio/ogg;codecs=opus",
            "audio/mp4",
        ];
        for (const c of candidates) {
            if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(c)) return c;
        }
        return "";
    }

    async function startRecording() {
        if (recording) return;
        if (!micSupported()) {
            showError("Mic not available — use the text input. (HTTPS required for mic.)");
            return;
        }
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    channelCount: 1,
                },
            });
        } catch (e) {
            showError("Mic permission denied or unavailable: " + e.message);
            return;
        }

        const mime = pickMime();
        recordedChunks = [];
        try {
            mediaRecorder = mime ? new MediaRecorder(mediaStream, { mimeType: mime })
                                 : new MediaRecorder(mediaStream);
        } catch (e) {
            showError("MediaRecorder failed: " + e.message);
            stopMicTracks();
            return;
        }
        mediaRecorder.ondataavailable = (ev) => {
            if (ev.data && ev.data.size > 0) recordedChunks.push(ev.data);
        };
        mediaRecorder.onstop = handleRecordingStop;
        mediaRecorder.start();

        recording = true;
        recordBtn.classList.add("recording");
        recordLabel.textContent = "Recording…";
        setState("listening", "Listening…");
        hideFeedback();
    }

    function stopMicTracks() {
        if (mediaStream) {
            for (const t of mediaStream.getTracks()) t.stop();
        }
        mediaStream = null;
    }

    function stopRecording() {
        if (!recording) return;
        recording = false;
        recordBtn.classList.remove("recording");
        recordLabel.textContent = "Hold to Speak";
        try {
            if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
        } catch (_) {}
    }

    async function handleRecordingStop() {
        const mime = (mediaRecorder && mediaRecorder.mimeType) || "audio/webm";
        const blob = new Blob(recordedChunks, { type: mime });
        recordedChunks = [];
        stopMicTracks();
        if (blob.size === 0) {
            showError("No audio captured.");
            setState("idle", "Ready");
            return;
        }
        setState("processing", "Transcribing…");

        const ext = mime.includes("ogg") ? "ogg" : mime.includes("mp4") ? "m4a" : "webm";
        const fd = new FormData();
        fd.append("audio", blob, `clip.${ext}`);

        try {
            const res = await fetch("/api/transcribe", { method: "POST", body: fd });
            if (res.status === 401) { location.replace("/login"); return; }
            const data = await res.json().catch(() => ({}));
            if (!res.ok) showError(data.error || "Transcription failed");
        } catch (e) {
            showError(e.message);
            setState("error", "Error");
        }
    }

    /* PTT bindings (mouse + touch) */
    function ptDown(e) { e.preventDefault(); startRecording(); }
    function ptUp(e)   { if (e) e.preventDefault?.(); stopRecording(); }
    recordBtn.addEventListener("mousedown",   ptDown);
    recordBtn.addEventListener("mouseup",     ptUp);
    recordBtn.addEventListener("mouseleave",  () => { if (recording) stopRecording(); });
    recordBtn.addEventListener("touchstart",  ptDown, { passive: false });
    recordBtn.addEventListener("touchend",    ptUp,   { passive: false });
    recordBtn.addEventListener("touchcancel", () => stopRecording());
    document.addEventListener("visibilitychange", () => {
        if (document.hidden && recording) stopRecording();
    });

    /* ------- Manual text command ------- */
    async function sendText(text) {
        const t = (text ?? textCmd.value).trim();
        if (!t) return;
        sendBtn.disabled = true;
        try {
            const res = await fetch("/api/text-command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: t }),
            });
            if (res.status === 401) { location.replace("/login"); return; }
            const data = await res.json().catch(() => ({}));
            if (!res.ok && data.error) showError(data.error);
            textCmd.value = "";
        } catch (e) {
            showError(e.message);
        } finally {
            sendBtn.disabled = false;
            textCmd.focus();
        }
    }

    textForm.addEventListener("submit", (e) => { e.preventDefault(); sendText(); });

    /* ------- Status & command list ------- */
    async function loadStatus() {
        try {
            const res = await fetch("/api/status");
            if (res.status === 401) { location.replace("/login"); return; }
            const data = await res.json();
            setPill(robotStatusEl, "Robot · " + (data.robot_connected ? "On" : "Off"),
                    data.robot_connected ? "ok" : "bad");
            setPill(modeStatusEl, data.mock_mode ? "Mock" : "Live",
                    data.mock_mode ? "warn" : "ok");
        } catch {
            setPill(robotStatusEl, "Robot · ?", "bad");
            setPill(modeStatusEl, "—", "");
        }
    }

    function renderCommands(filter) {
        const f = (filter || "").toLowerCase().trim();
        commandsList.innerHTML = "";
        const visible = allCommands.filter((c) => {
            if (!f) return true;
            return (
                c.display.toLowerCase().includes(f) ||
                c.triggers.some((t) => t.toLowerCase().includes(f))
            );
        });
        for (const c of visible) {
            const div = document.createElement("div");
            div.className = "cmd-item" + (c.is_movement ? " is-move" : "");
            div.innerHTML = `<div class="cmd-name">${c.display}</div>
                             <div class="cmd-triggers">${c.triggers.slice(0, 3).join(" · ")}</div>`;
            div.addEventListener("click", () => {
                sendText(c.triggers[0]);
                if (cmdPanel.classList.contains("open")) closeCmdSheet();
            });
            commandsList.appendChild(div);
        }
        if (visible.length === 0) {
            const empty = document.createElement("div");
            empty.className = "cmd-item";
            empty.style.color = "var(--text-mute)";
            empty.textContent = "No matches";
            commandsList.appendChild(empty);
        }
    }
    cmdFilter.addEventListener("input", () => renderCommands(cmdFilter.value));

    async function loadCommands() {
        try {
            const res = await fetch("/api/commands");
            if (res.status === 401) { location.replace("/login"); return; }
            allCommands = await res.json();
            renderCommands("");
        } catch {}
    }

    /* ------- Mobile sheet toggle ------- */
    function openCmdSheet()  {
        cmdPanel.classList.add("open");
        cmdSheetBackdrop.classList.remove("hidden");
    }
    function closeCmdSheet() {
        cmdPanel.classList.remove("open");
        cmdSheetBackdrop.classList.add("hidden");
    }
    cmdToggle.addEventListener("click", openCmdSheet);
    cmdSheetBackdrop.addEventListener("click", closeCmdSheet);

    /* ------- Logout ------- */
    logoutBtn.addEventListener("click", async () => {
        try { await fetch("/api/logout", { method: "POST" }); } catch (_) {}
        location.replace("/login");
    });

    /* ------- Boot ------- */
    if (!micSupported()) {
        recordBtn.classList.add("disabled");
        recordLabel.textContent = "Mic needs HTTPS";
    }
    loadStatus();
    loadCommands();
    connect();
    setState("idle", "Standby");
    hideFeedback();
})();
