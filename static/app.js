(function () {
  const card = document.getElementById("voice-model-card");
  if (!card) return;
  const caseId = card.dataset.caseId;

  const modelStatusEl = document.getElementById("model-status");
  const inputSelect = document.getElementById("input-device");
  const outputSelect = document.getElementById("output-device");
  const pitchInput = document.getElementById("pitch");
  const startBtn = document.getElementById("live-start");
  const stopBtn = document.getElementById("live-stop");
  const liveStatusEl = document.getElementById("live-status");
  const liveErrorEl = document.getElementById("live-error");

  function showError(message) {
    liveErrorEl.textContent = message;
    liveErrorEl.hidden = false;
  }

  function clearError() {
    liveErrorEl.hidden = true;
    liveErrorEl.textContent = "";
  }

  function populateDevices() {
    fetch("/devices")
      .then((res) => res.json())
      .then((data) => {
        if (data.error) {
          showError("Could not list audio devices: " + data.error);
          return;
        }
        inputSelect.innerHTML = "";
        data.inputs.forEach((dev) => {
          const opt = document.createElement("option");
          opt.value = dev.id;
          opt.textContent = dev.name;
          inputSelect.appendChild(opt);
        });
        outputSelect.innerHTML = "";
        data.outputs.forEach((dev) => {
          const opt = document.createElement("option");
          opt.value = dev.id;
          opt.textContent = dev.name;
          outputSelect.appendChild(opt);
        });
      })
      .catch((err) => showError("Could not list audio devices: " + err));
  }

  function pollTrainingStatus() {
    fetch(`/cases/${caseId}/train/status`)
      .then((res) => res.json())
      .then((data) => {
        modelStatusEl.textContent = data.status;
        modelStatusEl.className = "badge badge-" + data.status;
      })
      .catch(() => {});
  }

  function pollLiveStatus() {
    fetch(`/cases/${caseId}/live/status`)
      .then((res) => res.json())
      .then((data) => {
        liveStatusEl.textContent = data.running ? "running" : "stopped";
      })
      .catch(() => {});
  }

  startBtn.addEventListener("click", () => {
    clearError();
    fetch(`/cases/${caseId}/live/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_device: inputSelect.value,
        output_device: outputSelect.value,
        pitch: pitchInput.value,
      }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          showError(data.error || "Could not start live conversion.");
          return;
        }
        liveStatusEl.textContent = "running";
      })
      .catch((err) => showError(String(err)));
  });

  stopBtn.addEventListener("click", () => {
    clearError();
    fetch(`/cases/${caseId}/live/stop`, { method: "POST" })
      .then((res) => res.json())
      .then((data) => {
        liveStatusEl.textContent = data.running ? "running" : "stopped";
      })
      .catch((err) => showError(String(err)));
  });

  populateDevices();
  pollTrainingStatus();
  pollLiveStatus();
  setInterval(pollTrainingStatus, 4000);
  setInterval(pollLiveStatus, 4000);
})();
