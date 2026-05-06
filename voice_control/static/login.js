(function () {
    const form = document.getElementById("login-form");
    const userEl = document.getElementById("username");
    const passEl = document.getElementById("password");
    const errEl = document.getElementById("login-error");
    const btn = document.getElementById("login-btn");

    function showError(msg) {
        errEl.textContent = msg;
        errEl.classList.remove("hidden");
    }
    function clearError() { errEl.classList.add("hidden"); }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearError();
        btn.disabled = true;
        btn.textContent = "Signing in…";
        try {
            const res = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username: userEl.value,
                    password: passEl.value,
                }),
            });
            if (res.ok) {
                const next = new URLSearchParams(location.search).get("next") || "/";
                location.replace(next);
                return;
            }
            const data = await res.json().catch(() => ({}));
            showError(data.error || "Sign-in failed");
        } catch (e) {
            showError(e.message || "Network error");
        } finally {
            btn.disabled = false;
            btn.textContent = "Sign in";
        }
    });

    userEl.focus();
})();
