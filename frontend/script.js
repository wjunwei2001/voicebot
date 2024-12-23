const recordBtn = document.getElementById("record-btn");
const status = document.getElementById("status");
const chatOutput = document.getElementById("chat-output");

let isRecording = false;
let mediaRecorder;

recordBtn.addEventListener("click", async () => {
    if (!isRecording) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        let audioChunks = [];

        mediaRecorder.ondataavailable = event => audioChunks.push(event.data);

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
            const formData = new FormData();
            formData.append("file", audioBlob);

            status.textContent = "Processing audio...";
            try {
                const response = await fetch("http://localhost:8000/audio-to-text/", {
                    method: "POST",
                    body: formData
                });
                const result = await response.json();
                const userText = result.text;

                status.textContent = "Fetching response...";
                const chatResponse = await fetch("http://localhost:8000/chat/", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ text: userText })
                });
                const chatResult = await chatResponse.json();
                chatOutput.value += `User: ${userText}\nBot: ${chatResult.response}\n`;
                status.textContent = "Idle";
            } catch (error) {
                status.textContent = "Error occurred!";
                console.error(error);
            }
        };

        mediaRecorder.start();
        recordBtn.textContent = "Stop Recording";
        status.textContent = "Recording...";
        isRecording = true;
    } else {
        mediaRecorder.stop();
        recordBtn.textContent = "Start Recording";
        isRecording = false;
    }
});
